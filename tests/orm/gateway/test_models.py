from unittest.mock import patch

import pytest
from factories import (
    AccountTypeFactory,
    CountryFactory,
    DeliveryMechanismFactory,
    ExportTemplateFactory,
    FinancialServiceProviderConfigFactory,
    FinancialServiceProviderFactory,
    OfficeFactory,
    PaymentInstructionFactory,
    PaymentRecordFactory,
)
from hope_payment_gateway.apps.gateway.models import PaymentRecordState


@pytest.mark.django_db
def test_model_str_methods():
    at = AccountTypeFactory(label="Test Account Type")
    assert str(at) == "Test Account Type"

    dm = DeliveryMechanismFactory(name="Test DM", code="TDM")
    assert str(dm) == "Test DM [TDM]"

    office = OfficeFactory(name="Test Office")
    assert str(office) == "Test Office"

    country = CountryFactory(name="Test Country")
    assert str(country) == "Test Country"

    fsp = FinancialServiceProviderFactory(name="Test FSP", vendor_number="V123")
    assert str(fsp) == "Test FSP [V123]"

    fsp_config = FinancialServiceProviderConfigFactory(fsp=fsp, delivery_mechanism=dm, label="L1")
    assert str(fsp_config) == f"{fsp}/{dm} [L1]"

    template = ExportTemplateFactory(fsp=fsp, config_key="CK1")
    assert str(template) == "Test FSP [V123] / CK1"

    instruction = PaymentInstructionFactory(external_code="EC1", status="DRAFT")
    assert str(instruction) == "EC1 - DRAFT"

    record = PaymentRecordFactory(record_code="RC1", status="PENDING")
    assert str(record) == "RC1 / PENDING"


@pytest.mark.django_db
def test_payment_record_payload():
    instruction = PaymentInstructionFactory(payload={"a": "a"})
    prl = PaymentRecordFactory(parent=instruction, payload={"b": "b"}, record_code="r")
    assert prl.get_payload().keys() == {"a", "b", "payment_record_code", "remote_id"}


@pytest.mark.django_db
def test_payment_instruction_selected_export():
    fsp = FinancialServiceProviderFactory()
    dm = DeliveryMechanismFactory()
    office = OfficeFactory()
    country = CountryFactory()

    # Template with everything matching
    template1 = ExportTemplateFactory(fsp=fsp, delivery_mechanism=dm, office=office, country=country, config_key="T1")
    # Template with office as null
    template2 = ExportTemplateFactory(fsp=fsp, delivery_mechanism=dm, office=None, country=country, config_key="T2")

    instruction = PaymentInstructionFactory(fsp=fsp, delivery_mechanism=dm, office=office, country=country)
    assert instruction.selected_export == template1

    instruction.office = None
    instruction.save()
    assert instruction.selected_export == template2

    # Forced export
    forced_template = ExportTemplateFactory(fsp=fsp, config_key="FORCED")
    instruction.export = forced_template
    instruction.save()
    assert instruction.selected_export == forced_template


@pytest.mark.django_db
def test_payment_instruction_configuration():
    fsp = FinancialServiceProviderFactory()
    dm = DeliveryMechanismFactory()
    office = OfficeFactory()
    country1 = CountryFactory()
    country2 = CountryFactory()

    config1 = FinancialServiceProviderConfigFactory(
        fsp=fsp, delivery_mechanism=dm, office=office, country=country1, label="C1"
    )
    # Use different country to avoid unique_together constraint violation
    config2 = FinancialServiceProviderConfigFactory(
        fsp=fsp, delivery_mechanism=dm, office=None, country=country2, label="C2"
    )

    instruction = PaymentInstructionFactory(fsp=fsp, delivery_mechanism=dm, office=office, country=country1)
    assert instruction.configuration == config1

    instruction.country = country2
    instruction.office = None
    instruction.save()
    assert instruction.configuration == config2


@pytest.mark.django_db
def test_get_payload_methods():
    fsp = FinancialServiceProviderFactory()
    instruction = PaymentInstructionFactory(fsp=fsp, payload={"a": 1, "config_key": "CK1"})

    with patch.object(fsp.strategy.__class__, "get_configuration") as mock_get_config:
        mock_get_config.return_value = {"b": 2}

        payload = instruction.get_payload()
        assert payload["a"] == 1
        assert payload["b"] == 2
        assert "config_key" in payload

        # Case without config_key to cover branch
        instruction_no_config = PaymentInstructionFactory(fsp=fsp, payload={"a": 1})
        payload_no_config = instruction_no_config.get_payload()
        assert payload_no_config == {"a": 1}

        record = PaymentRecordFactory(parent=instruction, record_code="RC1", remote_id="RID1", payload={"c": 3})
        record_payload = record.get_payload()
        assert record_payload["a"] == 1
        assert record_payload["b"] == 2
        assert record_payload["c"] == 3
        assert record_payload["payment_record_code"] == "RC1"
        assert record_payload["remote_id"] == "RID1"


@pytest.mark.django_db
def test_payment_record_add_push_notification():
    record = PaymentRecordFactory(fsp_data=None)
    payload1 = {"event": "test1"}
    payload2 = {"event": "test2"}

    # Test initialization of None fsp_data
    record.add_push_notification(payload1)
    assert record.fsp_data["push_notification"] == [payload1]

    # Test appending second payload
    record.add_push_notification(payload2)
    assert record.fsp_data["push_notification"] == [payload1, payload2]

    # Test persistence
    record.save()
    record.refresh_from_db()
    assert record.fsp_data["push_notification"] == [payload1, payload2]


@pytest.mark.django_db
def test_record_updated_signal_no_old_instance():
    with patch("hope_payment_gateway.apps.gateway.signals.flag_enabled", return_value=True):
        with patch("hope_payment_gateway.apps.gateway.signals.notify_record_change") as mock_notify:
            parent = PaymentInstructionFactory()
            record = PaymentRecordFactory.build(id=99999, status=PaymentRecordState.PENDING, parent=parent)
            record.save()
            mock_notify.assert_not_called()

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


# --- Fixtures for test_model_str_methods ---


@pytest.fixture
def account_type():
    return AccountTypeFactory.create(label="Test Account Type")


@pytest.fixture
def delivery_mechanism_for_str():
    return DeliveryMechanismFactory.create(name="Test DM", code="TDM")


@pytest.fixture
def office_for_str():
    return OfficeFactory.create(name="Test Office")


@pytest.fixture
def country_for_str():
    return CountryFactory.create(name="Test Country")


@pytest.fixture
def fsp_for_str():
    return FinancialServiceProviderFactory.create(name="Test FSP", vendor_number="V123")


@pytest.fixture
def fsp_config_for_str(fsp_for_str, delivery_mechanism_for_str):
    return FinancialServiceProviderConfigFactory.create(
        fsp=fsp_for_str, delivery_mechanism=delivery_mechanism_for_str, label="L1"
    )


@pytest.fixture
def export_template_for_str(fsp_for_str):
    return ExportTemplateFactory.create(fsp=fsp_for_str, config_key="CK1")


@pytest.fixture
def instruction_for_str():
    return PaymentInstructionFactory.create(external_code="EC1", status="DRAFT")


@pytest.fixture
def record_for_str():
    return PaymentRecordFactory.create(record_code="RC1", status="PENDING")


@pytest.mark.django_db
def test_model_str_methods(
    account_type,
    delivery_mechanism_for_str,
    office_for_str,
    country_for_str,
    fsp_for_str,
    fsp_config_for_str,
    export_template_for_str,
    instruction_for_str,
    record_for_str,
):
    assert str(account_type) == "Test Account Type"
    assert str(delivery_mechanism_for_str) == "Test DM [TDM]"
    assert str(office_for_str) == "Test Office"
    assert str(country_for_str) == "Test Country"
    assert str(fsp_for_str) == "Test FSP [V123]"
    assert str(fsp_config_for_str) == f"{fsp_for_str}/{delivery_mechanism_for_str} [L1]"
    assert str(export_template_for_str) == "Test FSP [V123] / CK1"
    assert str(instruction_for_str) == "EC1 - DRAFT"
    assert str(record_for_str) == "RC1 / PENDING"


# --- Fixtures for test_payment_record_payload ---


@pytest.fixture
def payment_instruction_with_payload():
    return PaymentInstructionFactory.create(payload={"a": "a"})


@pytest.fixture
def payment_record_with_payload(payment_instruction_with_payload):
    return PaymentRecordFactory.create(parent=payment_instruction_with_payload, payload={"b": "b"}, record_code="r")


@pytest.mark.django_db
def test_payment_record_payload(payment_record_with_payload):
    assert payment_record_with_payload.get_payload().keys() == {
        "a",
        "delivery_mechanism",
        "b",
        "payment_record_code",
        "remote_id",
    }


# --- Fixtures for test_payment_instruction_selected_export ---


@pytest.fixture
def fsp_for_se():
    return FinancialServiceProviderFactory.create()


@pytest.fixture
def dm_for_se():
    return DeliveryMechanismFactory.create()


@pytest.fixture
def office_for_se():
    return OfficeFactory.create()


@pytest.fixture
def country_for_se():
    return CountryFactory.create()


@pytest.fixture
def template1_for_se(fsp_for_se, dm_for_se, office_for_se, country_for_se):
    return ExportTemplateFactory.create(
        fsp=fsp_for_se,
        delivery_mechanism=dm_for_se,
        office=office_for_se,
        country=country_for_se,
        config_key="T1",
    )


@pytest.fixture
def template2_for_se(fsp_for_se, dm_for_se, country_for_se):
    return ExportTemplateFactory.create(
        fsp=fsp_for_se,
        delivery_mechanism=dm_for_se,
        office=None,
        country=country_for_se,
        config_key="T2",
    )


@pytest.fixture
def instruction_for_se(fsp_for_se, dm_for_se, office_for_se, country_for_se):
    return PaymentInstructionFactory.create(
        fsp=fsp_for_se,
        delivery_mechanism=dm_for_se,
        office=office_for_se,
        country=country_for_se,
    )


@pytest.fixture
def forced_template_for_se(fsp_for_se):
    return ExportTemplateFactory.create(fsp=fsp_for_se, config_key="FORCED")


@pytest.mark.django_db
def test_payment_instruction_selected_export(
    template1_for_se,
    template2_for_se,
    instruction_for_se,
    forced_template_for_se,
):
    assert instruction_for_se.selected_export == template1_for_se

    instruction_for_se.office = None
    instruction_for_se.save()
    assert instruction_for_se.selected_export == template2_for_se

    instruction_for_se.export = forced_template_for_se
    instruction_for_se.save()
    assert instruction_for_se.selected_export == forced_template_for_se


# --- Fixtures for test_payment_instruction_configuration ---


@pytest.fixture
def fsp_for_config():
    return FinancialServiceProviderFactory.create()


@pytest.fixture
def dm_for_config():
    return DeliveryMechanismFactory.create()


@pytest.fixture
def office_for_config():
    return OfficeFactory.create()


@pytest.fixture
def country1_for_config():
    return CountryFactory.create()


@pytest.fixture
def country2_for_config():
    return CountryFactory.create()


@pytest.fixture
def config1_for_config(fsp_for_config, dm_for_config, office_for_config, country1_for_config):
    return FinancialServiceProviderConfigFactory.create(
        fsp=fsp_for_config,
        delivery_mechanism=dm_for_config,
        office=office_for_config,
        country=country1_for_config,
        label="C1",
    )


@pytest.fixture
def config2_for_config(fsp_for_config, dm_for_config, country2_for_config):
    return FinancialServiceProviderConfigFactory.create(
        fsp=fsp_for_config,
        delivery_mechanism=dm_for_config,
        office=None,
        country=country2_for_config,
        label="C2",
    )


@pytest.fixture
def instruction_for_config(fsp_for_config, dm_for_config, office_for_config, country1_for_config):
    return PaymentInstructionFactory.create(
        fsp=fsp_for_config,
        delivery_mechanism=dm_for_config,
        office=office_for_config,
        country=country1_for_config,
    )


@pytest.mark.django_db
def test_payment_instruction_configuration(
    config1_for_config,
    config2_for_config,
    instruction_for_config,
    country2_for_config,
):
    assert instruction_for_config.configuration == config1_for_config

    instruction_for_config.country = country2_for_config
    instruction_for_config.office = None
    instruction_for_config.save()
    assert instruction_for_config.configuration == config2_for_config


# --- Fixtures for test_get_payload_methods ---


@pytest.fixture
def fsp_for_get_payload():
    return FinancialServiceProviderFactory.create()


@pytest.fixture
def instruction_for_get_payload(fsp_for_get_payload):
    return PaymentInstructionFactory.create(fsp=fsp_for_get_payload, payload={"a": 1, "config_key": "CK1"})


@pytest.fixture
def instruction_no_config_for_get_payload(fsp_for_get_payload):
    return PaymentInstructionFactory.create(fsp=fsp_for_get_payload, payload={"a": 1})


@pytest.fixture
def record_for_get_payload(instruction_for_get_payload):
    return PaymentRecordFactory.create(
        parent=instruction_for_get_payload,
        record_code="RC1",
        remote_id="RID1",
        payload={"c": 3},
    )


@pytest.mark.django_db
def test_get_payload_methods(
    fsp_for_get_payload,
    instruction_for_get_payload,
    instruction_no_config_for_get_payload,
    record_for_get_payload,
):
    with patch.object(fsp_for_get_payload.strategy.__class__, "get_configuration") as mock_get_config:
        mock_get_config.return_value = {"b": 2}

        payload = instruction_for_get_payload.get_payload()
        assert payload["a"] == 1
        assert payload["b"] == 2
        assert "config_key" in payload

        payload_no_config = instruction_no_config_for_get_payload.get_payload()
        assert payload_no_config["a"] == 1

        record_payload = record_for_get_payload.get_payload()
        assert record_payload["a"] == 1
        assert record_payload["b"] == 2
        assert record_payload["c"] == 3
        assert record_payload["payment_record_code"] == "RC1"
        assert record_payload["remote_id"] == "RID1"


# --- Fixtures for test_payment_record_add_push_notification ---


@pytest.fixture
def record_for_push_notification():
    return PaymentRecordFactory.create(fsp_data=None)


@pytest.mark.django_db
def test_payment_record_add_push_notification(record_for_push_notification):
    payload1 = {"event": "test1"}
    payload2 = {"event": "test2"}

    record_for_push_notification.add_push_notification(payload1)
    assert record_for_push_notification.fsp_data["push_notification"] == [payload1]

    record_for_push_notification.add_push_notification(payload2)
    assert record_for_push_notification.fsp_data["push_notification"] == [
        payload1,
        payload2,
    ]

    record_for_push_notification.save()
    record_for_push_notification.refresh_from_db()
    assert record_for_push_notification.fsp_data["push_notification"] == [
        payload1,
        payload2,
    ]


# --- Fixtures for test_record_updated_signal_no_old_instance ---


@pytest.fixture
def parent_for_signal():
    return PaymentInstructionFactory.create()


@pytest.fixture
def record_for_signal(parent_for_signal):
    return PaymentRecordFactory.create(id=99999, status=PaymentRecordState.PENDING, parent=parent_for_signal)


@pytest.mark.django_db
def test_record_updated_signal_no_old_instance(parent_for_signal, record_for_signal):
    with patch("hope_payment_gateway.apps.gateway.signals.flag_enabled", return_value=True):
        with patch("hope_payment_gateway.apps.gateway.signals.notify_record_change") as mock_notify:
            record_for_signal.save()
            mock_notify.assert_not_called()


# --- Fixtures for test_get_payload_without_delivery_mechanism ---


@pytest.fixture
def fsp_for_no_dm():
    return FinancialServiceProviderFactory.create()


@pytest.fixture
def country_for_no_dm():
    return CountryFactory.create()


@pytest.fixture
def instruction_for_no_dm(fsp_for_no_dm, country_for_no_dm):
    return PaymentInstructionFactory.create(
        fsp=fsp_for_no_dm,
        delivery_mechanism=None,
        country=country_for_no_dm,
        payload={"a": 1},
    )


@pytest.mark.django_db
def test_get_payload_without_delivery_mechanism(instruction_for_no_dm):
    payload = instruction_for_no_dm.get_payload()
    assert payload["a"] == 1
    assert "delivery_mechanism" not in payload


# --- Fixtures for test_get_payload_without_country ---


@pytest.fixture
def fsp_for_no_country():
    return FinancialServiceProviderFactory.create()


@pytest.fixture
def dm_for_no_country():
    return DeliveryMechanismFactory.create(code="CASH")


@pytest.fixture
def instruction_for_no_country(fsp_for_no_country, dm_for_no_country):
    return PaymentInstructionFactory.create(
        fsp=fsp_for_no_country,
        delivery_mechanism=dm_for_no_country,
        country=None,
        payload={"a": 1},
    )


@pytest.mark.django_db
def test_get_payload_without_country(instruction_for_no_country):
    payload = instruction_for_no_country.get_payload()
    assert payload["a"] == 1
    assert payload["delivery_mechanism"] == "CASH"


# --- Fixtures for test_get_payload_with_real_configuration ---


@pytest.fixture
def fsp_for_real_config():
    return FinancialServiceProviderFactory.create()


@pytest.fixture
def country_for_real_config():
    return CountryFactory.create()


@pytest.fixture
def dm_for_real_config():
    return DeliveryMechanismFactory.create(code="cash_over_the_counter")


@pytest.fixture
def config_for_real_config(fsp_for_real_config, country_for_real_config, dm_for_real_config):
    return FinancialServiceProviderConfigFactory.create(
        fsp=fsp_for_real_config,
        country=country_for_real_config,
        delivery_mechanism=dm_for_real_config,
        configuration={"extra_key": "extra_value"},
    )


@pytest.fixture
def instruction_for_real_config(config_for_real_config):
    fsp = config_for_real_config.fsp
    country = config_for_real_config.country
    dm = config_for_real_config.delivery_mechanism
    return PaymentInstructionFactory.create(
        fsp=fsp,
        country=country,
        delivery_mechanism=dm,
        payload={"a": 1},
    )


@pytest.mark.django_db
def test_get_payload_with_real_configuration(config_for_real_config, instruction_for_real_config):
    payload = instruction_for_real_config.get_payload()

    assert payload["a"] == 1
    assert payload["delivery_mechanism"] == "cash_over_the_counter"
    assert payload["extra_key"] == "extra_value"

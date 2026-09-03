from unittest.mock import patch

import pytest
from constance.test import override_config
from django.test import override_settings
from factories import PaymentInstructionFactory, PaymentRecordFactory
from hope_payment_gateway.api.western_union.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.tasks import (
    western_union_send_task,
    western_union_update_status,
    update_corridors,
    update_templates,
    western_union_notify,
)
from hope_payment_gateway.apps.gateway.models import PaymentInstructionState, PaymentRecordState
from strategy_field.utils import fqn

from tests.factories import CorridorFactory


@pytest.fixture
def wu_instruction(wu):
    return PaymentInstructionFactory.create(status=PaymentInstructionState.READY, fsp=wu)


@pytest.fixture
def wu_instruction_b(wu):
    return PaymentInstructionFactory.create(status=PaymentInstructionState.READY, fsp=wu)


@pytest.fixture
def noise_instruction():
    return PaymentInstructionFactory.create(status=PaymentInstructionState.OPEN)


@pytest.fixture
def noise_instruction_no_tag():
    return PaymentInstructionFactory.create(status=PaymentInstructionState.OPEN)


@pytest.fixture
def noise_records(wu_instruction, noise_instruction, noise_instruction_no_tag):
    PaymentRecordFactory.create_batch(5, parent=wu_instruction, status=PaymentRecordState.CANCELLED)
    PaymentRecordFactory.create_batch(5, parent=noise_instruction, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create_batch(5, parent=noise_instruction_no_tag, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create_batch(5, parent__status=PaymentRecordState.PENDING, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create_batch(
        5,
        parent__status=PaymentRecordState.PENDING,
        status=PaymentRecordState.PENDING,
    )


@pytest.fixture
def corridor_data():
    data = [
        {
            "destination_country": "US",
            "destination_currency": "USD",
            "template_code": "1234",
        },
        {
            "destination_country": "GB",
            "destination_currency": "GBP",
            "template_code": "4321",
        },
    ]
    for corr in data:
        CorridorFactory.create(**corr)
    return data


@pytest.fixture
def wu_status_instruction(wu):
    return PaymentInstructionFactory.create(fsp=wu)


@pytest.fixture
def wu_status_records(wu_status_instruction):
    return PaymentRecordFactory.create_batch(
        3,
        parent=wu_status_instruction,
        fsp_code="MTCN123",
    )


@pytest.fixture
def wu_notify_records():
    return PaymentRecordFactory.create_batch(3, status=PaymentRecordState.PENDING)


@pytest.mark.parametrize(
    ("rec_a", "rec_b", "total"),
    [
        (5, 4, 2),
        (5, 8, 2),
        (5, 5, 2),
        (4, 0, 2),
        (0, 4, 2),
        (0, 0, 2),
    ],
)
@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.apps.fsp.tasks_utils.AsyncJob.queue")
def test_send_money_task(mock_class, wu, rec_a, rec_b, total, wu_instruction, wu_instruction_b, noise_records):
    PaymentRecordFactory.create_batch(rec_a, parent=wu_instruction, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create_batch(rec_b, parent=wu_instruction_b, status=PaymentRecordState.PENDING)

    western_union_send_task()
    assert len(mock_class.mock_calls) == total


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.apps.fsp.western_union.tasks.WesternUnionClient")
def test_western_union_update_status(mock_client, wu, wu_status_instruction, wu_status_records):
    western_union_update_status()

    assert mock_client.return_value.status.call_count == 3
    for record in wu_status_records:
        mock_client.return_value.status.assert_any_call(record.fsp_code, True)


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.apps.fsp.western_union.tasks.WesternUnionClient")
def test_western_union_update_status_filtered_by_ids(mock_client, wu, wu_status_instruction, wu_status_records):
    ids = [wu_status_records[0].id, wu_status_records[1].id]

    western_union_update_status(ids=ids)

    assert mock_client.return_value.status.call_count == 2
    mock_client.return_value.status.assert_any_call(wu_status_records[0].fsp_code, True)
    mock_client.return_value.status.assert_any_call(wu_status_records[1].fsp_code, True)


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@patch("hope_payment_gateway.apps.fsp.western_union.tasks.WesternUnionClient")
def test_update_corridors(mock_client):
    update_corridors()

    mock_client.return_value.das_countries_currencies.assert_called_once_with(create_corridors=True)


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@patch("hope_payment_gateway.apps.fsp.western_union.tasks.WesternUnionClient")
def test_update_templates(mock_client, corridor_data):
    update_templates()

    assert mock_client.return_value.das_delivery_option_template.call_count == 2

    for corr in corridor_data:
        mock_client.return_value.das_delivery_option_template.assert_any_call(*corr.values())


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@patch("hope_payment_gateway.apps.fsp.western_union.tasks.notify_records_to_fsp")
def test_western_union_notify(mock_notify, wu_notify_records):
    record_ids = [record.id for record in wu_notify_records]
    mock_notify.return_value = None
    western_union_notify(record_ids)

    mock_notify.assert_called_once_with(fqn(WesternUnionClient), record_ids)

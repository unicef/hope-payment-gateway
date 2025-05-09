from unittest.mock import patch

import pytest
from constance.test import override_config
from django.test import override_settings
from factories import PaymentInstructionFactory, PaymentRecordFactory
from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.tasks import (
    western_union_send_task,
    update_corridors,
    update_templates,
    western_union_notify,
)
from hope_payment_gateway.apps.gateway.models import PaymentInstructionState, PaymentRecordState
from strategy_field.utils import fqn

from tests.factories import CorridorFactory


@pytest.mark.parametrize(
    ("rec_a", "rec_b", "total"),
    [
        (5, 4, 2),  # 9),
        (5, 8, 1),  # 5),
        (5, 5, 2),  # 10),
        (4, 0, 2),  # 4),
        (0, 4, 2),  # 4),
        (0, 0, 2),  # 0),
    ],
)
@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.apps.fsp.tasks_utils.AsyncJob.queue")
def test_send_money_task(mock_class, wu, rec_a, rec_b, total):
    instr_a = PaymentInstructionFactory(status=PaymentInstructionState.READY, fsp=wu, tag="tag")
    instr_b = PaymentInstructionFactory(status=PaymentInstructionState.READY, fsp=wu, tag="tag")
    PaymentRecordFactory.create_batch(rec_a, parent=instr_a, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create_batch(rec_b, parent=instr_b, status=PaymentRecordState.PENDING)

    instr_noise = PaymentInstructionFactory(status=PaymentInstructionState.OPEN)
    instr_noise_no_tag = PaymentInstructionFactory(status=PaymentInstructionState.OPEN)
    PaymentRecordFactory.create_batch(5, parent=instr_a, status=PaymentRecordState.CANCELLED)
    PaymentRecordFactory.create_batch(5, parent=instr_noise, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create_batch(5, parent=instr_noise_no_tag, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create_batch(5, parent__status=PaymentRecordState.PENDING, status=PaymentRecordState.PENDING)
    PaymentRecordFactory.create_batch(
        5,
        parent__status=PaymentRecordState.PENDING,
        status=PaymentRecordState.PENDING,
    )

    western_union_send_task(tag="tag", threshold=10)
    assert len(mock_class.mock_calls) == total


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@patch("hope_payment_gateway.apps.fsp.western_union.tasks.WesternUnionClient")
def test_update_corridors(mock_client):
    update_corridors()

    mock_client.return_value.das_countries_currencies.assert_called_once_with(create_corridors=True)


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@patch("hope_payment_gateway.apps.fsp.western_union.tasks.WesternUnionClient")
def test_update_templates(mock_client):
    corridor_data = [
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

    for corr in corridor_data:
        CorridorFactory.create(**corr)

    update_templates()

    assert mock_client.return_value.das_delivery_option_template.call_count == 2

    for corr in corridor_data:
        mock_client.return_value.das_delivery_option_template.assert_any_call(*corr.values())


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
@patch("hope_payment_gateway.apps.fsp.western_union.tasks.notify_records_to_fsp")
def test_western_union_notify(mock_notify):
    records = PaymentRecordFactory.create_batch(3, status=PaymentRecordState.PENDING)
    record_ids = [record.id for record in records]
    mock_notify.return_value = None
    western_union_notify(record_ids)

    mock_notify.assert_called_once_with(fqn(WesternUnionClient), record_ids)

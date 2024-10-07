from functools import partial
from typing import cast
from unittest.mock import MagicMock, call

from admin_extra_buttons.buttons import ChoiceButton, LinkButton
from admin_extra_buttons.utils import labelize
from django.contrib.admin import ModelAdmin
from django.test.client import Client
from django.urls import reverse
from pytest import mark
from pytest_mock import MockerFixture

from gateway.admin.utils import get_view_handler_url, get_change_model_url, find_button, assert_has_expected_choices, \
    get_change_model_list_url
from hope_payment_gateway.apps.gateway.admin import PaymentRecordAdmin, PaymentInstructionAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord, PaymentInstruction


def test_export_button(admin_client: Client, pi: PaymentInstruction) -> None:
    url = get_view_handler_url(PaymentInstruction, PaymentInstructionAdmin.export)
    response = admin_client.get(reverse(url, args=(pi.pk,)), )
    assert response.status_code == 200



def test_import_records_button(admin_client: Client, pi: PaymentInstruction) -> None:
    url = get_view_handler_url(PaymentInstruction, PaymentInstructionAdmin.import_records)
    response = admin_client.get(reverse(url, args=(pi.pk,)), )
    assert response.status_code == 200


def test_records_link(admin_client: Client, pi: PaymentInstruction) -> None:
    url = get_change_model_url(PaymentInstruction)
    response = admin_client.get(reverse(url, args=(pi.pk,)))
    link = cast(LinkButton, find_button(response.context, labelize(PaymentInstructionAdmin.records.name)))
    assert link
    assert link.href == f"{reverse(get_change_model_list_url(PaymentRecord))}?parent={pi.pk}"

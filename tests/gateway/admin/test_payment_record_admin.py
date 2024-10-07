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

from gateway.admin.utils import get_view_handler_url, get_change_model_url, find_button, assert_has_expected_choices
from hope_payment_gateway.apps.gateway.admin import PaymentRecordAdmin
from hope_payment_gateway.apps.gateway.models import PaymentRecord, PaymentInstruction


def test_get_queryset(mocker: MockerFixture) -> None:
    super_get_queryset = mocker.patch.object(ModelAdmin, "get_queryset")
    payment_record_admin = PaymentRecordAdmin(MagicMock(), MagicMock())
    request = MagicMock()

    payment_record_admin.get_queryset(request)

    assert super_get_queryset.call_count == 1
    super_get_queryset.assert_has_calls((
        call(request).select_related("parent__fsp"),
    ))


def test_western_union_choice(admin_client: Client, prl: PaymentRecord) -> None:
    url = get_change_model_url(PaymentRecord)
    response = admin_client.get(reverse(url, args=(prl.pk,)))
    button = cast(ChoiceButton, find_button(response.context, labelize(PaymentRecordAdmin.western_union.name)))
    assert button
    assert_has_expected_choices(button,
                                PaymentRecordAdmin.wu_prepare_payload,
                                PaymentRecordAdmin.wu_send_money_validation,
                                PaymentRecordAdmin.wu_send_money,
                                PaymentRecordAdmin.wu_search_request,
                                PaymentRecordAdmin.wu_cancel)


def test_moneygram_choice(admin_client: Client, prl: PaymentRecord) -> None:
    url = get_change_model_url(PaymentRecord)
    response = admin_client.get(reverse(url, args=(prl.pk,)))
    button = cast(ChoiceButton, find_button(response.context, labelize(PaymentRecordAdmin.moneygram.name)))
    assert button
    assert_has_expected_choices(button,
                                PaymentRecordAdmin.mg_prepare_payload,
                                PaymentRecordAdmin.mg_create_transaction)


def test_instruction_link(admin_client: Client, prl: PaymentRecord) -> None:
    url = get_change_model_url(PaymentRecord)
    response = admin_client.get(reverse(url, args=(prl.pk,)))
    link = cast(LinkButton, find_button(response.context, labelize(PaymentRecordAdmin.instruction.name)))
    assert link
    assert link.href == reverse(get_change_model_url(PaymentInstruction), args=(prl.parent_id,))


@mark.parametrize("url",
                  map(partial(get_view_handler_url, PaymentRecord), (
                      PaymentRecordAdmin.wu_prepare_payload,
                      PaymentRecordAdmin.wu_send_money_validation,
                      PaymentRecordAdmin.wu_send_money,
                      PaymentRecordAdmin.wu_search_request,
                      PaymentRecordAdmin.wu_cancel,
                      PaymentRecordAdmin.mg_prepare_payload,
                      PaymentRecordAdmin.mg_create_transaction,
                  )))
def test_views(admin_client: Client, prl: PaymentRecord, url: str) -> None:
    response = admin_client.get(reverse(url, args=(prl.pk,)), )
    assert response.status_code == 200

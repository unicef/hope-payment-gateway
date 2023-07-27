from django.urls import reverse

import responses

from hope_payment_gateway.apps.hope.models import PaymentRecord


# @_recorder.record(file_path="tests/western_union/endpoints/send_money_complete.yaml")
@responses.activate
def test_send_complete(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses.patch("https://wugateway2pi.westernunion.com/SendMoneyStore_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/send_money_complete.yaml")
    payment = PaymentRecord.objects.filter(status=PaymentRecord.STATUS_PENDING).first()
    url = reverse("admin:hope_paymentrecord_send_money_complete", args=[payment.pk])
    response = django_app.get(url, user=admin_user)
    assert response.status_code == 302
    payment.refresh_from_db()
    assert payment.status == PaymentRecord.STATUS_STORE_OK
    assert payment.transaction_reference_id == "0352466394"


# @_recorder.record(file_path="tests/western_union/endpoints/cancel_complete.yaml")
@responses.activate
def test_cancel_complete(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2HServiceService")
    responses.patch("https://wugateway2pi.westernunion.com/CancelSend_Service_H2HService")
    responses._add_from_file(file_path="tests/western_union/endpoints/cancel_complete.yaml")
    payment = PaymentRecord.objects.first()
    payment.transaction_reference_id = "0352466394"
    payment.status = PaymentRecord.STATUS_STORE_OK
    payment.save()
    url = reverse("admin:hope_paymentrecord_cancel_complete", args=[payment.pk])
    response = django_app.get(url, user=admin_user)
    payment.refresh_from_db()
    assert response.status_code == 302
    assert payment.status == PaymentRecord.STATUS_PENDING

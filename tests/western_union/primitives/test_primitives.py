from django.urls import reverse

import responses

from hope_payment_gateway.apps.hope.models import PaymentRecord


# @_recorder.record(file_path="tests/western_union/primitives/send_money_validation.yaml")
@responses.activate
def test_send_money_validation(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/primitives/send_money_validation.yaml")
    payment = PaymentRecord.objects.first()
    url = reverse("admin:hope_paymentrecord_send_money_validation", args=[payment.pk])
    response = django_app.get(url, user=admin_user)
    assert response.status_code == 200


# @_recorder.record(file_path="tests/western_union/primitives/send_money_store.yaml")
@responses.activate
def test_send_money_store(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/SendMoneyStore_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/primitives/send_money_store.yaml")
    payment = PaymentRecord.objects.first()
    url = reverse("admin:hope_paymentrecord_send_money_store", args=[payment.pk])
    response = django_app.get(url, user=admin_user)
    assert response.status_code == 200


# @_recorder.record(file_path="tests/western_union/primitives/send_money_complete.yaml")
@responses.activate
def test_send_complete(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses.patch("https://wugateway2pi.westernunion.com/SendMoneyStore_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/primitives/send_money_complete.yaml")
    payment = PaymentRecord.objects.first()
    url = reverse("admin:hope_paymentrecord_send_money_complete", args=[payment.pk])
    response = django_app.get(url, user=admin_user)
    assert response.status_code == 302


# @_recorder.record(file_path="tests/western_union/primitives/search_request.yaml")
@responses.activate
def test_search_request(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/primitives/search_request.yaml")
    payment = PaymentRecord.objects.first()
    payment.transaction_reference_id = "8552593921"
    payment.save()
    url = reverse("admin:hope_paymentrecord_search_request", args=[payment.pk])
    response = django_app.get(url, user=admin_user)
    assert response.status_code == 200


# @_recorder.record(file_path="tests/western_union/primitives/cancel_request.yaml")
@responses.activate
def test_cancel_request(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/CancelSend_Service_H2HService")
    responses._add_from_file(file_path="tests/western_union/primitives/cancel_request.yaml")
    payment = PaymentRecord.objects.first()
    payment.transaction_reference_id = "8552593921"
    payment.save()
    url = reverse("admin:hope_paymentrecord_cancel_request", args=[payment.pk])
    response = django_app.get(url, user=admin_user)
    assert response.status_code == 200


# @_recorder.record(file_path="tests/western_union/primitives/cancel_complete.yaml")
@responses.activate
def test_cancel_complete(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/Search_Service_H2HServiceService")
    responses.patch("https://wugateway2pi.westernunion.com/CancelSend_Service_H2HService")
    responses._add_from_file(file_path="tests/western_union/primitives/cancel_complete.yaml")
    payment = PaymentRecord.objects.first()
    payment.transaction_reference_id = "0352466394"
    payment.save()
    url = reverse("admin:hope_paymentrecord_cancel_complete", args=[payment.pk])
    response = django_app.get(url, user=admin_user)
    assert response.status_code == 302

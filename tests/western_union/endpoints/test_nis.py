from pathlib import Path

from django.urls import reverse

import responses

from ...factories import PaymentRecordFactory


def test_push_notification(django_app, admin_user):
    xml = open(Path(__file__).parent / "push_notification.xml", "r")
    url = reverse("western_union:pay-notification-view")
    headers = {"Content-Type": "application/xml"}
    django_app.post(url, xml.read(), user=admin_user, headers=headers)


@responses.activate
def test_nis_notification_rejected(django_app, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/nis_notification_rejected.yaml")
    xml = open(Path(__file__).parent / "push_notification.xml", "r")
    PaymentRecordFactory(record_code="2323589126420060", status="TRANSFERRED_TO_FSP")
    url = reverse("western_union:nis-notification-view")
    headers = {"Content-Type": "application/xml"}
    django_app.post(url, xml.read(), user=admin_user, headers=headers)

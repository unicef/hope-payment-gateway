from pathlib import Path

from django.urls import reverse

from ...factories import PaymentRecordLogFactory


def test_push_notification(django_app, admin_user):
    xml = open(Path(__file__).parent / "push_notification.xml", "r")
    url = reverse("western_union:pay-notification-view")
    headers = {"Content-Type": "application/xml"}
    django_app.post(url, xml.read(), user=admin_user, headers=headers)


def test_nis_notification(django_app, admin_user):
    xml = open(Path(__file__).parent / "push_notification.xml", "r")
    PaymentRecordLogFactory(record_code="2323589126420060", status="TRANSFERRED_TO_FSP")
    url = reverse("western_union:nis-notification-view")
    headers = {"Content-Type": "application/xml"}
    django_app.post(url, xml.read(), user=admin_user, headers=headers)

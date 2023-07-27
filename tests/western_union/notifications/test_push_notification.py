from django.urls import reverse
from pathlib import Path
from hope_payment_gateway.apps.hope.models import PaymentRecord
import xml.etree.ElementTree as ET


def test_push_notification(django_app, admin_user):
    # with open("push_notification.xml") as xml:
    directory = Path(__file__).parent
    xml = open(directory / "push_notification.xml", "r")
    payload = ET.parse(xml)
    url = reverse("western_union:pay-notification-view")
    django_app.post(url, payload, user=admin_user)

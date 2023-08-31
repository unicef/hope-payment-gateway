from pathlib import Path

from django.urls import reverse


def test_push_notification(django_app, admin_user):
    # with open("push_notification.xml") as xml:
    directory = Path(__file__).parent
    xml = open(directory / "push_notification.xml", "r")
    url = reverse("western_union:pay-notification-view")
    headers = {"Content-Type": "application/xml"}
    django_app.post(url, xml.read(), user=admin_user, headers=headers)

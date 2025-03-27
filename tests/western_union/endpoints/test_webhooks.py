from pathlib import Path

import pytest
import responses
from django.urls import reverse
from factories import PaymentRecordFactory


@responses.activate
@pytest.mark.django_db
def test_nis_notification_rejected(wu, api_client, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses._add_from_file(file_path="tests/western_union/endpoints/nis_notification_rejected.yaml")
    with open(Path(__file__).parent / "push_notification.xml", "r") as xml:
        PaymentRecordFactory(record_code="2323589126420060", status="TRANSFERRED_TO_FSP", parent__fsp=wu)
        url = reverse("western_union:nis-notification-xml-view")
        data = xml.read()
        api_client.post(url, data=data, user=admin_user, content_type="application/xml")

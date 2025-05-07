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
        response = api_client.post(url, data=data, user=admin_user, content_type="application/xml")

        assert response.status_code == 400
        assert "cannot_find_transaction" in response.data


def test_nis_notification_xml_with_invalid_request(api_client, admin_user):
    url = reverse("western_union:nis-notification-xml-view")
    response = api_client.get(url, data={}, user=admin_user, content_type="application/xml")

    assert response.status_code == 400
    assert response.data.get("invalid_request") is not None


@pytest.mark.django_db
def test_nis_notification_xml_with_header_and_invalid_request(wu, api_client, admin_user):
    url = reverse("western_union:nis-notification-xml-view")
    with open(Path(__file__).parent / "invalid_notification.xml", "r") as xml:
        response = api_client.generic(
            method="GET", path=url, data=xml.read(), content_type="application/xml", user=admin_user
        )

    assert response.status_code == 400
    assert "invalid_request" in response.data
    assert "nis-notification-request" in response.data["invalid_request"]
    assert "invalid_notification" in response.data["invalid_request"]


@pytest.mark.django_db
def test_nis_notification_xml_with_valid_request(wu, api_client, admin_user):
    url = reverse("western_union:nis-notification-xml-view")
    with open(Path(__file__).parent / "push_notification.xml", "r") as xml:
        response = api_client.generic(
            method="GET", path=url, data=xml.read(), content_type="application/xml", user=admin_user
        )

    assert response.status_code == 200
    assert "transaction_id" in response.data
    assert str(response.data["transaction_id"]) == "2323589126420060"
    assert "money_transfer_control" in response.data
    assert "payment_details" in response.data
    assert "notification_type" in response.data


@pytest.mark.django_db
def test_nis_notification_xml_post_with_invalid_request(wu, api_client, admin_user):
    url = reverse("western_union:nis-notification-xml-view")
    with open(Path(__file__).parent / "invalid_notification.xml", "r") as xml:
        response = api_client.generic(
            method="POST", path=url, data=xml.read(), content_type="application/xml", user=admin_user
        )

    assert response.status_code == 400
    assert "invalid_request" in response.data
    assert "nis-notification-request" in response.data["invalid_request"]
    assert "invalid_notification" in response.data["invalid_request"]


@pytest.mark.django_db
def test_nis_notification_xml_post_with_validation_error(wu, api_client, admin_user, monkeypatch):
    url = reverse("western_union:nis-notification-xml-view")

    def mock_prepare(*args, **kwargs):
        from zeep.exceptions import ValidationError

        raise ValidationError("Invalid XML structure")

    monkeypatch.setattr(
        "hope_payment_gateway.apps.fsp.western_union.api.client.WesternUnionClient.prepare", mock_prepare
    )

    with open(Path(__file__).parent / "push_notification.xml", "r") as xml:
        response = api_client.generic(
            method="POST", path=url, data=xml.read(), content_type="application/xml", user=admin_user
        )

    assert response.status_code == 400
    assert "validation_error" in response.data
    assert "Invalid XML structure" in response.data["validation_error"]

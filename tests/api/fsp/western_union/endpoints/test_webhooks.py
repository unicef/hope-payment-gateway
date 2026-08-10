from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import responses
from constance.test import override_config
from django.urls import reverse
from factories import PaymentRecordFactory
from viewflow.fsm import TransitionNotAllowed
from zeep.exceptions import ValidationError


@responses.activate
@pytest.mark.django_db
def test_nis_notification_rejected(wu, api_client, admin_user):
    responses.patch("https://wugateway2pi.westernunion.com/SendmoneyValidation_Service_H2H")
    responses._add_from_file(file_path="tests/api/fsp/western_union/endpoints/nis_notification_rejected.yaml")
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
        raise ValidationError("Invalid XML structure")

    monkeypatch.setattr("hope_payment_gateway.api.western_union.client.WesternUnionClient.prepare", mock_prepare)

    with open(Path(__file__).parent / "push_notification.xml", "r") as xml:
        response = api_client.generic(
            method="POST", path=url, data=xml.read(), content_type="application/xml", user=admin_user
        )

    assert response.status_code == 400
    assert "validation_error" in response.data
    assert "Invalid XML structure" in response.data["validation_error"]


def _test_nis_notification_xml_post_success(mock_flow, wu, api_client, admin_user, file_name):
    url = reverse("western_union:nis-notification-xml-view")
    payment_record = PaymentRecordFactory(fsp_code="2323589126420060", status="TRANSFERRED_TO_FSP", parent__fsp=wu)

    mock_instance = MagicMock()
    mock_flow.return_value = mock_instance

    with open(Path(__file__).parent / file_name, "r") as xml:
        response = api_client.generic(
            method="POST", path=url, data=xml.read(), content_type="application/xml", user=admin_user
        )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/xml"
    mock_instance.confirm.assert_called_once()

    payment_record.refresh_from_db()
    assert payment_record.success is True
    assert payment_record.message == "Transferred to Beneficiary by Push Notification"
    assert payment_record.payout_amount == 8500.00  # from XML expected_payout_amount
    assert payment_record.payout_date.strftime("%Y-%m-%d") == "2023-08-23"
    assert str(payment_record.fsp_data["mtcn"]) == "3634673433"
    assert "push_notification" in payment_record.fsp_data
    assert len(payment_record.fsp_data["push_notification"]) == 1


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.api.western_union.views.webhook.PaymentRecordFlow")
def test_nis_notification_xml_post_success(mock_flow, wu, api_client, admin_user):
    _test_nis_notification_xml_post_success(mock_flow, wu, api_client, admin_user, file_name="push_notification.xml")


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.api.western_union.views.webhook.PaymentRecordFlow")
def test_nis_notification_xml_post_success_apn(mock_flow, wu, api_client, admin_user):
    _test_nis_notification_xml_post_success(
        mock_flow, wu, api_client, admin_user, file_name="push_notification_success_apn.xml"
    )


def _test_nis_notification_xml_post_cancel(mock_flow, wu, api_client, admin_user, file_name):
    url = reverse("western_union:nis-notification-xml-view")
    payment_record = PaymentRecordFactory(fsp_code="2323589126420060", status="TRANSFERRED_TO_FSP", parent__fsp=wu)

    mock_instance = MagicMock()
    mock_flow.return_value = mock_instance

    with open(Path(__file__).parent / file_name, "r") as xml:
        response = api_client.generic(
            method="POST", path=url, data=xml.read(), content_type="application/xml", user=admin_user
        )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/xml"
    mock_instance.cancel.assert_called_once()

    payment_record.refresh_from_db()
    assert payment_record.success is False
    assert "Cancelled by FSP:" in payment_record.message


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.api.western_union.views.webhook.PaymentRecordFlow")
def test_nis_notification_xml_post_cancel(mock_flow, wu, api_client, admin_user):
    _test_nis_notification_xml_post_cancel(
        mock_flow, wu, api_client, admin_user, file_name="push_notification_cancel.xml"
    )


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.api.western_union.views.webhook.PaymentRecordFlow")
def test_nis_notification_xml_post_reject_apn(mock_flow, wu, api_client, admin_user):
    _test_nis_notification_xml_post_cancel(
        mock_flow, wu, api_client, admin_user, file_name="push_notification_reject_apn.xml"
    )


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.api.western_union.views.webhook.PaymentRecordFlow")
def test_nis_notification_xml_post_purged(mock_flow, wu, api_client, admin_user):
    url = reverse("western_union:nis-notification-xml-view")
    payment_record = PaymentRecordFactory(fsp_code="2323589126420060", status="TRANSFERRED_TO_FSP", parent__fsp=wu)

    mock_instance = MagicMock()
    mock_flow.return_value = mock_instance

    with open(Path(__file__).parent / "push_notification_purged.xml", "r") as xml:
        response = api_client.generic(
            method="POST", path=url, data=xml.read(), content_type="application/xml", user=admin_user
        )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/xml"
    mock_instance.purge.assert_called_once()

    payment_record.refresh_from_db()
    assert payment_record.success is False
    assert "Purged by FSP:" in payment_record.message


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.api.western_union.views.webhook.PaymentRecordFlow")
def test_nis_notification_xml_post_refund(mock_flow, wu, api_client, admin_user):
    url = reverse("western_union:nis-notification-xml-view")
    payment_record = PaymentRecordFactory(fsp_code="2323589126420060", status="TRANSFERRED_TO_FSP", parent__fsp=wu)

    mock_instance = MagicMock()
    mock_flow.return_value = mock_instance

    with open(Path(__file__).parent / "push_notification_refund.xml", "r") as xml:
        response = api_client.generic(
            method="POST", path=url, data=xml.read(), content_type="application/xml", user=admin_user
        )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/xml"
    mock_instance.refund.assert_called_once()

    payment_record.refresh_from_db()
    assert payment_record.success is False
    assert "Refund by FSP:" in payment_record.message


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.api.western_union.views.webhook.PaymentRecordFlow")
def test_nis_notification_xml_post_error(mock_flow, wu, api_client, admin_user):
    url = reverse("western_union:nis-notification-xml-view")
    payment_record = PaymentRecordFactory(fsp_code="2323589126420060", status="TRANSFERRED_TO_FSP", parent__fsp=wu)

    mock_instance = MagicMock()
    mock_flow.return_value = mock_instance

    with open(Path(__file__).parent / "push_notification_error.xml", "r") as xml:
        response = api_client.generic(
            method="POST", path=url, data=xml.read(), content_type="application/xml", user=admin_user
        )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/xml"
    mock_instance.fail.assert_called_once()

    payment_record.refresh_from_db()
    assert payment_record.success is False
    assert "Error in Notification:" in payment_record.message


def _test_nis_notification_xml_post_transition_not_allowed(mock_flow, wu, api_client, admin_user, method, file_name):
    url = reverse("western_union:nis-notification-xml-view")
    PaymentRecordFactory(fsp_code="2323589126420060", status="TRANSFERRED_TO_FSP", parent__fsp=wu)

    mock_instance = MagicMock()
    getattr(mock_instance, method).side_effect = TransitionNotAllowed()
    mock_flow.return_value = mock_instance

    with open(Path(__file__).parent / file_name, "r") as xml:
        response = api_client.generic(
            method="POST", path=url, data=xml.read(), content_type="application/xml", user=admin_user
        )

    assert response.status_code == 400
    assert response["Content-Type"] == "application/xml; charset=utf-8"
    getattr(mock_instance, method).assert_called_once()


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.api.western_union.views.webhook.PaymentRecordFlow")
def test_nis_notification_xml_post_transition_not_allowed_confirm(mock_flow, wu, api_client, admin_user):
    _test_nis_notification_xml_post_transition_not_allowed(
        mock_flow, wu, api_client, admin_user, method="confirm", file_name="push_notification.xml"
    )


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.api.western_union.views.webhook.PaymentRecordFlow")
def test_nis_notification_xml_post_transition_not_allowed_purge(mock_flow, wu, api_client, admin_user):
    _test_nis_notification_xml_post_transition_not_allowed(
        mock_flow, wu, api_client, admin_user, method="purge", file_name="push_notification_purged.xml"
    )


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.api.western_union.views.webhook.PaymentRecordFlow")
def test_nis_notification_xml_post_transition_not_allowed_refund(mock_flow, wu, api_client, admin_user):
    _test_nis_notification_xml_post_transition_not_allowed(
        mock_flow, wu, api_client, admin_user, method="refund", file_name="push_notification_refund.xml"
    )


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.api.western_union.views.webhook.PaymentRecordFlow")
def test_nis_notification_xml_post_unpay(mock_flow, wu, api_client, admin_user):
    url = reverse("western_union:nis-notification-xml-view")
    payment_record = PaymentRecordFactory(
        fsp_code="2323589126420060", status="TRANSFERRED_TO_BENEFICIARY", parent__fsp=wu
    )

    mock_instance = MagicMock()
    mock_flow.return_value = mock_instance

    with open(Path(__file__).parent / "push_notification_unpay.xml", "r") as xml:
        response = api_client.generic(
            method="POST", path=url, data=xml.read(), content_type="application/xml", user=admin_user
        )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/xml"
    mock_instance.unpay.assert_called_once()

    payment_record.refresh_from_db()
    assert payment_record.success is False
    assert "Unpay by FSP:" in payment_record.message


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.api.western_union.views.webhook.PaymentRecordFlow")
def test_nis_notification_xml_post_transition_not_allowed_unpay(mock_flow, wu, api_client, admin_user):
    _test_nis_notification_xml_post_transition_not_allowed(
        mock_flow, wu, api_client, admin_user, method="unpay", file_name="push_notification_unpay.xml"
    )


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.api.western_union.views.webhook.PaymentRecordFlow")
def test_nis_notification_xml_post_overridden_unpay(mock_flow, wu, api_client, admin_user, monkeypatch):
    monkeypatch.setattr("hope_payment_gateway.api.western_union.views.webhook.UNPAY", "OVERRIDDEN_UNPAY_CODE")
    url = reverse("western_union:nis-notification-xml-view")
    payment_record = PaymentRecordFactory(
        fsp_code="2323589126420060", status="TRANSFERRED_TO_BENEFICIARY", parent__fsp=wu
    )

    mock_instance = MagicMock()
    mock_flow.return_value = mock_instance

    with open(Path(__file__).parent / "push_notification_overridden_unpay.xml", "r") as xml:
        response = api_client.generic(
            method="POST", path=url, data=xml.read(), content_type="application/xml", user=admin_user
        )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/xml"
    mock_instance.unpay.assert_called_once()

    payment_record.refresh_from_db()
    assert payment_record.success is False
    assert "Unpay by FSP:" in payment_record.message


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.api.western_union.views.webhook.PaymentRecordFlow")
def test_nis_notification_xml_post_transfer_to_fsp(mock_flow, wu, api_client, admin_user):
    url = reverse("western_union:nis-notification-xml-view")
    payment_record = PaymentRecordFactory(fsp_code="2323589126420060", status="PENDING", parent__fsp=wu)

    mock_instance = MagicMock()
    mock_flow.return_value = mock_instance

    with open(Path(__file__).parent / "push_notification_transfer_to_fsp.xml", "r") as xml:
        response = api_client.generic(
            method="POST", path=url, data=xml.read(), content_type="application/xml", user=admin_user
        )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/xml"
    mock_instance.store.assert_called_once()

    payment_record.refresh_from_db()
    assert payment_record.success is False
    assert "Store by FSP:" in payment_record.message
    assert "push_notification" in payment_record.fsp_data
    assert len(payment_record.fsp_data["push_notification"]) == 1


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.api.western_union.views.webhook.PaymentRecordFlow")
def test_nis_notification_xml_post_transfer_to_fsp_not_pending(mock_flow, wu, api_client, admin_user):
    url = reverse("western_union:nis-notification-xml-view")
    PaymentRecordFactory(fsp_code="2323589126420060", status="TRANSFERRED_TO_FSP", parent__fsp=wu)

    mock_instance = MagicMock()
    mock_flow.return_value = mock_instance

    with open(Path(__file__).parent / "push_notification_transfer_to_fsp.xml", "r") as xml:
        response = api_client.generic(
            method="POST", path=url, data=xml.read(), content_type="application/xml", user=admin_user
        )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/xml"
    mock_instance.store.assert_not_called()

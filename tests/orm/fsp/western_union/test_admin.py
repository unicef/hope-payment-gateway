import pytest
from constance import config
from constance.test import override_config
from django.contrib.auth.models import Permission
from django.urls import reverse
from unittest.mock import patch

from tests.factories.payment import CorridorFactory


@pytest.fixture
def superuser(db):
    from tests.factories.user import SuperUserFactory

    return SuperUserFactory()


@pytest.fixture
def user_with_ds_perm(user):
    perm = Permission.objects.get(codename="das_delivery_services", content_type__app_label="western_union")
    user.user_permissions.add(perm)
    return user


@pytest.fixture
def user_with_dot_perm(user):
    perm = Permission.objects.get(codename="das_delivery_option_template", content_type__app_label="western_union")
    user.user_permissions.add(perm)
    return user


@pytest.fixture
def us_corridor():
    return CorridorFactory(destination_country="US", destination_currency="USD", template_code="1234")


@pytest.fixture
def ph_corridor():
    return CorridorFactory(destination_country="PH", destination_currency="PHP", template_code="4061")


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.apps.fsp.western_union.admin.requests_request")
def test_request_button(mock_requests_request, superuser, client):
    mock_requests_request.return_value = {"title": 200, "content": "<ok/>"}
    client.force_login(superuser)
    url = reverse("admin:western_union_corridor_request")
    response = client.get(url)
    assert response.status_code == 200
    mock_requests_request.assert_called_once()


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.apps.fsp.western_union.admin.WesternUnionClient")
def test_delivery_services(mock_wu_cls, user_with_ds_perm, us_corridor, client):
    mock_instance = mock_wu_cls.return_value
    mock_instance.das_delivery_services.return_value = {"title": "GetDeliveryServices"}

    client.force_login(user_with_ds_perm)
    url = reverse("admin:western_union_corridor_delivery_services", args=[us_corridor.pk])
    response = client.get(url)

    assert response.status_code == 200
    ctx = response.context_data
    assert "US" in ctx["msg"]
    assert "USD" in ctx["msg"]
    mock_instance.das_delivery_services.assert_called_once_with(
        "US",
        "USD",
        config.WESTERN_UNION_DAS_IDENTIFIER,
        config.WESTERN_UNION_DAS_COUNTER,
    )


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.apps.fsp.western_union.admin.WesternUnionClient")
def test_delivery_services_with_query_params(mock_wu_cls, user_with_ds_perm, us_corridor, client):
    mock_instance = mock_wu_cls.return_value
    mock_instance.das_delivery_services.return_value = {"title": "GetDeliveryServices"}

    client.force_login(user_with_ds_perm)
    url = reverse("admin:western_union_corridor_delivery_services", args=[us_corridor.pk])
    url += "?destination_country=PH&destination_currency=PHP&identifier=MY_ID&counter_id=MY_COUNTER"
    response = client.get(url)

    assert response.status_code == 200
    ctx = response.context_data
    assert "PH" in ctx["msg"]
    assert "PHP" in ctx["msg"]
    mock_instance.das_delivery_services.assert_called_once_with("PH", "PHP", "MY_ID", "MY_COUNTER")


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.apps.fsp.western_union.admin.WesternUnionClient")
def test_delivery_option_template(mock_wu_cls, user_with_dot_perm, ph_corridor, client):
    mock_instance = mock_wu_cls.return_value
    mock_instance.das_delivery_option_template.return_value = {"title": "GetDeliveryOptionTemplate"}

    client.force_login(user_with_dot_perm)
    url = reverse("admin:western_union_corridor_delivery_option_template", args=[ph_corridor.pk])
    response = client.get(url)

    assert response.status_code == 200
    ctx = response.context_data
    assert "PH" in ctx["msg"]
    assert "PHP" in ctx["msg"]
    assert "4061" in ctx["msg"]
    mock_instance.das_delivery_option_template.assert_called_once_with(
        "PH",
        "PHP",
        config.WESTERN_UNION_DAS_IDENTIFIER,
        config.WESTERN_UNION_DAS_COUNTER,
        "4061",
    )


@pytest.mark.django_db
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
@patch("hope_payment_gateway.apps.fsp.western_union.admin.WesternUnionClient")
def test_delivery_option_template_with_query_params(mock_wu_cls, user_with_dot_perm, ph_corridor, client):
    mock_instance = mock_wu_cls.return_value
    mock_instance.das_delivery_option_template.return_value = {"title": "GetDeliveryOptionTemplate"}

    client.force_login(user_with_dot_perm)
    url = reverse("admin:western_union_corridor_delivery_option_template", args=[ph_corridor.pk])
    url += "?destination_country=US&destination_currency=USD&identifier=MY_ID&counter_id=MY_COUNTER"
    response = client.get(url)

    assert response.status_code == 200
    ctx = response.context_data
    assert "US" in ctx["msg"]
    assert "USD" in ctx["msg"]
    mock_instance.das_delivery_option_template.assert_called_once_with("US", "USD", "MY_ID", "MY_COUNTER", "4061")

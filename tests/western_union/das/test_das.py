from django.urls import reverse

import pytest
import responses
from constance.test import override_config

# from responses import _recorder
# @_recorder.record(file_path="tests/western_union/das/das_countries_currencies.yaml")


@pytest.mark.parametrize(
    "endpoint",
    [
        "das_countries_currencies",
        "das_origination_currencies",
        "das_destination_currencies",
        "das_destination_countries",
        "das_delivery_services",
        "das_delivery_option_template",
    ],
)
@responses.activate
@override_config(WESTERN_UNION_VENDOR_NUMBER="12345")
def test_das(django_app, admin_user, endpoint, wu):
    responses.patch("https://wugateway2pi.westernunion.com/DAS_Service_H2H")
    responses._add_from_file(file_path=f"tests/western_union/das/{endpoint}.yaml")
    url = reverse(f"admin:western_union_corridor_{endpoint}")
    response = django_app.get(url, user=admin_user)
    assert response.status_code == 200

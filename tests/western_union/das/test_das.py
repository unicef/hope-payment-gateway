from django.urls import reverse

import pytest
import responses

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
def test_das(django_app, admin_user, endpoint):
    responses.patch("https://wugateway2pi.westernunion.com/DAS_Service_H2H")
    responses._add_from_file(file_path=f"tests/western_union/cassettes/{endpoint}.yaml")
    url = reverse(f"admin:western_union_corridor_{endpoint}")
    response = django_app.get(url, user=admin_user)
    assert response.status_code == 200

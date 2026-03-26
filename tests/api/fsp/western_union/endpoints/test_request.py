import responses

from hope_payment_gateway.api.western_union.views.request import requests_request


@responses.activate
def test_client_request():
    responses.patch("https://wugateway2pi.westernunion.com/")
    responses._add_from_file(file_path="tests/api/fsp/western_union/endpoints/request.yaml")
    requests_request()

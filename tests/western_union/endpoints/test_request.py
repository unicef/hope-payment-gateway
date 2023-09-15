import responses

from hope_payment_gateway.apps.western_union.endpoints.request import requests_request


@responses.activate
def test_client_request():
    responses.patch("https://wugateway2pi.westernunion.com/")
    responses._add_from_file(file_path="tests/western_union/endpoints/request.yaml")
    resp = requests_request()
    print(resp)

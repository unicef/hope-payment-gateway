from hope_payment_gateway.apps.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.western_union.endpoints.utils import eur, unicef, usd


def das_countries_currencies():
    payload = {
        "name": "GetCountriesCurrencies",
        "channel": unicef,
        "foreign_remote_system": usd,
        "filters": {
            "queryfilter1": "en",
            "queryfilter2": "US USD",  # destination
        },
    }
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    return client.response_context("DAS_Service", payload)


def das_origination_currencies():
    payload = {
        "name": "GetOriginationCurrencies",
        "channel": unicef,
        "foreign_remote_system": usd,
        "filters": {
            "queryfilter1": "en",
        },
    }
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    return client.response_context("DAS_Service", payload)


def das_destination_countries():
    payload = {
        "name": "GetDestinationCountries",
        "channel": unicef,
        "foreign_remote_system": usd,
        "filters": {"queryfilter1": "en", "queryfilter2": "US USD"},
    }
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    return client.response_context("DAS_Service", payload)


def das_destination_currencies(destination_country):
    payload = {
        "name": "GetDestinationCurrencies",
        "channel": unicef,
        "foreign_remote_system": usd,
        "filters": {
            "queryfilter1": "en",
            "queryfilter2": "US USD",  # origination country
            "queryfilter3": destination_country,
        },
    }
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    return client.response_context("DAS_Service", payload)


def das_delivery_services(destination_country, destination_currency):
    payload = {
        "name": "GetDeliveryServices",
        "channel": unicef,
        "foreign_remote_system": eur,
        "filters": {
            "queryfilter1": "en",
            "queryfilter2": "US USD",  # origination country, currency
            "queryfilter3": f"{destination_country} {destination_currency}",
            "queryfilter4": "ALL",
        },
    }
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    return client.response_context("DAS_Service", payload)


def das_delivery_option_template(destination_country, destination_currency, template_code):
    payload = {
        "name": "GetDeliveryOptionTemplate",
        "channel": unicef,
        "foreign_remote_system": usd,
        "filters": {
            "queryfilter1": "en",
            "queryfilter2": f"{destination_country} {destination_currency}",  # destination
            "queryfilter3": template_code,  # coming delivery services endpoint ***
            "queryfilter8": "XPath",
        },
    }
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    return client.response_context("DAS_Service", payload)

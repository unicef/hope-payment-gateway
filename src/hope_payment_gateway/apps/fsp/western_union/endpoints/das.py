from constance import config

from hope_payment_gateway.apps.fsp.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.endpoints.config import unicef


def create_usd():
    return {
        "identifier": config.WESTERN_UNION_DAS_IDENTIFIER,
        "reference_no": "N/A",
        "counter_id": config.WESTERN_UNION_DAS_COUNTER,
    }


def das_countries_currencies():
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    payload = {
        "name": "GetCountriesCurrencies",
        "channel": unicef,
        "foreign_remote_system": create_usd(),
        "filters": {
            "queryfilter1": "en",
            "queryfilter2": "US USD",  # destination
        },
    }
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    return client.response_context("DAS_Service", payload, "DAS_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")


def das_origination_currencies():
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    payload = {
        "name": "GetOriginationCurrencies",
        "channel": unicef,
        "foreign_remote_system": create_usd(),
        "filters": {
            "queryfilter1": "en",
        },
    }
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    return client.response_context("DAS_Service", payload, "DAS_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")


def das_destination_countries():
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    payload = {
        "name": "GetDestinationCountries",
        "channel": unicef,
        "foreign_remote_system": create_usd(),
        "filters": {"queryfilter1": "en", "queryfilter2": "US USD"},
    }
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    return client.response_context("DAS_Service", payload, "DAS_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")


def das_destination_currencies(destination_country):
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    payload = {
        "name": "GetDestinationCurrencies",
        "channel": unicef,
        "foreign_remote_system": create_usd(),
        "filters": {
            "queryfilter1": "en",
            "queryfilter2": "US USD",  # origination country
            "queryfilter3": destination_country,
        },
    }
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    return client.response_context("DAS_Service", payload, "DAS_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")


def das_delivery_services(destination_country, destination_currency):
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    payload = {
        "name": "GetDeliveryServices",
        "channel": unicef,
        "foreign_remote_system": create_usd(),
        "filters": {
            "queryfilter1": "en",
            "queryfilter2": "US USD",  # origination country, currency
            "queryfilter3": f"{destination_country} {destination_currency}",
            "queryfilter4": "ALL",
        },
    }
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    return client.response_context("DAS_Service", payload, "DAS_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")


def das_delivery_option_template(destination_country, destination_currency, template_code):
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    payload = {
        "name": "GetDeliveryOptionTemplate",
        "channel": unicef,
        "foreign_remote_system": create_usd(),
        "filters": {
            "queryfilter1": "en",
            "queryfilter2": f"{destination_country} {destination_currency}",  # destination
            "queryfilter3": template_code,  # coming delivery services endpoint ***
            "queryfilter8": "XPath",
        },
    }
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    return client.response_context("DAS_Service", payload, "DAS_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")

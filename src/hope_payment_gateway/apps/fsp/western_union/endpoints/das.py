from constance import config

from hope_payment_gateway.apps.fsp.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.endpoints.config import unicef
from hope_payment_gateway.apps.fsp.western_union.models import Corridor


def create_usd():
    return {
        "identifier": config.WESTERN_UNION_DAS_IDENTIFIER,
        "reference_no": "N/A",
        "counter_id": config.WESTERN_UNION_DAS_COUNTER,
    }


def das_countries_currencies(create_corridors=False):
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    more_data, qf3, qf4, response = True, "", "", None

    while more_data:
        payload = {
            "name": "GetCountriesCurrencies",
            "channel": unicef,
            "foreign_remote_system": create_usd(),
            "filters": {
                "queryfilter1": "en",
                "queryfilter2": "US USD",  # destination
                "queryfilter3": qf3,
                "queryfilter4": qf4,
            },
        }
        client = WesternUnionClient("DAS_Service_H2HService.wsdl")
        response = client.response_context("DAS_Service", payload, "DAS_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")

        context = response["content"]["MTML"]["REPLY"]["DATA_CONTEXT"]
        more_data = context["HEADER"]["DATA_MORE"] == "Y"

        if create_corridors:
            for country_currency in context["RECORDSET"]["GETCOUNTRIESCURRENCIES"]:
                country = country_currency["ISO_COUNTRY_CD"]
                currency = country_currency["CURRENCY_CD"]
                qf3 = country_currency["COUNTRY_LONG"]
                qf4 = country_currency["CURRENCY_NAME"]

                das_delivery_services(country, currency, create_corridors=create_corridors)
        else:
            more_data = False  # skip we want only 1st page
    return response


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


def das_delivery_services(destination_country, destination_currency, create_corridors=False):
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
    response = client.response_context("DAS_Service", payload, "DAS_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")

    context = response["content"]["MTML"]["REPLY"]["DATA_CONTEXT"]["RECORDSET"]
    if create_corridors and context:
        for ds in context["GETDELIVERYSERVICES"]:
            if ds["SVC_CODE"] == "800":
                Corridor.objects.get_or_create(
                    destination_country=destination_country,
                    destination_currency=destination_currency,
                    defaults={
                        "description": f"{destination_country}: {destination_currency}",
                        "template_code": ds["TEMPLT"],
                    },
                )

    return response


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

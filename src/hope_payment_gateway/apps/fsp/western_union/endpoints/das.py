from constance import config

from hope_payment_gateway.apps.fsp.western_union.endpoints.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.models import Corridor, ServiceProviderCode
from hope_payment_gateway.apps.gateway.models import FinancialServiceProvider


def das_countries_currencies(identifier, counter_id, create_corridors=False):
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    more_data, qf3, qf4, response = True, "", "", None
    payload = FinancialServiceProvider.objects.get(
        vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
    ).configuration.copy()

    while more_data:
        payload.pop("sender", None)
        payload.update(
            {
                "name": "GetCountriesCurrencies",
                "foreign_remote_system": {"identifier": identifier, "counter_id": counter_id, "reference_no": "N/A"},
                "filters": {
                    "queryfilter1": "en",
                    "queryfilter2": "US USD",  # destination
                    "queryfilter3": qf3,
                    "queryfilter4": qf4,
                },
            }
        )
        client = WesternUnionClient("DAS_Service_H2HService.wsdl")
        response = client.response_context("DAS_Service", payload, "DAS_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")
        if isinstance(response["content"], dict):
            context = response["content"]["MTML"]["REPLY"]["DATA_CONTEXT"]
            more_data = context["HEADER"]["DATA_MORE"] == "Y"

            if create_corridors:
                for country_currency in context["RECORDSET"]["GETCOUNTRIESCURRENCIES"]:
                    country = country_currency["ISO_COUNTRY_CD"]
                    currency = country_currency["CURRENCY_CD"]
                    qf3 = country_currency["COUNTRY_LONG"]
                    qf4 = country_currency["CURRENCY_NAME"]

                    das_delivery_services(country, currency, identifier, counter_id, create_corridors=create_corridors)
            else:
                more_data = False  # skip we want only 1st page
        else:
            more_data = False  # skip we want only 1st page
    return response


def das_origination_currencies(identifier, counter_id):
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    payload = FinancialServiceProvider.objects.get(
        vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
    ).configuration.copy()
    payload.pop("sender", None)
    payload.update(
        {
            "name": "GetOriginationCurrencies",
            "foreign_remote_system": {"identifier": identifier, "counter_id": counter_id, "reference_no": "N/A"},
            "filters": {
                "queryfilter1": "en",
            },
        }
    )
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    return client.response_context("DAS_Service", payload, "DAS_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")


def das_destination_countries(identifier, counter_id):
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    payload = FinancialServiceProvider.objects.get(
        vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
    ).configuration.copy()
    payload.pop("sender", None)
    payload.update(
        {
            "name": "GetDestinationCountries",
            "foreign_remote_system": {"identifier": identifier, "counter_id": counter_id, "reference_no": "N/A"},
            "filters": {"queryfilter1": "en", "queryfilter2": "US USD"},
        }
    )
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    return client.response_context("DAS_Service", payload, "DAS_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")


def das_destination_currencies(destination_country, identifier, counter_id):
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    payload = FinancialServiceProvider.objects.get(
        vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
    ).configuration.copy()
    payload.pop("sender", None)
    payload.update(
        {
            "name": "GetDestinationCurrencies",
            "foreign_remote_system": {"identifier": identifier, "counter_id": counter_id, "reference_no": "N/A"},
            "filters": {
                "queryfilter1": "en",
                "queryfilter2": "US USD",  # origination country
                "queryfilter3": destination_country,
            },
        }
    )
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    return client.response_context("DAS_Service", payload, "DAS_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")


def das_delivery_services(destination_country, destination_currency, identifier, counter_id, create_corridors=False):
    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    payload = FinancialServiceProvider.objects.get(
        vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
    ).configuration.copy()
    payload.pop("sender", None)
    payload.update(
        {
            "name": "GetDeliveryServices",
            "foreign_remote_system": {"identifier": identifier, "counter_id": counter_id, "reference_no": "N/A"},
            "filters": {
                "queryfilter1": "en",
                "queryfilter2": "US USD",  # origination country, currency
                "queryfilter3": f"{destination_country} {destination_currency}",
                "queryfilter4": "ALL",
            },
        }
    )
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    response = client.response_context("DAS_Service", payload, "DAS_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")

    if isinstance(response["content"], dict) and "content" in response and "MTML" in response["content"]:
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


def das_delivery_option_template(destination_country, destination_currency, identifier, counter_id, template_code):

    wu_env = config.WESTERN_UNION_WHITELISTED_ENV
    payload = FinancialServiceProvider.objects.get(
        vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
    ).configuration.copy()
    payload.pop("sender", None)
    payload.update(
        {
            "name": "GetDeliveryOptionTemplate",
            "foreign_remote_system": {"identifier": identifier, "counter_id": counter_id, "reference_no": "N/A"},
            "filters": {
                "queryfilter1": "en",
                "queryfilter2": f"{destination_country} {destination_currency}",  # destination
                "queryfilter3": template_code,  # coming delivery services endpoint ***
                "queryfilter8": "XPath",
            },
        }
    )
    client = WesternUnionClient("DAS_Service_H2HService.wsdl")
    response = client.response_context("DAS_Service", payload, "DAS_Service_H2H", f"SOAP_HTTP_Port_{wu_env}")

    if isinstance(response["content"], dict) and "content" in response and "MTML" in response["content"]:
        rows = response["content"]["MTML"]["REPLY"]["DATA_CONTEXT"]["RECORDSET"]
        template = {}
        structure = []
        service_provider_code = False
        if rows:
            try:
                obj = Corridor.objects.get(
                    destination_country=destination_country, destination_currency=destination_currency
                )
            except Corridor.DoesNotExist:
                obj = None
            if obj and not obj.template:
                for row in rows["GETDELIVERYOPTIONTEMPLATE"]:
                    t_index = row["T_INDEX"]
                    if t_index != "000":
                        first_value = row["DESCRIPTION"].split(";")[0].split(".")

                        if len(first_value) == 1:
                            code = row["DESCRIPTION"].split(";")[2].strip()
                            description = row["DESCRIPTION"].split(";")[3].strip()
                            base = template
                            for item in structure[:-1]:
                                base = base[item]
                            if not base[structure[-1]]:
                                base[structure[-1]] = code
                            elif isinstance(base[structure[-1]], list):
                                base[structure[-1]].append(code)
                            else:
                                base[structure[-1]] = [base[structure[-1]], code]
                            if service_provider_code:
                                ServiceProviderCode.objects.get_or_create(
                                    code=code,
                                    description=description,
                                    country=destination_country,
                                    currency=destination_currency,
                                )
                        else:
                            base = template
                            structure = first_value
                            for i in range(len(first_value)):
                                field = first_value[i]
                                if i == len(first_value) - 1:
                                    base[field] = None
                                else:
                                    if field not in base:
                                        base[field] = {}
                                    base = base[field]
                            if first_value == ["wallet_details", "service_provider_code"]:
                                service_provider_code = True
                            else:
                                service_provider_code = False
                obj.template = template
                obj.save()
    return response

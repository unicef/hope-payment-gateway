import logging
import random
from pathlib import Path

import sentry_sdk
from constance import config
from defusedxml.minidom import parseString
from requests import Session
from requests.exceptions import ConnectTimeout
from viewflow.fsm import TransitionNotAllowed
from zeep import Client, Settings
from zeep.exceptions import Fault, TransportError
from zeep.helpers import serialize_object
from zeep.transports import Transport
from zeep.wsdl.utils import etree_to_string

from hope_payment_gateway.apps.core.models import Singleton
from hope_payment_gateway.apps.fsp.client import FSPClient
from hope_payment_gateway.apps.fsp.utils import get_phone_number
from hope_payment_gateway.apps.fsp.western_union.api import (
    MONEY_IN_TIME,
    WALLET,
    WIC,
    WMF,
    agent,
    web,
)
from hope_payment_gateway.apps.fsp.western_union.api.utils import integrate_payload
from hope_payment_gateway.apps.fsp.western_union.exceptions import (
    InvalidCorridorError,
    PayloadException,
    PayloadMissingKeyError,
)
from hope_payment_gateway.apps.fsp.western_union.models import (
    Corridor,
    ServiceProviderCode,
)
from hope_payment_gateway.apps.gateway.flows import PaymentRecordFlow
from hope_payment_gateway.apps.gateway.models import (
    FinancialServiceProvider,
    PaymentRecord,
    PaymentRecordState,
)
from hope_payment_gateway.config.settings import WESTERN_UNION_CERT, WESTERN_UNION_KEY

logger = logging.getLogger(__name__)


class WesternUnionClient(FSPClient, metaclass=Singleton):
    def __init__(self) -> None:
        super().__init__()
        session = Session()
        session.cert = WESTERN_UNION_CERT, WESTERN_UNION_KEY
        transport = Transport(session=session, timeout=60, operation_timeout=60)
        settings = Settings(strict=False, xml_huge_tree=True)

        das_wsdl = str(Path(__file__).parent / "wsdl" / "DAS_Service_H2HService.wsdl")
        self.das_client = Client(das_wsdl, transport=transport, settings=settings)
        self.das_client.set_ns_prefix("xrsi", "http://www.westernunion.com/schema/xrsi")

        search_wsdl = str(Path(__file__).parent / "wsdl" / "Search_Service_H2HServiceService.wsdl")
        self.search_client = Client(search_wsdl, transport=transport, settings=settings)
        self.search_client.set_ns_prefix("xrsi", "http://www.westernunion.com/schema/xrsi")

        cancel_wsdl = str(Path(__file__).parent / "wsdl" / "CancelSend_Service_H2HService.wsdl")
        self.cancel_client = Client(cancel_wsdl, transport=transport, settings=settings)
        self.cancel_client.set_ns_prefix("xrsi", "http://www.westernunion.com/schema/xrsi")

        quote_wsdl = str(Path(__file__).parent / "wsdl" / "SendMoneyValidation_Service_H2HService.wsdl")
        self.quote_client = Client(quote_wsdl, transport=transport, settings=settings)
        self.quote_client.set_ns_prefix("xrsi", "http://www.westernunion.com/schema/xrsi")

        status_wsdl = str(Path(__file__).parent / "wsdl" / "PayStatus_Service_H2HService.wsdl")
        self.status_client = Client(status_wsdl, transport=transport, settings=settings)
        self.status_client.set_ns_prefix("xrsi", "http://www.westernunion.com/schema/xrsi")

        transaction_wsdl = str(Path(__file__).parent / "wsdl" / "SendMoneyStore_Service_H2HService.wsdl")
        self.transaction_client = Client(transaction_wsdl, transport=transport, settings=settings)
        self.transaction_client.set_ns_prefix("xrsi", "http://www.westernunion.com/schema/xrsi")

        nis_wsdl = str(Path(__file__).parent / "wsdl" / "NisNotification.wsdl")
        self.notification_client = Client(nis_wsdl, transport=transport, settings=settings)
        self.notification_client.set_ns_prefix("xrsi", "http://www.westernunion.com/schema/xrsi")

    @staticmethod
    def response_context(client, service_name, payload, wsdl_name=None, port=None):
        response = dict
        error = ""
        display_format = "string"
        try:
            if wsdl_name and port:
                binded_client = client.bind(wsdl_name, port)
            else:
                binded_client = client.service
            service = getattr(binded_client, service_name)
        except ValueError as exc:
            return {"title": str(exc), "code": 400, "error": str(exc)}
        except AttributeError as exc:
            return {"title": str(exc), "code": 500, "error": str(exc)}
        try:
            response = service(**payload)
            title = service_name
            display_format = "json"
            code = 200
        except (TransportError, ConnectTimeout) as exc:
            title = f"{exc.message} [{exc.status_code}]"
            code = 400
            logger.exception(exc)
        except TypeError as exc:
            display_format = "xml"
            title = "Invalid Payload"
            code = 400
            error = str(exc)
            logger.exception(exc)
        except Fault as exc:
            display_format = "xml"
            title = f"{exc.message} [{exc.code}]"
            response = etree_to_string(exc.detail).decode()
            try:
                error = exc.detail.xpath("//error/text()")[0]
            except IndexError:
                error = "generic error"
            code = 400
            logger.exception(exc)
        except Exception as exc:
            title = type(exc).__name__
            code = 400
            error = str(exc)
            logger.exception(exc)

        return {
            "title": title,
            "url": f"{wsdl_name}:{service_name}",
            "content_request": payload,
            "content_response": response,
            "request_format": "json",
            "response_format": display_format,
            "code": code,
            "error": error,
        }

    @staticmethod
    def prepare(client, service_name, payload):
        node = client.create_message(client.service, service_name, **payload)
        data = etree_to_string(node)
        dom = parseString(data)
        return node, dom.toprettyxml()

    @staticmethod
    def create_validation_payload(base_payload):
        try:
            counter_ids = base_payload.get("counter_id", "N/A")
            counter_id = (
                random.choice(counter_ids)  # noqa
                if isinstance(counter_ids, list)
                else counter_ids
            )
            transaction_type = base_payload.get("transaction_type", WMF)
            frm = {
                "identifier": base_payload.get("identifier", "N/A"),
                "reference_no": base_payload.get("payment_record_code", "N/A"),
                "counter_id": counter_id,
            }

            delivery_phone_number = base_payload.get("delivery_phone_number")
            phone_number, country_code = get_phone_number(delivery_phone_number)
            contact_no = base_payload.get("phone_no", "N/A")

            receiver = {
                "name": {
                    "first_name": base_payload["first_name"],
                    "last_name": base_payload["last_name"],
                    "middle_name": base_payload.get("middle_name", ""),
                    "name_type": "D",
                },
                "contact_phone": contact_no,
                "mobile_phone": {
                    "phone_number": {
                        "country_code": country_code,
                        "national_number": phone_number,
                    },
                },
                "reason_for_sending": base_payload.get("reason_for_sending", None),
            }
            amount_key = "destination_principal_amount" if transaction_type == WMF else "originators_principal_amount"
            financials = {
                amount_key: int(float(base_payload["amount"]) * 100),
            }
            payment_details = {
                "recording_country_currency": {  # sending country
                    "iso_code": {
                        "country_code": base_payload.get("origination_country", "US"),
                        "currency_code": base_payload.get("origination_currency", "USD"),
                    },
                },
                "destination_country_currency": {  # destination
                    "iso_code": {
                        "country_code": base_payload["destination_country"],
                        "currency_code": base_payload["destination_currency"],
                    },
                },
                "originating_country_currency": {  # sending country
                    "iso_code": {
                        "country_code": base_payload.get("origination_country", "US"),
                        "currency_code": base_payload.get("origination_currency", "USD"),
                    },
                },
                "transaction_type": transaction_type,
                "payment_type": "Cash",
                "duplicate_detection_flag": base_payload.get("duplication_enabled", "D"),
            }

            delivery_services = {"code": base_payload.get("delivery_services_code", MONEY_IN_TIME)}
            partner_notification = {"partner_notification": {"notification_requested": "Y"}}

            payload = FinancialServiceProvider.objects.get(
                vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
            ).configuration.copy()
            payload.update(
                {
                    "device": web,
                    "receiver": receiver,
                    "payment_details": payment_details,
                    "financials": financials,
                    "delivery_services": delivery_services,
                    "foreign_remote_system": frm,
                    "partner_info_buffer": partner_notification,
                    "wallet_details": {"service_provider_code": base_payload.get("service_provider_code")},
                }
            )

            if "delivery_services_code" in base_payload and base_payload["delivery_services_code"] == WALLET:
                country = base_payload["destination_country"]
                currency = base_payload["destination_currency"]
                try:
                    template = Corridor.objects.get(
                        destination_country=country,
                        destination_currency=currency,
                    ).template

                except Corridor.DoesNotExist:
                    raise InvalidCorridorError(f"Invalid corridor for {country}/{currency}")

                payload = integrate_payload(payload, template)
        except KeyError as e:
            raise PayloadMissingKeyError(f"InvalidPayload: {e.args[0]} is missing in the payload")
        return payload

    def send_money_validation(self, payload):
        wu_env = config.WESTERN_UNION_WHITELISTED_ENV
        sentry_sdk.capture_message("Western Union: Send Money Validation")
        ref_no = payload.get("foreign_remote_system", dict).get("reference_no", "N/A")
        logging.info(f"VALIDATION {ref_no}")
        return self.response_context(
            self.quote_client,
            "sendmoneyValidation",
            payload,
            "SendmoneyValidation_Service_H2H",
            f"SOAP_HTTP_Port_{wu_env}",
        )

    def send_money_store(self, payload):
        wu_env = config.WESTERN_UNION_WHITELISTED_ENV
        sentry_sdk.capture_message("Western Union: Send Money Store")
        mtcn = payload.get("mtcn", "N/A")
        logging.info(f"STORE {mtcn}")
        return self.response_context(
            self.transaction_client,
            "SendMoneyStore_H2H",
            payload,
            "SendMoneyStore_Service_H2H",
            f"SOAP_HTTP_Port_{wu_env}",
        )

    def create_transaction(self, base_payload: dict, update: bool = True) -> dict:
        record_code = base_payload["payment_record_code"]
        pr = PaymentRecord.objects.get(
            record_code=record_code,
            status=PaymentRecordState.PENDING,
            parent__fsp__vendor_number=config.WESTERN_UNION_VENDOR_NUMBER,
        )
        try:
            payload = self.create_validation_payload(base_payload)
            response = self.send_money_validation(payload)
            pr.refresh_from_db()
            if response["code"] != 200:
                pr.message = f"Validation failed: {response['error']}"
                pr.status, pr.success = PaymentRecordState.ERROR, False
                pr.save()
                return response
            smv_payload = serialize_object(response["content_response"])
            pr.auth_code = smv_payload["mtcn"]
            pr.fsp_code = smv_payload["new_mtcn"]
            pr.save()
        except (InvalidCorridorError, PayloadException, TransitionNotAllowed) as exc:
            pr.message, pr.status, pr.success = (
                str(exc),
                PaymentRecordState.ERROR,
                False,
            )
            pr.save()
            raise exc

        if response["code"] != 200:
            pr.message, pr.success, pr.auth_code, pr.fsp_code = (
                f"Send Money Validation: {response['error']}",
                False,
                smv_payload["mtcn"],
                smv_payload["new_mtcn"],
            )
            if response["error"][:5] not in config.WESTERN_UNION_ERRORS.split(";"):
                pr.fail()
            pr.save()
            return response
        extra_data = {
            key: smv_payload[key]
            for key in [
                "foreign_remote_system",
                "instant_notification",
                "mtcn",
                "new_mtcn",
                "financials",
                "filing_date",
                "filing_time",
            ]
        }
        log_data = extra_data.copy()
        log_data["record_code"] = base_payload["payment_record_code"]
        log_data.pop("financials")
        extra_data.pop("filing_date")
        extra_data.pop("filing_time")
        pr.message = "Send Money Validation: Success"
        pr.success = True
        pr.extra_data.update(log_data)
        pr.save()
        for key, value in extra_data.items():
            payload[key] = value

        response = self.send_money_store(payload)
        pr.refresh_from_db()
        flow = PaymentRecordFlow(pr)
        if response["code"] == 200:
            pr.message, pr.success = "Send Money Store: Success", True
            flow.store()
        else:
            pr.message, pr.success = f"Send Money Store: {response['error']}", False
            flow.fail()
        pr.extra_data.update(log_data)
        pr.save()
        return response

    def status(self, transaction_id, update):
        pr = PaymentRecord.objects.get(
            fsp_code=transaction_id,
            parent__fsp__vendor_number=config.WESTERN_UNION_VENDOR_NUMBER,
        )
        wu_env = config.WESTERN_UNION_WHITELISTED_ENV
        frm = pr.extra_data.get("foreign_remote_system", None)
        mtcn = pr.extra_data.get("mtcn", None)
        payload = {
            "channel": {"type": "H2H", "name": "CHANNEL", "version": "9500"},
            "mtcn": mtcn,
            "foreign_remote_system": frm,
        }
        response = self.response_context(
            self.status_client,
            "PayStatus",
            payload,
            "PayStatus_Service_H2H",
            f"SOAP_HTTP_Port_{wu_env}",
        )
        if update:
            wu_status = response["content_response"]["payment_transactions"]["payment_transaction"][0][
                "pay_status_description"
            ]
            status = {
                "PAID": PaymentRecordState.TRANSFERRED_TO_BENEFICIARY,
                "WCQ": PaymentRecordState.TRANSFERRED_TO_FSP,
                "CAN": PaymentRecordState.CANCELLED,
            }.get(wu_status)
            if pr.status != status:
                if status in [PaymentRecordState.TRANSFERRED_TO_FSP]:
                    pr.message = "Transferred to FSP*"
                    pr.status = status
                    pr.success = True
                elif status in [PaymentRecordState.TRANSFERRED_TO_BENEFICIARY]:
                    pr.message = "Transferred to Beneficiary*"
                    pr.status = status
                    pr.success = True
                elif status in [PaymentRecordState.CANCELLED]:
                    pr.message = "Cancelled*"
                    pr.status = status
                    pr.success = True
                pr.save()

        return response

    def search_request(self, frm, mtcn):
        payload = FinancialServiceProvider.objects.get(
            vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
        ).configuration.copy()
        wu_env = config.WESTERN_UNION_WHITELISTED_ENV
        partner_notification = {"partner_notification": {"notification_requested": "Y"}}
        payload.pop("sender", None)
        payload.update(
            {
                "device": agent,
                "payment_transaction": {
                    "payment_details": {
                        "originating_country_currency": {"iso_code": {"country_code": "US", "currency_code": "USD"}},
                    },
                    "mtcn": mtcn,
                },
                "search_flag": "CANCEL_SEND",
                "foreign_remote_system": frm,
                "partner_info_buffer": partner_notification,
            }
        )
        return self.response_context(
            self.search_client,
            "Search",
            payload,
            "Search_Service_H2H",
            f"SOAP_HTTP_Port_{wu_env}",
        )

    def cancel_request(self, frm, mtcn, database_key, reason=WIC):
        wu_env = config.WESTERN_UNION_WHITELISTED_ENV
        payload = FinancialServiceProvider.objects.get(
            vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
        ).configuration.copy()
        payload.pop("sender", None)
        payload.update(
            {
                "device": agent,
                "foreign_remote_system": frm,
                "reason_for_redelivery": reason,
                "mtcn": mtcn,
                "database_key": database_key,
                "comments_data": "Client requested for cancel",
                "disallow_traffic_flag": "Y",
            }
        )

        ref_no = payload.get("foreign_remote_system", dict).get("reference_no", "N/A")
        logging.info(f"CANCEL {ref_no}")
        return self.response_context(
            self.cancel_client,
            "CancelSend",
            payload,
            "CancelSend_Service_H2H",
            f"SOAP_HTTP_Port_{wu_env}",
        )

    def refund(self, transaction_id, base_payload):
        pr = PaymentRecord.objects.get(
            fsp_code=transaction_id,
            parent__fsp__vendor_number=config.WESTERN_UNION_VENDOR_NUMBER,
        )
        mtcn = pr.extra_data.get("mtcn", None)
        frm = pr.extra_data.get("foreign_remote_system", None)
        response = self.search_request(frm, mtcn)
        payload = response["content_response"]
        try:
            database_key = payload["payment_transactions"]["payment_transaction"][0]["money_transfer_key"]
        except TypeError:
            database_key = None
        if not database_key:
            pr.message = "Search Error: No Money Transfer Key"
            pr.success = False
            flow = PaymentRecordFlow(pr)
            flow.fail()
            pr.save()
            return response

        response = self.cancel_request(frm, mtcn, database_key)
        extra_data = {"db_key": database_key, "mtcn": mtcn}

        if response["code"] == 200:
            pr.message = "Request for cancel"
            pr.success = True
        else:
            pr.message = f"Cancel request error: {response['error']}"
            pr.success = False
        pr.extra_data.update(extra_data)
        pr.save()
        return response

    # DAS API

    def das_countries_currencies(self, identifier, counter_id, create_corridors=False):
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
                    "foreign_remote_system": {
                        "identifier": identifier,
                        "counter_id": counter_id,
                        "reference_no": "N/A",
                    },
                    "filters": {
                        "queryfilter1": "en",
                        "queryfilter2": "US USD",  # destination
                        "queryfilter3": qf3,
                        "queryfilter4": qf4,
                    },
                }
            )
            response = self.response_context(
                self.das_client,
                "DAS_Service",
                payload,
                "DAS_Service_H2H",
                f"SOAP_HTTP_Port_{wu_env}",
            )
            if isinstance(response["content_response"], dict):
                context = response["content_response"]["MTML"]["REPLY"]["DATA_CONTEXT"]
                more_data = context["HEADER"]["DATA_MORE"] == "Y"

                if create_corridors:
                    for country_currency in context["RECORDSET"]["GETCOUNTRIESCURRENCIES"]:
                        country = country_currency["ISO_COUNTRY_CD"]
                        currency = country_currency["CURRENCY_CD"]
                        qf3 = country_currency["COUNTRY_LONG"]
                        qf4 = country_currency["CURRENCY_NAME"]

                        self.das_delivery_services(
                            country,
                            currency,
                            identifier,
                            counter_id,
                            create_corridors=create_corridors,
                        )
                else:
                    more_data = False  # skip we want only 1st page
            else:
                more_data = False  # skip we want only 1st page
        return response

    def das_origination_currencies(self, identifier, counter_id):
        wu_env = config.WESTERN_UNION_WHITELISTED_ENV
        payload = FinancialServiceProvider.objects.get(
            vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
        ).configuration.copy()
        payload.pop("sender", None)
        payload.update(
            {
                "name": "GetOriginationCurrencies",
                "foreign_remote_system": {
                    "identifier": identifier,
                    "counter_id": counter_id,
                    "reference_no": "N/A",
                },
                "filters": {
                    "queryfilter1": "en",
                },
            }
        )
        return self.response_context(
            self.das_client,
            "DAS_Service",
            payload,
            "DAS_Service_H2H",
            f"SOAP_HTTP_Port_{wu_env}",
        )

    def das_destination_countries(self, identifier, counter_id):
        wu_env = config.WESTERN_UNION_WHITELISTED_ENV
        payload = FinancialServiceProvider.objects.get(
            vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
        ).configuration.copy()
        payload.pop("sender", None)
        payload.update(
            {
                "name": "GetDestinationCountries",
                "foreign_remote_system": {
                    "identifier": identifier,
                    "counter_id": counter_id,
                    "reference_no": "N/A",
                },
                "filters": {"queryfilter1": "en", "queryfilter2": "US USD"},
            }
        )
        return self.response_context(
            self.das_client,
            "DAS_Service",
            payload,
            "DAS_Service_H2H",
            f"SOAP_HTTP_Port_{wu_env}",
        )

    def das_destination_currencies(self, destination_country, identifier, counter_id):
        wu_env = config.WESTERN_UNION_WHITELISTED_ENV
        payload = FinancialServiceProvider.objects.get(
            vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
        ).configuration.copy()
        payload.pop("sender", None)
        payload.update(
            {
                "name": "GetDestinationCurrencies",
                "foreign_remote_system": {
                    "identifier": identifier,
                    "counter_id": counter_id,
                    "reference_no": "N/A",
                },
                "filters": {
                    "queryfilter1": "en",
                    "queryfilter2": "US USD",  # origination country
                    "queryfilter3": destination_country,
                },
            }
        )
        return self.response_context(
            self.das_client,
            "DAS_Service",
            payload,
            "DAS_Service_H2H",
            f"SOAP_HTTP_Port_{wu_env}",
        )

    def das_delivery_services(
        self,
        destination_country,
        destination_currency,
        identifier,
        counter_id,
        create_corridors=False,
    ):
        wu_env = config.WESTERN_UNION_WHITELISTED_ENV
        payload = FinancialServiceProvider.objects.get(
            vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
        ).configuration.copy()
        payload.pop("sender", None)
        payload.update(
            {
                "name": "GetDeliveryServices",
                "foreign_remote_system": {
                    "identifier": identifier,
                    "counter_id": counter_id,
                    "reference_no": "N/A",
                },
                "filters": {
                    "queryfilter1": "en",
                    "queryfilter2": "US USD",  # origination country, currency
                    "queryfilter3": f"{destination_country} {destination_currency}",
                    "queryfilter4": "ALL",
                },
            }
        )
        response = self.response_context(
            self.das_client,
            "DAS_Service",
            payload,
            "DAS_Service_H2H",
            f"SOAP_HTTP_Port_{wu_env}",
        )

        if (
            isinstance(response["content_response"], dict)
            and "content" in response
            and "MTML" in response["content_response"]
        ):
            context = response["content_response"]["MTML"]["REPLY"]["DATA_CONTEXT"]["RECORDSET"]
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

    def das_delivery_option_template(  # noqa
        self,
        destination_country,
        destination_currency,
        identifier,
        counter_id,
        template_code,
    ):
        wu_env = config.WESTERN_UNION_WHITELISTED_ENV
        payload = FinancialServiceProvider.objects.get(
            vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
        ).configuration.copy()
        payload.pop("sender", None)
        payload.update(
            {
                "name": "GetDeliveryOptionTemplate",
                "foreign_remote_system": {
                    "identifier": identifier,
                    "counter_id": counter_id,
                    "reference_no": "N/A",
                },
                "filters": {
                    "queryfilter1": "en",
                    "queryfilter2": f"{destination_country} {destination_currency}",  # destination
                    "queryfilter3": template_code,  # coming delivery services endpoint ***
                    "queryfilter8": "XPath",
                },
            }
        )
        response = self.response_context(
            self.das_client,
            "DAS_Service",
            payload,
            "DAS_Service_H2H",
            f"SOAP_HTTP_Port_{wu_env}",
        )
        if (
            isinstance(response["content_response"], dict)
            and "content" in response
            and "MTML" in response["content_response"]
        ):
            rows = response["content_response"]["MTML"]["REPLY"]["DATA_CONTEXT"]["RECORDSET"]
            template = {}
            structure = []
            service_provider_code = False
            if rows:
                try:
                    obj = Corridor.objects.get(
                        destination_country=destination_country,
                        destination_currency=destination_currency,
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
                                if first_value == [
                                    "wallet_details",
                                    "service_provider_code",
                                ]:
                                    service_provider_code = True
                                else:
                                    service_provider_code = False
                    obj.template = template
                    obj.save()
        return response

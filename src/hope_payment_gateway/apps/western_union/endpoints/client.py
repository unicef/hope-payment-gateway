from pathlib import Path

from requests import Session
from zeep import Client, Settings
from zeep.exceptions import Fault, TransportError
from zeep.transports import Transport
from zeep.wsdl.utils import etree_to_string

from hope_payment_gateway.config.settings import WESTERN_UNION_CERT, WESTERN_UNION_KEY


class WesternUnionClient:
    def __init__(self, wsdl_filename) -> None:
        super().__init__()
        session = Session()
        session.cert = WESTERN_UNION_CERT, WESTERN_UNION_KEY
        transport = Transport(session=session, timeout=60, operation_timeout=60)
        settings = Settings(strict=False, xml_huge_tree=True)
        wsdl = str(Path(__file__).parent / "wsdl" / wsdl_filename)
        self.client = Client(wsdl, transport=transport, settings=settings)
        self.client.set_ns_prefix("xrsi", "http://www.westernunion.com/schema/xrsi")

    def response_context(self, service_name, payload):
        response = ""
        error = ""
        format = "string"
        try:
            service = getattr(self.client.service, service_name)
        except AttributeError as exc:
            return {"title": str(exc), "code": 500}
        try:
            response = service(**payload)
            title = service_name
            format = "json"
            code = 200
        except TransportError as exc:
            title = f"{exc.message} [{exc.status_code}]"
            code = 400
        except TypeError as exc:
            title = "Invalid Payload"
            code = 400
            error = str(exc)
        except Fault as exc:
            title = f"{exc.message} [{exc.code}]"
            response = etree_to_string(exc.detail)
            try:
                error = exc.detail.xpath("//error/text()")[0]
            except BaseException:
                error = "generic error"
            code = 400

        return {"title": title, "content": response, "format": format, "code": code, "error": error}

import logging
import xml.dom.minidom
from pathlib import Path

from requests import Session
from requests.exceptions import ConnectTimeout
from zeep import Client, Settings
from zeep.exceptions import Fault, TransportError
from zeep.transports import Transport
from zeep.wsdl.utils import etree_to_string

from hope_payment_gateway.config.settings import WESTERN_UNION_CERT, WESTERN_UNION_KEY

logger = logging.getLogger(__name__)


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

    def response_context(self, service_name, payload, wsdl_name=None, port=None):
        response = dict()
        error = ""
        format = "string"
        try:
            if wsdl_name and port:
                client_binded = self.client.bind(wsdl_name, port)
            else:
                client_binded = self.client.service
            service = getattr(client_binded, service_name)
        except ValueError as exc:
            return {"title": str(exc), "code": 400}
        except AttributeError as exc:
            return {"title": str(exc), "code": 500}
        try:
            response = service(**payload)
            title = service_name
            format = "json"
            code = 200
        except (TransportError, ConnectTimeout) as exc:
            title = f"{exc.message} [{exc.status_code}]"
            code = 400
            logger.exception(exc)
        except TypeError as exc:
            title = "Invalid Payload"
            code = 400
            error = str(exc)
            logger.exception(exc)
        except Fault as exc:
            title = f"{exc.message} [{exc.code}]"
            response = etree_to_string(exc.detail)
            try:
                error = exc.detail.xpath("//error/text()")[0]
            except BaseException:  # noqa: B036
                error = "generic error"
            code = 400
            logger.exception(exc)
        except Exception as exc:
            title = type(exc).__name__
            code = 400
            error = str(exc)
            logger.exception(exc)

        return {"title": title, "content": response, "format": format, "code": code, "error": error}

    def prepare(self, service_name, payload):
        node = self.client.create_message(self.client.service, service_name, **payload)
        data = etree_to_string(node)
        dom = xml.dom.minidom.parseString(data)
        return node, dom.toprettyxml()

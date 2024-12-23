from django.conf import settings

import requests


class WUClient:
    def __init__(
        self,
        base_url=None,
        cert=settings.WESTERN_UNION_CERT,
        key=settings.WESTERN_UNION_KEY,
    ):
        self.headers = {"Content-Type": "application/xml"}
        self.BASE_URL = base_url or settings.WESTERN_UNION_BASE_URL
        self.cert = cert, key

    def request(self, body):
        return requests.post(self.BASE_URL, cert=self.cert, headers=self.headers, data=body, timeout=30)


def requests_request():
    request = """
        <?xml version='1.0' encoding='utf-8'?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:xrsi="http://www.westernunion.com/schema/xrsi">
           <soapenv:Header/>
           <soapenv:Body>
              <ns2:esp-heartbeat-request xmlns:ns2="http://www.westernunion.com/schema/xrsi">
                 <partner>
                    <id>USATEST</id>
                    <system>
                       <id>USATEST</id>
                       <name>WU-MMT-PILOT-SVR</name>
                       <version>9001</version>
                       <ip_address>192.168.1.1</ip_address>
                       <connector>
                          <id>USATEST</id>
                       </connector>
                    </system>
                 </partner>
                 <external_reference_no>1</external_reference_no>
              </ns2:esp-heartbeat-request>
           </soapenv:Body>
        </soapenv:Envelope>
        """

    response = WUClient().request(request)

    return {"title": response.status_code, "content": response.text}


# nc -vz wugateway2pi.westernunion.com 443
# Connection to wugateway2pi.westernunion.com port 443 [tcp/https] succeeded!

from datetime import datetime

web = {"type": "WEB"}
agent = {"type": "AGENT"}
unicef = {"type": "H2H", "name": "UNICEF", "version": "9500"}


def get_usd(ref_num="N/A"):
    rnd = int(round(datetime.now().timestamp()))
    return {
        "identifier": "WGQCUS1250T",
        "reference_no": f"{ref_num}-{rnd}",
        "counter_id": "US125QCUSD1T",
    }


def get_eur(ref_num="N/A"):
    rnd = int(round(datetime.now().timestamp()))
    return {
        "identifier": "WGQCUS125ET",
        "reference_no": f"{ref_num}-{rnd}",
        "counter_id": "US125QCEUR1T",
    }


WMF = "WMF"
WMN = "WMN"

# delivery_services_code
MONEY_IN_TIME = "000"
WALLET = "800"


def iso_code(country_code, currency_code):
    return {
        "country_code": country_code,
        "currency_code": currency_code,
    }


sender = {
    "name": {
        "name_type": "C",
        "business_name": "UNICEF",
    },
    "address": {
        "addr_line1": "3 United Nations Plaza",
        "addr_line2": "",
        "city": "NEW YORK",
        "state": "NY",
        "postal_code": "10017",
        "country_code": {
            "iso_code": iso_code("US", "USD"),
            "country_name": "US",
        },
        "local_area": "NEW YORK",
        "street": "3 United Nations Plaza",
    },
    "email": "unicef@unicef.org",
    "contact_phone": "2123267000",
    "mobile_phone": {
        "phone_number": {
            "country_code": "1",
            "national_number": "2123267000",
        },
    },
    "fraud_warning_consent": "Y",
}

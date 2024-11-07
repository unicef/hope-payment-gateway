web = {"type": "WEB"}
agent = {"type": "AGENT"}


WMF = "WMF"  # fixed money transfer
WMN = "WMN"  # money transfer

WIC = "WIC"  # system

# delivery_services_code
MONEY_IN_TIME = "000"  # Cash over the counter: collect money kiosk
WALLET = "800"


def iso_code(country_code, currency_code):
    return {
        "country_code": country_code,
        "currency_code": currency_code,
    }

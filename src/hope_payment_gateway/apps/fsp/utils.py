import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException


def get_phone_number(raw_phone_no):
    try:
        phone_no = phonenumbers.parse(raw_phone_no, None)
        phone_number = phone_no.national_number
        country_code = phone_no.country_code
    except NumberParseException:
        phone_number = raw_phone_no
        country_code = None

    return phone_number, country_code


def get_from_delivery_mechanism(payload, key, default=None):
    delivery_mechanism = payload.get("delivery_mechanism", "")
    return payload.get(f"{key}__{delivery_mechanism}", default)

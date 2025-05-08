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


def get_account_field(payload, field_name):
    if account_dict := payload.get("account"):
        return account_dict.get(field_name, None)
    return None


def extrapolate_errors(data):
    msgs = []
    if "errors" in data:
        for error in data["errors"]:
            msgs.append(f"{error['message']} ({error['code']})")
            if "offendingFields" in error:
                msgs.extend([f"Field: {field['field']}" for field in error["offendingFields"] if "field" in field])
    elif "error" in data:
        message = data.get("message", data["error"])
        msgs.append(message)
    else:
        msgs = ["Error"]
    return msgs

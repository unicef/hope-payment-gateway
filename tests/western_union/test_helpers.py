def analyze_node(nodes, partial=[]):
    for item in nodes:
        if isinstance(item, dict):
            news = []
            for key, value in item.items():
                biz = analyze_node(
                    [value],
                    partial
                    + [
                        key,
                    ],
                )
                if isinstance(value, dict):
                    news.extend(biz)
                else:
                    news.append(biz)
            return news
        else:
            partial.append(item)
            return partial


def integrate_payload(payload, template):
    for path in analyze_node([template]):
        cursor = payload
        value = path[-1]
        for key in path[:-1]:
            if key not in cursor:
                cursor[key] = dict()
            cursor = cursor[key]
        print(value, cursor)
        if value is None:
            if cursor is None or not cursor:
                raise (Exception(f"missing element {value} in {cursor}"))
        elif isinstance(value, list):
            if cursor not in value:
                raise (Exception("invalid choice"))
        else:
            cursor[key] = value
    return payload


template = {
    "receiver": {
        "mobile_phone": {"phone_number": {"country_code": 63}},
        "reason_for_sending": ["P012", "P014", "P015", "P016", "P017", "P018", "P019", "P020"],
    },
    "wallet_details": {"service_provider_code": ["06301", "06302", "06304", "06305", "06307"]},
}


payload = {
    "device": {"type": "WEB"},
    "channel": {"type": "H2H", "name": "UNICEF", "version": "9500"},
    "sender": {
        "name": {"name_type": "C", "business_name": "UNICEF"},
        "address": {
            "addr_line1": "3 United Nations Plaza",
            "addr_line2": "",
            "city": "NEW YORK",
            "state": "NY",
            "postal_code": "10017",
            "country_code": {"iso_code": {"country_code": "US", "currency_code": "USD"}, "country_name": "US"},
            "local_area": "NEW YORK",
            "street": "3 United Nations Plaza",
        },
        "email": "unicef@unicef.org",
        "contact_phone": "2123267000",
        "mobile_phone": {"phone_number": {"country_code": "1", "national_number": "2123267000"}},
        "fraud_warning_consent": "Y",
    },
    "receiver": {
        "name": {"first_name": "Aliyah", "last_name": "GRAY", "name_type": "D"},
        "contact_phone": "+94786661137",
    },
    "payment_details": {
        "recording_country_currency": {"iso_code": {"country_code": "US", "currency_code": "USD"}},
        "destination_country_currency": {"iso_code": {"country_code": "ES", "currency_code": "EUR"}},
        "originating_country_currency": {"iso_code": {"country_code": "US", "currency_code": "USD"}},
        "transaction_type": "WMF",
        "payment_type": "Cash",
        "duplicate_detection_flag": "D",
    },
    "financials": {"destination_principal_amount": 199900},
    "delivery_services": {"code": "800"},
    "foreign_remote_system": {
        "identifier": "WGQCUS1250T",
        "reference_no": "RCPT-0060-23-0.000.618-1693925489",
        "counter_id": "US125QCUSD1T",
    },
}

analyze_node([template])
integrate_payload(payload, template)

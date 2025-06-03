import hashlib
import hmac
import uuid

import requests

from hope_payment_gateway.config import settings
import time


def get_hmac_sha512(data, key):
    key_bytes = bytes(key, "ascii")
    data_bytes = bytes(data, "ascii")
    hmac_object = hmac.new(key_bytes, data_bytes, hashlib.sha512)
    return hmac_object.hexdigest()


def generate_hmac_signature(url, method, client_id, client_secret):
    unix_timestamp = int(time.time())
    nonce = str(uuid.uuid4())
    concatenated_string = client_id + method + settings.PALPAY_HOST + url + str(unix_timestamp) + nonce
    hmac_signature = get_hmac_sha512(concatenated_string, client_secret)
    return f"{client_id}:{hmac_signature}:{nonce}:{unix_timestamp}"


def perform_request(endpoint, method):
    headers = {
        "Authorization": generate_hmac_signature(
            endpoint, method, settings.PALPAY_CLIENT_ID, settings.PALPAY_CLIENT_SECRET
        ),
        "Content-Type": "application/json",
    }

    url = f"{settings.PALPAY_HOST}{endpoint}"
    response = requests.get(url, headers=headers, timeout=30)
    return response.json()


perform_request("/api/v1/moneytransfer/profile", "GET")

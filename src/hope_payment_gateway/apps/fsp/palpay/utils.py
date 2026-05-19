import hashlib
import hmac
import time
import uuid

from hope_payment_gateway.config import settings


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

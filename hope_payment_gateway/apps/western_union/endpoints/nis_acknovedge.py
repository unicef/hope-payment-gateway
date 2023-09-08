from hope_payment_gateway.apps.western_union.endpoints.client import WesternUnionClient


def nic_acknowledge(payload):
    payload.pop("notification_type")
    payload.pop("message_code")
    payload.pop("message_text")
    payload["ack_message"] = "SUCCESS"

    client = WesternUnionClient("NisNotification.wsdl")
    return client.response_context("NotifService", payload)

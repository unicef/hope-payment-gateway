from ..settings import env

STREAMING = {
    "BROKER_URL": env("STREAMING_BROKER_URL"),
    "QUEUES": {"payment_gateway": {"routing": ["payment.*.*"]}},
}

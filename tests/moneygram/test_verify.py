import pytest

from hope_payment_gateway.apps.fsp.moneygram.endpoints import verify
from django.test import override_settings


@pytest.mark.parametrize(
    ("signature_header", "unix_time_in_seconds", "destination_host", "body"),
    [
        (
            "wGIPt8Wt16Vl9yMGEBO7ByZA8zkJzuUjaE/2G5NDez8SEGDnX5VdxoSqdTN8N6/LaX2jV/9o25fWppJoxBBK6g/SHKFAo/Ib8uOnNYWeyjdrhZ4RVBCmB+IcdKuSXZHWFwtCLZM0R6PitE4HkXJrooe5KY93VzR8migLd7bw4ANAFwhYLBn6JmfnKO78A1hqpsUsq1T28Aph+6mYPx2q4SrfpkKK/YAoZrCpZMR/nzZMYevJhupy4i7B2L5axv94gm6YKZkaTAjCJWtXp2Kkv+UQ4Dpo7I+DkxWObg8dCy1JfzLlh57XswSdyiombhizHI89MgW4j1IWHZ4EZWxc6Q==",  # noqa
            1679925945,
            "f-p-sandbox.snssdk.com",
            '{"eventId":"740708201679925945014500444747","eventDate":"2023-03-27T14:05:44.884026","subscriptionId":"15efa8b3-bb09-4fe9-a295-55fc323cf3ee","subscriptionType":"TRANSACTION_STATUS_EVENT","eventPayload":{"transactionId":"3009143868","agentPartnerId":"74097706","referenceNumber":"40196296","transactionSendDate":"2023-03-27T14:05:41.007","transactionStatusDate":"2023-03-27T14:05:41.007","transactionStatus":"SENT","transactionSubStatus":[]}}',  # noqa
        ),
        (
            "UhqXSGEQ2d3Tg9Q0/H/TEW+ERZkmPJ+xI5+rH+Y3AH1IBlqTzXgtaIS4ilXWmuE6+G9E3nylSNDu8mFjk99Q5aiiLhJ4BSl8RpY+Q5zKH07k4slKqVWmgpjrdEOVXpa367e59lW20f41JIoLmf05LHWgI6/ttcr1fsCBCkKUfYBGeF4oaOlSK/NGMomF97Whw+uuso9TaTco2h3ognkqxunWq8xOpzDqIz1kTXXTJr4DAxVIKfrDcw+q41YkeP3IrISnCPun9kjCrWKi6bU6+5Z5jYj4tGxlTJS1EBMwE6EYh7PJ5Jbxd/pueetE8+Te39nGSVQFG2BLfjNIomS99Q==",  # noqa
            1744557471,
            "payment-hope-stg.unitst.org",
            '{"eventId":"752486481744557471490362098772","eventDate":"2025-04-13T15:17:51.483061","subscriptionId":"237c8303-de5f-4665-986c-32e08e963929","subscriptionType":"TRANSACTION_STATUS_EVENT","eventPayload":{"transactionId":"ca4c68c6-74aa-4120-8f2d-ab03c62913de","agentPartnerId":"75601117","referenceNumber":"76916143","transactionSendDate":"2025-04-13T10:17:12.000037","transactionStatusDate":"2025-04-13T15:17:51.483061","expectedPayoutDate":"2025-04-13","transactionStatus":"REFUNDED","transactionSubStatus":[]}}',  # noqa
        ),
    ],
)
@override_settings(
    MONEYGRAM_PUBLIC_KEY="MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0Dm7LFleQyaXakYdNOvCv2Irm2ufOcncek0Q4J+MtzmEYvdlfhx5Sm206s2Z5l0/+6YyA3tFljRNCFar3lm96o/S6IFNo0xOsCy+Il7EzQNl4S7kojqnOGfgMgUBC/qxf0S7zkh7y0St8G3OpcjYg7Ff7PAFXmcgjk22F1lUeOqy+zyP2dRJ+NEKZrcHJhbFheB0dPH++e+1foHSfhz+I+Pt9DDaESJasJptZGo0Ww3U+KkPmrDriOLbvpdE4r7MKzeQfGa7SMx4VzhtWFa98/6V6MO29ZjkegejHBZsCekA/1NU0gAQhQnxuYsgdCn/9LogrWqUS8Tl44K2yPYCsQIDAQAB"  # noqa
)
def test_verify(signature_header, unix_time_in_seconds, destination_host, body):
    assert verify(signature_header, unix_time_in_seconds, destination_host, body)

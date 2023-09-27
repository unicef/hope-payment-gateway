from hope_payment_gateway.apps.fsp.western_union.endpoints.send_money import send_money
from hope_payment_gateway.apps.gateway.registry import FSPProcessor


class WesternUnionHandler(FSPProcessor):
    def notify(self, records):
        for record in records:
            send_money(record.get_payload())

from hope_payment_gateway.apps.western_union.endpoints.send_money import send_money
from hope_payment_gateway.apps.western_union.registry import FSPProcessor


class WesternUnionHandler(FSPProcessor):
    def notify(self, records):
        for record in records:
            send_money(record.get_payload())

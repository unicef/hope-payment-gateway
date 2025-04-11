from constance import config
from strategy_field.utils import fqn

from hope_payment_gateway.apps.fsp.tasks_utils import send_to_fsp, notify_records_to_fsp
from hope_payment_gateway.apps.fsp.western_union.api.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.western_union.models import Corridor
from hope_payment_gateway.apps.gateway.models import (
    PaymentRecord,
)
from hope_payment_gateway.config.celery import app


def western_union_notify(to_process_ids: list[PaymentRecord]) -> None:
    notify_records_to_fsp(fqn(WesternUnionClient), to_process_ids)


@app.task()  # queue="executors"
def western_union_send_task(tag=None, threshold=10000):
    """Task to trigger Western Union payments."""
    fsp = "WesternUnion"
    fsp_vendor_number = config.WESTERN_UNION_VENDOR_NUMBER
    threshold = threshold or config.WESTERN_UNION_THREASHOLD
    action_fqn = western_union_notify
    group_key = "wu-send-instruction"

    send_to_fsp(fsp, fsp_vendor_number, action_fqn, group_key, threshold, tag)


@app.task
def update_corridors():
    WesternUnionClient().das_countries_currencies(create_corridors=True)


@app.task
def update_templates():
    client = WesternUnionClient()
    for corridor in Corridor.objects.all():
        client.das_delivery_option_template(
            corridor.destination_country,
            corridor.destination_currency,
            corridor.template_code,
        )

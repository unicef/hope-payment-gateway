from constance import config
from strategy_field.utils import fqn

from hope_payment_gateway.api.western_union.client import WesternUnionClient
from hope_payment_gateway.apps.fsp.tasks_utils import notify_records_to_fsp, send_to_fsp
from hope_payment_gateway.apps.fsp.western_union.models import Corridor
from hope_payment_gateway.apps.gateway.models import PaymentRecord
from hope_payment_gateway.config.celery import app


def western_union_notify(instruction_id: int) -> None:
    notify_records_to_fsp(fqn(WesternUnionClient), instruction_id)


@app.task()  # queue="executors"
def western_union_send_task():
    """Task to trigger Western Union payments."""
    fsp = "WesternUnion"
    fsp_vendor_number = config.WESTERN_UNION_VENDOR_NUMBER
    action_fqn = western_union_notify
    group_key = "wu-send-instruction"
    send_to_fsp(fsp, fsp_vendor_number, action_fqn, group_key)


def western_union_update_status(ids: list[int] | None = None) -> None:
    client = WesternUnionClient()
    qs = PaymentRecord.objects.select_related("parent__fsp").filter(
        parent__fsp__vendor_number=config.WESTERN_UNION_VENDOR_NUMBER
    )
    if ids:
        qs = qs.filter(id__in=ids)
    for record in qs:
        client.status(record.fsp_code, True)


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

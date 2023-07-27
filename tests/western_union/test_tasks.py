from unittest.mock import patch

from hope_payment_gateway.apps.western_union.tasks import send_money


@patch("hope_payment_gateway.apps.western_union.tasks.send_money_complete")
def test_send_money_task(django_app, admin_user):
    send_money()

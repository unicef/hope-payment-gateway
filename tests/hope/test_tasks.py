from unittest.mock import patch

from hope_payment_gateway.apps.hope.tasks import send_money_task


@patch("hope_payment_gateway.apps.hope.tasks.send_money")
def test_send_money_task(django_app, admin_user):
    send_money_task()


@patch("hope_payment_gateway.apps.hope.tasks.send_money")
def test_send_money_task_ba(django_app, admin_user):
    send_money_task(ba="afghanistan")

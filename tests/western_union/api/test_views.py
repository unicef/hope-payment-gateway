from django.urls import reverse

import pytest

from tests.factories import PaymentRecordFactory


@pytest.mark.parametrize(
    "action,detail,status",
    [
        ("list", False, 200),
        ("detail", True, 200),
        ("open", True, 200),
        ("ready", True, 400),
        ("close", True, 400),
        ("cancel", True, 200),
    ],
)
def test_payment_instruction_list(django_app, admin_user, action, detail, status):
    pr = PaymentRecordFactory()
    if detail:
        url = reverse(f"rest:payment-instruction-{action}", args=[pr.parent.uuid])
    else:
        url = reverse(f"rest:payment-instruction-{action}")
    view = django_app.get(url, user=admin_user, expect_errors=True)
    assert view.status_code == status


@pytest.mark.parametrize(
    "action,detail,status",
    [
        ("list", False, 200),
        ("detail", True, 200),
    ],
)
def test_payment_record_list(django_app, admin_user, action, detail, status):
    pr = PaymentRecordFactory()
    if detail:
        url = reverse(f"rest:payment-record-{action}", args=[pr.uuid])
    else:
        url = reverse(f"rest:payment-record-{action}")
    view = django_app.get(url, user=admin_user)
    assert view.status_code == status

from django.urls import reverse
from django.contrib import messages


def assert_error_redirect(response, payment_record):
    assert response.status_code == 302
    assert response.url == reverse("admin:gateway_paymentrecord_change", args=[payment_record.pk])
    user_messages = list(response.wsgi_request._messages)
    assert len(user_messages) == 1
    assert user_messages[0].level == messages.ERROR

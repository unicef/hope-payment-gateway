from django.core import mail
from django.core.mail import send_mail
import pytest
from pytest_django.fixtures import SettingsWrapper


@pytest.fixture
def mail_backend(settings: SettingsWrapper) -> None:
    settings.EMAIL_BACKEND = "anymail.backends.test.EmailBackend"


def test_mail_configuration(mail_backend: None, settings: SettingsWrapper) -> None:
    subject = "Test subject"
    body = "Test body"
    from_email = "to@example.com"
    to_emails = ["user@example.com"]
    send_mail(subject, body, from_email, to_emails)

    assert len(mail.outbox) == 1

    mail0 = mail.outbox[0]
    assert mail0.subject == subject
    assert mail0.body == body
    assert mail0.from_email == from_email
    assert mail0.to == to_emails

    connection = mail0.connection
    assert connection.debug_api_requests == settings.ANYMAIL["DEBUG_API_REQUESTS"]
    assert connection.ignore_recipient_status == settings.ANYMAIL["IGNORE_RECIPIENT_STATUS"]
    assert connection.ignore_unsupported_features == settings.ANYMAIL["IGNORE_UNSUPPORTED_FEATURES"]

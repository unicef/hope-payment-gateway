from typing import Any

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.models import LogEntry
from django.core.mail import send_mail
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.forms import Form
from django.http import HttpRequest

from admin_extra_buttons.decorators import button
from adminfilters.autocomplete import AutoCompleteFilter
from smart_admin.modeladmin import SmartModelAdmin
from unicef_security.admin import is_superuser

from .fields import ChoiceArrayField
from .models import APILogEntry, APIToken

TOKEN_INFO_EMAIL = """
Dear {friendly_name},

please find below API token info

Name: {obj}
Key: {obj.key}
Grants: {obj.grants}
Expires: {expire}

Regards

The HOPE Team
"""  # noqa

TOKEN_CREATED_EMAIL = """
Dear {friendly_name},

you have been assigned a new API token.

Name: {obj}
Key: {obj.key}
Grants: {obj.grants}
Expires: {expire}

Regards

The HOPE Team
"""  # noqa

TOKEN_UPDATED_EMAIL = """
Dear {friendly_name},

your assigned API token {obj} has been updated.

Grants: {obj.grants}
Expires: {expire}


Regards

The HOPE Team
"""  # noqa


class APITokenForm(forms.ModelForm):
    class Meta:
        model = APIToken
        fields = ("user", "allowed_ips", "valid_from", "valid_to", "grants")


@admin.register(APIToken)
class APITokenAdmin(SmartModelAdmin):
    list_display = ("__str__", "user", "valid_from", "valid_to", "key")
    list_filter = (("user", AutoCompleteFilter),)
    autocomplete_fields = ("user",)
    formfield_overrides = {
        ChoiceArrayField: {"widget": forms.CheckboxSelectMultiple},
    }
    form = APITokenForm
    search_fields = ("id",)
    readonly_fields = ("key",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related("user")

    def get_fields(self, request: HttpRequest, obj: Any | None = None) -> tuple[str, ...]:
        if obj:
            return super().get_fields(request, obj)
        return "user", "grants", "valid_to"

    def get_readonly_fields(self, request: HttpRequest, obj: Any | None = None) -> tuple[str, ...]:
        if obj:
            return "user", "valid_from"
        return ()

    def _get_email_context(self, request: HttpRequest, obj: Any) -> dict[str, Any]:
        return {
            "obj": obj,
            "friendly_name": obj.user.first_name or obj.user.username,
            "expire": obj.valid_to or "Never",
        }

    def _send_token_email(self, request: HttpRequest, obj: Any, template: str) -> None:
        try:
            send_mail(
                f"HOPE API Token {obj} infos",
                template.format(**self._get_email_context(request, obj)),
                None,
                recipient_list=[obj.user.email],
            )
            self.message_user(request, f"Email sent to {obj.user.email}", messages.SUCCESS)
        except OSError:
            self.message_user(
                request,
                f"Unable to send notification email to {obj.user.email}",
                messages.ERROR,
            )

    @button(permission=is_superuser)
    def resend_email(self, request: HttpRequest, pk: int) -> None:
        obj = self.get_object(request, str(pk))
        self._send_token_email(request, obj, TOKEN_INFO_EMAIL)

    def log_addition(self, request: HttpRequest, obj: Any, message: str) -> LogEntry:
        return super().log_addition(request, obj, message)

    @atomic()
    def save_model(self, request: HttpRequest, obj: Any, form: Form, change: bool) -> None:
        obj.save()
        if change:
            self._send_token_email(request, obj, TOKEN_UPDATED_EMAIL)
        else:
            self._send_token_email(request, obj, TOKEN_CREATED_EMAIL)


@admin.register(APILogEntry)
class APILogEntryAdmin(SmartModelAdmin):
    list_display = ("timestamp", "method", "url", "token")
    list_filter = (("token", AutoCompleteFilter),)
    date_hierarchy = "timestamp"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
        return False

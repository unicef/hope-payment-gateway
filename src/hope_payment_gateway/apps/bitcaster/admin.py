from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.contrib import admin, messages

from hope_payment_gateway.apps.bitcaster.client import get_hope_bitcaster_client

if TYPE_CHECKING:  # pragma: no cover
    from django.db.models import QuerySet
    from django.http import HttpRequest


@admin.action(description="Sync selected users to Bitcaster")
def sync_to_bitcaster(modeladmin: admin.ModelAdmin, request: "HttpRequest", queryset: "QuerySet[Any]") -> None:
    client = get_hope_bitcaster_client()
    if client is None:
        modeladmin.message_user(request, "Bitcaster is not enabled or configured.", messages.WARNING)
        return
    count = 0
    for user in queryset.iterator():
        client.register_user(user)
        count += 1
    modeladmin.message_user(request, f"Synced {count} user(s) to Bitcaster.", messages.SUCCESS)


class BitcasterUserAdminMixin:
    def get_actions(self, request: "HttpRequest") -> dict:
        actions = super().get_actions(request)
        if settings.BITCASTER_ENABLED:
            actions["sync_to_bitcaster"] = self.get_action(sync_to_bitcaster)
        return actions

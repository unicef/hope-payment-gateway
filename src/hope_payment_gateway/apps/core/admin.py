from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.contrib import admin, messages
from unicef_security.admin import UserAdminPlus

from hope_payment_gateway.apps.bitcaster.tasks import sync_user_to_bitcaster
from hope_payment_gateway.apps.core.models import System, User

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest

admin.site.site_header = "Payment Gateway"


@admin.action(description="Sync selected users to Bitcaster")
def sync_to_bitcaster(modeladmin: admin.ModelAdmin, request: "HttpRequest", queryset: "QuerySet[Any]") -> None:
    count = 0
    for user in queryset.iterator():
        sync_user_to_bitcaster.delay(user.pk)
        count += 1
    modeladmin.message_user(request, f"Queued {count} user(s) for Bitcaster sync.", messages.SUCCESS)


@admin.register(User)
class UserAdminPlus(UserAdminPlus):
    def get_actions(self, request: "HttpRequest") -> dict:
        actions = super().get_actions(request)
        if settings.BITCASTER_ENABLED:
            actions["sync_to_bitcaster"] = self.get_action(sync_to_bitcaster)
        return actions


@admin.register(System)
class SystemAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "owner")
    raw_id_fields = ("owner",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("owner")

from django.contrib import admin

from unicef_security.admin import UserAdminPlus

from hope_payment_gateway.apps.core.models import System, User

admin.site.site_header = "Payment Gateway"


@admin.register(User)
class UserAdminPlus(UserAdminPlus):
    pass


@admin.register(System)
class SystemAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "owner")

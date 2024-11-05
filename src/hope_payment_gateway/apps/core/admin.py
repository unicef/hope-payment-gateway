from django.contrib import admin

from unicef_security.admin import UserAdminPlus

from hope_payment_gateway.apps.core.models import System, User

admin.site.site_header = "Payment Gateway"


@admin.register(User)
class UserAdminPlus(UserAdminPlus):

    all_fieldsets = (
        (None, {"fields": (("username", "azure_id"), "password")}),
        (
            "Personal info",
            {
                "fields": (
                    (
                        "first_name",
                        "last_name",
                    ),
                    ("email", "display_name"),
                    ("job_title",),
                )
            },
        ),
        ("NEW", {"fields": ("last_login",)}),
        ("OLD", {"fields": ("date_joined",)}),
    )


@admin.register(System)
class SystemAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "owner")

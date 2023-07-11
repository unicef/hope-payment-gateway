from django.contrib import admin

from hope_payment_gateway.apps.hope.models import (
    BusinessArea,
    FinancialServiceProvider,
    PaymentPlan,
    PaymentRecord,
    Programme,
    ProgrammeCycle,
)


class ReadOnlyMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class LimitedUpdateMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [
            field.name
            for field in PaymentRecord._meta.fields
            if field.name not in PaymentRecord.CustomMeta.updatable_fields
        ]


@admin.register(BusinessArea)
class BusinessAreaAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = ("name", "code", "slug")
    search_fields = ("name", "code", "slug")


@admin.register(FinancialServiceProvider)
class FinancialServiceProviderAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = ("name", "communication_channel")
    search_fields = ("name", "communication_channel")


@admin.register(Programme)
class ProgrammeAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = ("get_business_area", "name", "status", "start_date", "end_date")
    search_fields = ("name",)
    list_filter = ("status", "business_area__name")

    @admin.display(ordering="business_area__name", description="Business Area")
    def get_business_area(self, obj):
        return obj.business_area.name


@admin.register(ProgrammeCycle)
class ProgrammeCycleAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = ("get_business_area", "get_programme", "iteration", "status", "start_date", "end_date")
    search_fields = ("program__name",)
    list_filter = ("status", "program__business_area__name", "program__name")

    @admin.display(ordering="program__business_area__name", description="Business Area")
    def get_business_area(self, obj):
        return obj.program.business_area.name

    @admin.display(ordering="program__business_area__name", description="Programme")
    def get_programme(self, obj):
        return obj.program.name


@admin.register(PaymentPlan)
class PaymentPlanAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = (
        "unicef_id",
        "get_programme",
        "get_programme_cycle",
        "status",
        "start_date",
        "end_date",
        "is_follow_up",
    )
    list_filter = ("status", "business_area")
    search_fields = ("unicef_id",)

    @admin.display(ordering="program__business_area__name", description="Programme")
    def get_programme(self, obj):
        return obj.program.name

    @admin.display(ordering="program_cycle__iteration", description="Iteration")
    def get_programme_cycle(self, obj):
        return getattr(obj.program_cycle, "iteration", "-")


@admin.register(PaymentRecord)
class PaymentRecordAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = (
        "get_business_area",
        "get_parent",
        "get_programme",
        "delivery_type",
        "status",
        "currency",
        "entitlement_quantity",
        "delivered_quantity",
        "entitlement_date",
        "transaction_reference_id",
    )
    list_filter = (
        "status",
        "parent__business_area__name",
        "conflicted",
        "excluded",
    )
    search_fields = ("parent__unicef_id",)
    # list_editable = ("status",)

    @admin.display(ordering="programme__name", description="Programme")
    def get_programme(self, obj):
        return obj.program.name

    @admin.display(ordering="parent__program_cycle__iteration", description="Payment Plan")
    def get_parent(self, obj):
        return obj.parent.unicef_id

    @admin.display(ordering="business_area__name", description="Business Area")
    def get_business_area(self, obj):
        return obj.business_area.name

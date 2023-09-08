from django.contrib import admin, messages
from django.template.response import TemplateResponse

from admin_extra_buttons.decorators import button, choice, view
from admin_extra_buttons.mixins import ExtraButtonsMixin

from hope_payment_gateway.apps.hope.models import (
    BusinessArea,
    FinancialServiceProvider,
    PaymentHouseholdSnapshot,
    PaymentPlan,
    PaymentRecord,
    Programme,
    ProgrammeCycle,
)
from hope_payment_gateway.apps.hope.payloads.send_money_validation_payload import get_send_money_validation_payload
from hope_payment_gateway.apps.western_union.endpoints.cancel import cancel, search_request
from hope_payment_gateway.apps.western_union.endpoints.send_money import (
    create_validation_payload,
    send_money,
    send_money_validation,
)
from hope_payment_gateway.apps.western_union.models import PaymentRecordLog


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


class PaymentHouseholdSnapshotInline(admin.TabularInline):
    model = PaymentHouseholdSnapshot
    # readonly_fields = ("snapshot_data", "household_id")


@admin.register(PaymentRecord)
class PaymentRecordAdmin(ExtraButtonsMixin, LimitedUpdateMixin, admin.ModelAdmin):
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
        "token_number",
    )
    list_filter = (
        "status",
        "parent__business_area__name",
        "conflicted",
        "excluded",
    )
    search_fields = ("parent__unicef_id", "unicef_id", "transaction_reference_id")

    inlines = (PaymentHouseholdSnapshotInline,)

    @admin.display(ordering="programme__name", description="Programme")
    def get_programme(self, obj):
        return obj.program.name

    @admin.display(ordering="parent__program_cycle__iteration", description="Payment Plan")
    def get_parent(self, obj):
        return obj.parent.unicef_id

    @admin.display(ordering="business_area__name", description="Business Area")
    def get_business_area(self, obj):
        return obj.business_area.name

    @choice(change_list=False)
    def primitives(self, button):
        button.choices = [self.send_money_validation, self.search_request]
        return button

    @view(html_attrs={"style": "background-color:#88FF88;color:black"})
    def send_money_validation(self, request, pk) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        context["msg"] = "First call: check if data is valid \n it returns MTCN"
        hope_payload = get_send_money_validation_payload(pk)
        payload = create_validation_payload(hope_payload)
        context.update(send_money_validation(payload))
        return TemplateResponse(request, "western_union.html", context)

    @button()
    def send_money(self, request, pk) -> TemplateResponse:
        hope_payload = get_send_money_validation_payload(pk)
        log = send_money(hope_payload)
        loglevel = messages.SUCCESS if log.success else messages.ERROR
        messages.add_message(request, loglevel, log.message)

    @view(html_attrs={"style": "background-color:yellow;color:blue"})
    def search_request(self, request, pk) -> TemplateResponse:
        context = self.get_common_context(request, pk)
        obj = PaymentRecord.objects.get(pk=pk)
        log = PaymentRecordLog.objects.get(record_code=obj.unicef_id)
        if mtcn := log.extra_data.get("mtcn", None):
            context["msg"] = f"Search request through MTCN \n" f"PARAM: mtcn {mtcn}"
            context.update(search_request(log.record_code, mtcn))
            return TemplateResponse(request, "western_union.html", context)
        messages.warning(request, "Missing MTCN")

    @button()
    def cancel(self, request, pk) -> TemplateResponse:
        context = self.get_common_context(request, pk)

        obj = PaymentRecord.objects.get(pk=pk)
        log = PaymentRecordLog.objects.get(record_code=obj.unicef_id)
        if mtcn := log.extra_data.get("mtcn", None):
            context["msg"] = f"Search request through MTCN \n" f"PARAM: mtcn {mtcn}"
        log = cancel(log.record_code, mtcn)
        loglevel = messages.SUCCESS if log.success else messages.ERROR
        messages.add_message(request, loglevel, log.message)

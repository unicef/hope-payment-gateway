import django_filters
from django_filters import rest_framework as filters

from hope_payment_gateway.apps.gateway.models import (
    AccountType,
    DeliveryMechanism,
    ExportTemplate,
    FinancialServiceProvider,
    FinancialServiceProviderConfig,
    PaymentInstruction,
    PaymentRecord,
)


class AccountTypeFilter(filters.FilterSet):
    class Meta:
        model = AccountType
        fields = {
            "key": ["exact"],
            "label": ["exact", "contains"],
        }


class DeliveryMechanismFilter(filters.FilterSet):
    class Meta:
        model = DeliveryMechanism
        fields = {
            "code": ["exact"],
            "name": ["exact", "contains"],
            "transfer_type": ["exact"],
        }


class FinancialServiceProviderFilter(filters.FilterSet):
    class Meta:
        model = FinancialServiceProvider
        fields = {
            "remote_id": ["exact"],
            "name": ["exact"],
            "vendor_number": ["exact"],
        }


class FinancialServiceProviderConfigFilter(filters.FilterSet):
    delivery_mechanism_name = django_filters.CharFilter(
        field_name="delivery_mechanism__name", lookup_expr="starts_with"
    )
    fsp_name = django_filters.CharFilter(field_name="fsp__name", lookup_expr="starts_with")

    class Meta:
        model = FinancialServiceProviderConfig
        fields = {
            "key": ["exact"],
            "fsp": ["exact"],
            "delivery_mechanism": ["exact"],
        }


class PaymentInstructionFilter(filters.FilterSet):
    class Meta:
        model = PaymentInstruction
        fields = {
            "remote_id": ["exact"],
            "external_code": ["exact", "in"],
            "status": ["exact", "in"],
        }


class PaymentRecordFilter(filters.FilterSet):
    class Meta:
        model = PaymentRecord
        fields = {
            "created": ["lt", "lte", "gt", "gte"],
            "modified": ["lt", "lte", "gt", "gte"],
            "remote_id": ["exact"],
            "record_code": ["exact", "in"],
            "parent__remote_id": ["exact", "in"],
            "status": ["exact", "in"],
        }


class ExportTemplateFilter(filters.FilterSet):
    class Meta:
        model = ExportTemplate
        fields = {
            "fsp": ["exact"],
            "config_key": ["exact"],
        }

from django_filters import rest_framework as filters

from hope_payment_gateway.apps.gateway.models import (
    FinancialServiceProvider,
    FinancialServiceProviderConfig,
    PaymentInstruction,
    PaymentRecord,
)


class FinancialServiceProviderFilter(filters.FilterSet):
    class Meta:
        model = FinancialServiceProvider
        fields = {
            "remote_id": ["exact"],
            "name": ["exact"],
            "vision_vendor_number": ["exact"],
        }


class FinancialServiceProviderConfigFilter(filters.FilterSet):
    class Meta:
        model = FinancialServiceProviderConfig
        fields = {
            "key": ["exact"],
            "fsp": ["exact"],
        }


class PaymentInstructionFilter(filters.FilterSet):
    class Meta:
        model = PaymentInstruction
        fields = {
            "remote_id": ["exact"],
            "unicef_id": ["exact", "in"],
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

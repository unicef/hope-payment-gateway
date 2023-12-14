from django_filters import rest_framework as filters

from hope_payment_gateway.apps.gateway.models import FinancialServiceProvider, PaymentInstruction, PaymentRecord


class FinancialServiceProviderFilter(filters.FilterSet):
    class Meta:
        model = FinancialServiceProvider
        fields = {
            "name": ["exact"],
            "vision_vendor_number": ["exact"],
        }


class PaymentInstructionFilter(filters.FilterSet):
    class Meta:
        model = PaymentInstruction
        fields = {
            "uuid": ["exact"],
            "unicef_id": ["exact", "in"],
            "status": ["exact", "in"],
        }


class PaymentRecordFilter(filters.FilterSet):
    class Meta:
        model = PaymentRecord
        fields = {
            "created": ["lt", "lte", "gt", "gte"],
            "modified": ["lt", "lte", "gt", "gte"],
            "uuid": ["exact"],
            "record_code": ["exact", "in"],
            "parent__uuid": ["exact", "in"],
            "status": ["exact", "in"],
        }

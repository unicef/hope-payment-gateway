from django_filters import rest_framework as filters

from hope_payment_gateway.apps.gateway.models import PaymentInstruction, PaymentRecord


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
            "uuid": ["exact"],
            "record_code": ["exact", "in"],
            "parent__uuid": ["exact", "in"],
            "status": ["exact", "in"],
        }

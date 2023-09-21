from django_filters import rest_framework as filters

from hope_payment_gateway.apps.western_union.models import PaymentRecordLog, PaymentInstruction


class PaymentInstructionFilter(filters.FilterSet):
    class Meta:
        model = PaymentInstruction
        fields = {
            "uuid": ["exact"],
            "unicef_id": ["exact", "in"],
            "status": ["exact", "in"],
        }


class PaymentRecordLogFilter(filters.FilterSet):
    class Meta:
        model = PaymentRecordLog
        fields = {
            "uuid": ["exact"],
            "record_code": ["exact", "in"],
            "parent__uuid": ["exact", "in"],
            "status": ["exact", "in"],
        }

from rest_framework import serializers

from hope_payment_gateway.apps.western_union.models import PaymentInstruction, PaymentRecordLog


class PaymentInstructionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentInstruction
        fields = (
            "id",
            "uuid",
            "unicef_id",
            "status",
            "payload",
        )


class PaymentRecordLogLightSerializer(serializers.ModelSerializer):
    parent = serializers.ReadOnlyField(source='parent.uuid')

    class Meta:
        model = PaymentRecordLog
        fields = (
            "id",
            "uuid",
            "record_code",
            "parent",
            "status",
            "success",
        )


class PaymentRecordLogSerializer(serializers.ModelSerializer):
    parent = serializers.SlugRelatedField(slug_field='uuid', queryset=PaymentInstruction.objects.all())

    class Meta:
        model = PaymentRecordLog
        fields = (
            "id",
            "uuid",
            "record_code",
            "parent",
            "status",
            "success",
            "message",
            "payload",
            "extra_data",
        )

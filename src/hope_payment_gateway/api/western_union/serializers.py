from rest_framework import serializers

from hope_payment_gateway.apps.western_union.models import PaymentInstruction, PaymentRecord


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


class PaymentRecordLightSerializer(serializers.ModelSerializer):
    parent = serializers.ReadOnlyField(source="parent.uuid")

    class Meta:
        model = PaymentRecord
        fields = (
            "id",
            "uuid",
            "record_code",
            "parent",
            "status",
            "success",
        )


class PaymentRecordSerializer(serializers.ModelSerializer):
    parent = serializers.SlugRelatedField(slug_field="uuid", queryset=PaymentInstruction.objects.all())

    class Meta:
        model = PaymentRecord
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

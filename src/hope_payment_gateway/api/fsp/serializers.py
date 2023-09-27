from rest_framework import serializers

from hope_payment_gateway.apps.gateway.models import FinancialServiceProvider, PaymentInstruction, PaymentRecord


class PaymentInstructionSerializer(serializers.ModelSerializer):
    fsp = serializers.SlugRelatedField(
        slug_field="vision_vendor_number", queryset=FinancialServiceProvider.objects.all()
    )
    system = serializers.PrimaryKeyRelatedField(read_only=True)  # handled in the view

    class Meta:
        model = PaymentInstruction
        fields = (
            "id",
            "uuid",
            "unicef_id",
            "status",
            "fsp",
            "system",
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

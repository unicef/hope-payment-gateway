from rest_framework import serializers

from hope_payment_gateway.apps.gateway.models import FinancialServiceProvider, PaymentInstruction, PaymentRecord


class FinancialServiceProviderSerializer(serializers.ModelSerializer):
    payload = serializers.SerializerMethodField()

    class Meta:
        model = FinancialServiceProvider
        fields = ("name", "vision_vendor_number", "configuration", "payload")

    def get_payload(self):
        return {
            'instruction': {
                "destination_country": "mandatory: CO",
                "destination_currency": "mandatory: COP",
                "country_code": "optional: 63",
                "reason_for_sending": "optional: P20",
                "delivery_services_code": "optional: 000 (money in minutes) 800 (wallet)",
                "corridor": "optional: Benin",
                "service_provider_code": "optional: 06301",
                "transaction_type": "optional: WMF (fixed money transfer) WMN (money transfer)",
                "duplication_enabled": "optional: D"
            },
            'record': {
                "amount": "mandatory: 20000",
                "first_name": "mandatory: Jason",
                "last_name": "mandatory: Yorker",
                "phone_no": "optional: 63123123",
            }
        }


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

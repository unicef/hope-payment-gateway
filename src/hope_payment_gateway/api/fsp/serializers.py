from typing import Any

from rest_framework import serializers

from hope_payment_gateway.apps.gateway.models import (
    DeliveryMechanism,
    ExportTemplate,
    FinancialServiceProvider,
    FinancialServiceProviderConfig,
    PaymentInstruction,
    PaymentRecord,
    AccountType,
)


class PayloadMixin:
    payload = serializers.SerializerMethodField()

    def get_payload(self, obj: Any) -> Any:
        return {
            "instruction": {
                "destination_country": "mandatory: CO",
                "destination_currency": "mandatory: COP",
                "country_code": "optional: 63",
                "reason_for_sending": "optional: P20",
                "delivery_services_code": "optional: 000 (money in minutes) 800 (wallet)",
                "corridor": "optional: Benin",
                "service_provider_code": "optional: 06301",
                "transaction_type": "optional: WMF (fixed money transfer) WMN (money transfer)",
                "duplication_enabled": "optional: D",
            },
            "record": {
                "amount": "mandatory: 20000",
                "first_name": "mandatory: Jason",
                "last_name": "mandatory: Yorker",
                "phone_no": "optional: 63123123",
            },
        }


class AccountTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountType
        fields = ("id", "key", "label", "unique_fields")


class DeliveryMechanismSerializer(PayloadMixin, serializers.ModelSerializer):
    class Meta:
        model = DeliveryMechanism
        fields = ("id", "code", "name", "description", "account_type", "transfer_type")


class FinancialServiceProviderConfigNestedSerializer(serializers.ModelSerializer):
    delivery_mechanism_name = serializers.CharField(source="delivery_mechanism.name", allow_null=True)
    delivery_mechanism_code = serializers.CharField(source="delivery_mechanism.code", allow_null=True)
    delivery_mechanism_transfer_type = serializers.CharField(source="delivery_mechanism.transfer_type", allow_null=True)

    class Meta:
        model = FinancialServiceProviderConfig
        fields = (
            "id",
            "key",
            "label",
            "delivery_mechanism",
            "delivery_mechanism_name",
            "delivery_mechanism_transfer_type",
            "delivery_mechanism_code",
            "required_fields",
        )


class FinancialServiceProviderLightSerializer(PayloadMixin, serializers.ModelSerializer):
    class Meta:
        model = FinancialServiceProvider
        fields = (
            "id",
            "name",
            "vendor_number",
        )


class FinancialServiceProviderSerializer(PayloadMixin, serializers.ModelSerializer):
    configs = FinancialServiceProviderConfigNestedSerializer(many=True, read_only=True)

    class Meta:
        model = FinancialServiceProvider
        fields = (
            "id",
            "remote_id",
            "name",
            "vendor_number",
            "configs",
        )


class FinancialServiceProviderConfigSerializer(serializers.ModelSerializer):
    fsp = FinancialServiceProviderLightSerializer()
    delivery_mechanism = DeliveryMechanismSerializer()

    class Meta:
        model = FinancialServiceProviderConfig
        fields = (
            "id",
            "key",
            "label",
            "fsp",
            "delivery_mechanism",
        )


class PaymentInstructionSerializer(serializers.ModelSerializer):
    fsp = serializers.PrimaryKeyRelatedField(queryset=FinancialServiceProvider.objects.all())
    system = serializers.PrimaryKeyRelatedField(read_only=True)  # handled in the view

    class Meta:
        model = PaymentInstruction
        fields = (
            "id",
            "remote_id",
            "external_code",
            "active",
            "status",
            "fsp",
            "system",
            "payload",
            "extra",
        )

    def create(self, validated_data):
        try:
            instance = PaymentInstruction.objects.get(
                remote_id=validated_data["remote_id"], system=validated_data["system"]
            )
        except PaymentInstruction.DoesNotExist:
            instance = None

        if instance:
            return super().update(instance, validated_data)
        return super().create(validated_data)


class PaymentRecordLightSerializer(serializers.ModelSerializer):
    parent = serializers.ReadOnlyField(source="parent.remote_id")

    class Meta:
        model = PaymentRecord
        fields = (
            "id",
            "remote_id",
            "created",
            "modified",
            "record_code",
            "fsp_code",
            "auth_code",
            "parent",
            "status",
            "message",
            "payout_amount",
            "payout_date",
        )


class PaymentRecordSerializer(PaymentRecordLightSerializer):
    parent = serializers.SlugRelatedField(slug_field="remote_id", queryset=PaymentInstruction.objects.all())

    class Meta:
        model = PaymentRecord
        fields = (
            "id",
            "remote_id",
            "created",
            "modified",
            "record_code",
            "fsp_code",
            "auth_code",
            "parent",
            "status",
            "message",
            "payload",
            "payout_amount",
        )


class ExportTemplateSerializer(serializers.ModelSerializer):
    fsp = serializers.PrimaryKeyRelatedField(queryset=FinancialServiceProvider.objects.all())

    class Meta:
        model = ExportTemplate
        fields = ("query", "fsp", "config_key")

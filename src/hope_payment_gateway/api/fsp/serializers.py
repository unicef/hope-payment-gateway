from rest_framework import serializers

from hope_payment_gateway.apps.gateway.models import (
    AccountType,
    DeliveryMechanism,
    ExportTemplate,
    FinancialServiceProvider,
    FinancialServiceProviderConfig,
    PaymentInstruction,
    PaymentRecord,
    Office,
    Country,
)


class AccountTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountType
        fields = ("id", "key", "label", "unique_fields")


class OfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Office
        fields = ("id", "name", "code", "slug")


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ("id", "name", "iso_code2", "iso_code3")


class DeliveryMechanismSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryMechanism
        fields = ("id", "code", "name", "description", "account_type", "transfer_type")


class FinancialServiceProviderConfigNestedSerializer(serializers.ModelSerializer):
    country_iso_code2 = serializers.CharField(source="country.iso_code2", allow_null=True)
    country_iso_code3 = serializers.CharField(source="country.iso_code3", allow_null=True)
    office_code = serializers.CharField(source="office.code", allow_null=True)
    office_slug = serializers.CharField(source="office.slug", allow_null=True)
    delivery_mechanism_name = serializers.CharField(source="delivery_mechanism.name", allow_null=True)
    delivery_mechanism_code = serializers.CharField(source="delivery_mechanism.code", allow_null=True)
    delivery_mechanism_transfer_type = serializers.CharField(source="delivery_mechanism.transfer_type", allow_null=True)

    class Meta:
        model = FinancialServiceProviderConfig
        fields = (
            "id",
            "label",
            "key",
            "office",
            "office_code",
            "office_slug",
            "country",
            "country_iso_code2",
            "country_iso_code3",
            "delivery_mechanism",
            "delivery_mechanism_name",
            "delivery_mechanism_transfer_type",
            "delivery_mechanism_code",
            "required_fields",
        )


class FinancialServiceProviderLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialServiceProvider
        fields = (
            "id",
            "name",
            "vendor_number",
        )


class FinancialServiceProviderSerializer(serializers.ModelSerializer):
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
    office = OfficeSerializer()
    country = CountrySerializer()

    class Meta:
        model = FinancialServiceProviderConfig
        fields = (
            "id",
            "key",
            "office",
            "country",
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
            "extra_data",
        )


class ExportTemplateSerializer(serializers.ModelSerializer):
    fsp = serializers.PrimaryKeyRelatedField(queryset=FinancialServiceProvider.objects.all())

    class Meta:
        model = ExportTemplate
        fields = ("query", "fsp", "config_key")

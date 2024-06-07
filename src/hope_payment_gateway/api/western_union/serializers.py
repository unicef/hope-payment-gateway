from rest_framework import serializers

from hope_payment_gateway.apps.fsp.western_union.models import Corridor, ServiceProviderCode


class CorridorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Corridor
        fields = ("id", "description", "destination_country", "destination_currency", "template_code", "template")


class ServiceProviderCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProviderCode
        fields = ("description", "code", "country", "currency")

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.serializers import Serializer

from hope_payment_gateway.apps.fsp.western_union.models import Corridor, ServiceProviderCode


class CorridorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Corridor
        fields = (
            "id",
            "description",
            "destination_country",
            "destination_currency",
            "template_code",
            "template",
        )


class ServiceProviderCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProviderCode
        fields = ("description", "code", "country", "currency")


class FileSerializer(Serializer):
    name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_name(self, obj):
        return str(obj)

    @extend_schema_field(OpenApiTypes.URI)
    def get_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(str(obj))

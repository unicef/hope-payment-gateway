from rest_framework import serializers

from hope_payment_gateway.apps.fsp.western_union.models import Corridor


class CorridorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Corridor
        fields = ("id", "description", "destination_country", "destination_currency", "template_code", "template")

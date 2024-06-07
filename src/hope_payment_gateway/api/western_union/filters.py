from django_filters import rest_framework as filters

from hope_payment_gateway.apps.fsp.western_union.models import Corridor, ServiceProviderCode


class CorridorFilter(filters.FilterSet):
    class Meta:
        model = Corridor
        fields = {
            "description": ["exact", "icontains"],
            "destination_country": ["exact"],
            "destination_currency": ["exact"],
            "template_code": ["exact"],
        }


class ServiceProviderCodeFilter(filters.FilterSet):
    class Meta:
        model = ServiceProviderCode
        fields = {
            "description": ["exact", "icontains"],
            "code": ["exact", "icontains"],
            "country": ["exact"],
            "currency": ["exact"],
        }

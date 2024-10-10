from django.utils import timezone

import factory
from factory import fuzzy
from strategy_field.utils import fqn

from hope_api_auth.models import APIToken, Grant
from hope_payment_gateway.apps.fsp.western_union.models import Corridor, ServiceProviderCode
from hope_payment_gateway.apps.gateway.models import (
    DeliveryMechanism,
    FinancialServiceProvider,
    FinancialServiceProviderConfig,
    PaymentInstruction,
    PaymentRecord,
)
from hope_payment_gateway.apps.gateway.registry import DefaultProcessor

from .user import SystemFactory, UserFactory


class CorridorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Corridor


class ServiceProviderCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceProviderCode


class DeliveryMechanismFactory(factory.django.DjangoModelFactory):
    code = fuzzy.FuzzyText()
    name = fuzzy.FuzzyText()

    class Meta:
        model = DeliveryMechanism


class FinancialServiceProviderFactory(factory.django.DjangoModelFactory):
    remote_id = fuzzy.FuzzyText()
    name = fuzzy.FuzzyText()
    vendor_number = fuzzy.FuzzyText()
    strategy = fqn(DefaultProcessor)

    class Meta:
        model = FinancialServiceProvider


class FinancialServiceProviderConfigFactory(factory.django.DjangoModelFactory):
    key = fuzzy.FuzzyText()
    label = fuzzy.FuzzyText()
    fsp = factory.SubFactory(FinancialServiceProviderFactory)
    delivery_mechanism = factory.SubFactory(DeliveryMechanismFactory)

    class Meta:
        model = FinancialServiceProviderConfig


class PaymentInstructionFactory(factory.django.DjangoModelFactory):
    fsp = factory.SubFactory(FinancialServiceProviderFactory)
    system = factory.SubFactory(SystemFactory)
    remote_id = fuzzy.FuzzyText()

    class Meta:
        model = PaymentInstruction


class PaymentRecordFactory(factory.django.DjangoModelFactory):
    remote_id = fuzzy.FuzzyText()
    record_code = fuzzy.FuzzyText()
    parent = factory.SubFactory(PaymentInstructionFactory)

    class Meta:
        model = PaymentRecord


class APITokenFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    allowed_ips = ""
    grants = [Grant.API_READ_ONLY]
    valid_from = timezone.now
    valid_to = None

    class Meta:
        model = APIToken
        django_get_or_create = ("user",)

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import signals
from django.utils import timezone

import factory
from factory import fuzzy
from strategy_field.utils import fqn

from hope_api_auth.models import APIToken, Grant
from hope_payment_gateway.apps.core.models import System
from hope_payment_gateway.apps.fsp.western_union.models import Corridor, ServiceProviderCode
from hope_payment_gateway.apps.gateway.models import (
    DeliveryMechanism,
    FinancialServiceProvider,
    FinancialServiceProviderConfig,
    PaymentInstruction,
    PaymentRecord,
)
from hope_payment_gateway.apps.gateway.registry import DefaultProcessor


@factory.django.mute_signals(signals.post_save)
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: "user%03d" % n)

    last_name = factory.Faker("last_name")
    first_name = factory.Faker("first_name")

    email = factory.Sequence(lambda n: "m%03d@mailinator.com" % n)
    password = "password"
    is_superuser = False
    is_active = True


class AdminFactory(UserFactory):
    is_superuser = True


class AnonUserFactory(UserFactory):
    username = "anonymous"


class GroupFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "name%03d" % n)

    @factory.post_generation
    def permissions(self, create, extracted, **kwargs):
        if not create:
            return  # Simple build, do nothing.

        if extracted:
            for permission in extracted:  # A list of groups were passed in, use them
                self.permissions.add(permission)

    class Meta:
        model = Group
        django_get_or_create = ("name",)


class CorridorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Corridor


class ServiceProviderCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceProviderCode


class SystemFactory(factory.django.DjangoModelFactory):
    name = fuzzy.FuzzyText()
    owner = factory.SubFactory(UserFactory)

    class Meta:
        model = System


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

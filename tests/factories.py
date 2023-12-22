from django.contrib.auth import get_user_model
from django.db.models import signals
from django.utils import timezone

import factory
from factory import fuzzy
from strategy_field.utils import fqn

from hope_api_auth.models import APIToken, Grant
from hope_payment_gateway.apps.core.models import System
from hope_payment_gateway.apps.fsp.western_union.models import Corridor
from hope_payment_gateway.apps.gateway.models import FinancialServiceProvider, PaymentInstruction, PaymentRecord
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


class CorridorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Corridor


class SystemFactory(factory.django.DjangoModelFactory):
    name = fuzzy.FuzzyText()
    owner = factory.SubFactory(UserFactory)

    class Meta:
        model = System


class FinancialServiceProviderFactory(factory.django.DjangoModelFactory):
    remote_id = fuzzy.FuzzyText()
    name = fuzzy.FuzzyText()
    vision_vendor_number = fuzzy.FuzzyText()
    strategy = fqn(DefaultProcessor)

    class Meta:
        model = FinancialServiceProvider


class PaymentInstructionFactory(factory.django.DjangoModelFactory):
    fsp = factory.SubFactory(FinancialServiceProviderFactory)
    system = factory.SubFactory(SystemFactory)
    remote_id = fuzzy.FuzzyText()

    class Meta:
        model = PaymentInstruction


class PaymentRecordFactory(factory.django.DjangoModelFactory):
    remote_id = fuzzy.FuzzyText()
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

import uuid

from django.contrib.auth import get_user_model
from django.db.models import signals

import factory

from hope_payment_gateway.apps.western_union.models import Corridor, PaymentInstruction, PaymentRecord


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


class PaymentInstructionFactory(factory.django.DjangoModelFactory):
    uuid = uuid.uuid4()

    class Meta:
        model = PaymentInstruction


class PaymentRecordFactory(factory.django.DjangoModelFactory):
    parent = factory.SubFactory(PaymentInstructionFactory)
    uuid = uuid.uuid4()

    class Meta:
        model = PaymentRecord

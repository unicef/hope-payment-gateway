from django.contrib.auth import get_user_model
from django.db.models import signals

import factory

from hope_payment_gateway.apps.hope.models import (
    BusinessArea,
    FinancialServiceProvider,
    PaymentPlan,
    PaymentRecord,
    Programme,
)


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


class BusinessAreaFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda x: "BusinessArea{}".format(x))
    code = factory.Sequence(lambda x: "BA{}".format(x))

    class Meta:
        model = BusinessArea
        django_get_or_create = ("code",)


class FinancialServiceProviderFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda x: "FSP{}".format(x))

    class Meta:
        model = FinancialServiceProvider
        django_get_or_create = ("code",)


class ProgrammeFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "%03d" % n)

    class Meta:
        model = Programme
        django_get_or_create = ("name",)


class PaymentPlanFactory(factory.django.DjangoModelFactory):
    code = factory.Sequence(lambda n: "code%03d" % n)
    business_area = factory.SubFactory(BusinessAreaFactory)

    class Meta:
        model = PaymentPlan
        django_get_or_create = ("code",)


class PaymentFactory(factory.django.DjangoModelFactory):
    code = factory.Sequence(lambda n: "code%03d" % n)
    payment_plan = factory.SubFactory(PaymentPlanFactory)

    class Meta:
        model = PaymentRecord
        django_get_or_create = ("code",)

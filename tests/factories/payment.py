import factory
from django.utils import timezone
from factory import fuzzy
from strategy_field.utils import fqn

from hope_api_auth.models import APILogEntry, APIToken, Grant
from hope_payment_gateway.apps.fsp.western_union.handlers import WesternUnionHandler
from hope_payment_gateway.apps.fsp.western_union.models import Corridor, ServiceProviderCode
from hope_payment_gateway.apps.gateway.models import (
    DeliveryMechanism,
    ExportTemplate,
    FinancialServiceProvider,
    FinancialServiceProviderConfig,
    PaymentInstruction,
    PaymentRecord,
)
from hope_payment_gateway.apps.gateway.registry import DefaultProcessor

from . import AutoRegisterModelFactory
from .user import SystemFactory, UserFactory


class CorridorFactory(AutoRegisterModelFactory):
    class Meta:
        model = Corridor


class ServiceProviderCodeFactory(AutoRegisterModelFactory):
    class Meta:
        model = ServiceProviderCode


class DeliveryMechanismFactory(AutoRegisterModelFactory):
    code = fuzzy.FuzzyText()
    name = fuzzy.FuzzyText()

    class Meta:
        model = DeliveryMechanism


class FinancialServiceProviderFactory(AutoRegisterModelFactory):
    remote_id = fuzzy.FuzzyText()
    name = fuzzy.FuzzyText()
    vendor_number = fuzzy.FuzzyText()
    strategy = fqn(DefaultProcessor)

    class Meta:
        model = FinancialServiceProvider


class FinancialServiceProviderConfigFactory(AutoRegisterModelFactory):
    key = fuzzy.FuzzyText()
    label = fuzzy.FuzzyText()
    fsp = factory.SubFactory(FinancialServiceProviderFactory)
    delivery_mechanism = factory.SubFactory(DeliveryMechanismFactory)

    class Meta:
        model = FinancialServiceProviderConfig


class PaymentInstructionFactory(AutoRegisterModelFactory):
    fsp = factory.SubFactory(FinancialServiceProviderFactory)
    system = factory.SubFactory(SystemFactory)
    remote_id = fuzzy.FuzzyText()

    class Meta:
        model = PaymentInstruction


class PaymentRecordFactory(AutoRegisterModelFactory):
    remote_id = fuzzy.FuzzyText()
    record_code = fuzzy.FuzzyText()
    parent = factory.SubFactory(PaymentInstructionFactory)

    class Meta:
        model = PaymentRecord


class APITokenFactory(AutoRegisterModelFactory):
    user = factory.SubFactory(UserFactory)
    allowed_ips = ""
    grants = [Grant.API_READ_ONLY]
    valid_from = timezone.now
    valid_to = None

    class Meta:
        model = APIToken
        django_get_or_create = ("user",)


class APILogEntryFactory(AutoRegisterModelFactory):
    token = factory.SubFactory(APITokenFactory)
    status_code = fuzzy.FuzzyDecimal(200, 599)

    class Meta:
        model = APILogEntry


class ExportTemplateFactory(AutoRegisterModelFactory):
    fsp = factory.SubFactory(FinancialServiceProviderFactory)
    delivery_mechanism = factory.SubFactory(DeliveryMechanismFactory)
    strategy = fqn(WesternUnionHandler)

    class Meta:
        model = ExportTemplate

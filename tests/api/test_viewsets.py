from django.urls import reverse

import pytest
from api_checker import LastModifiedRecorder, frozenfixture
from drf_api_checker.pytest import contract
from factories import (
    CorridorFactory,
    FinancialServiceProviderConfigFactory,
    FinancialServiceProviderFactory,
    PaymentInstructionFactory,
    PaymentRecordFactory,
    ServiceProviderCodeFactory,
)


@frozenfixture()
def fsp(request, db):
    return FinancialServiceProviderFactory()


@frozenfixture()
def p_instruction(request, fsp):
    return PaymentInstructionFactory(fsp=fsp)


@frozenfixture()
def p_record(request, db, p_instruction):
    return PaymentRecordFactory(parent=p_instruction)


@frozenfixture()
def corridor(request, db):
    return CorridorFactory()


@frozenfixture()
def service_provider_code(request, db):
    return ServiceProviderCodeFactory()


@frozenfixture()
def configuration(request, db, fsp):
    return FinancialServiceProviderConfigFactory(fsp=fsp)


@pytest.mark.django_db
@contract(LastModifiedRecorder)
def test_api_fsp(request, django_app, fsp):
    return reverse("api:fsp-list")


@pytest.mark.django_db
@contract(LastModifiedRecorder)
def test_api_payment_instructions(request, django_app, p_instruction):
    return reverse("api:payment-instruction-list")


@pytest.mark.django_db
@contract(LastModifiedRecorder)
def test_payment_records(request, django_app, p_record):
    return reverse("api:payment-record-list")


@pytest.mark.django_db
@contract(LastModifiedRecorder)
def test_api_config(request, django_app, configuration):
    return reverse("api:config-list")


@pytest.mark.django_db
@contract(LastModifiedRecorder)
def test_api_wu_corridors(request, django_app, corridor):
    return reverse("api:wu-corridor-list")


@pytest.mark.django_db
@contract(LastModifiedRecorder)
def test_api_wu_service_provider_code(request, django_app, service_provider_code):
    return reverse("api:wu-service-provider-code-list")

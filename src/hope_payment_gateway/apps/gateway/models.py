import csv

from adminactions.api import delimiters, quotes
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_celery_boost.models import AsyncJobModel
from model_utils.models import TimeStampedModel
from strategy_field.fields import StrategyField

from hope_payment_gateway.apps.core.models import System
from hope_payment_gateway.apps.gateway.registry import export_registry, registry


def default_requirements() -> dict:
    return {
        "required_fields": [],
        "optional_fields": [],
        "unique_fields": [],
    }


class AccountType(TimeStampedModel):
    key = models.CharField(max_length=255, unique=True)
    label = models.CharField(max_length=255)
    unique_fields = ArrayField(
        default=list,
        base_field=models.CharField(max_length=255),
        help_text="comma separated list of unique fields",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.label


class DeliveryMechanism(TimeStampedModel):
    IN_CASH = "IN_CASH"
    VOUCHER = "VOUCHER"
    DIGITAL = "DIGITAL"
    DELIVERY_MECHANISM_TYPE = (
        (IN_CASH, "In Cash"),
        (VOUCHER, "Voucher"),
        (DIGITAL, "Digital Asset"),
    )
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)
    account_type = models.ForeignKey(AccountType, on_delete=models.CASCADE, related_name="delivery_mechanisms")
    transfer_type = models.CharField(choices=DELIVERY_MECHANISM_TYPE, max_length=32)
    requirements = models.JSONField(default=default_requirements, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.name} [{self.code}]"


class Office(TimeStampedModel):
    remote_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    long_name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    code = models.CharField(max_length=100, blank=True, null=True, db_index=True, unique=True)
    slug = models.SlugField(max_length=100, blank=True, null=True, db_index=True, unique=True)
    supervised = models.BooleanField(default=False, help_text="Flag to enable/disable offices, which need manual check")

    extra_fields = models.JSONField(default=dict, blank=True, null=False)

    def __str__(self) -> str:
        return str(self.name)


class FinancialServiceProvider(TimeStampedModel):
    remote_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    name = models.CharField(max_length=64, unique=True)
    vendor_number = models.CharField(max_length=100, unique=True)
    strategy = StrategyField(registry=registry)
    configuration = models.JSONField(default=dict, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.name} [{self.vendor_number}]"


class FinancialServiceProviderConfig(models.Model):
    key = models.CharField(max_length=16, db_index=True)
    label = models.CharField(max_length=16, db_index=True, null=True, blank=True)
    fsp = models.ForeignKey(FinancialServiceProvider, on_delete=models.CASCADE, related_name="configs")
    delivery_mechanism = models.ForeignKey(DeliveryMechanism, on_delete=models.CASCADE, related_name="fsp")
    configuration = models.JSONField(default=dict, null=True, blank=True)
    required_fields = ArrayField(
        default=list,
        base_field=models.CharField(max_length=255),
        help_text="comma separated list of unique fields",
        blank=True,
        null=True,
    )

    class Meta:
        unique_together = ("key", "fsp", "delivery_mechanism")

    def __str__(self) -> str:
        if self.delivery_mechanism:
            return f"{self.fsp}/{self.delivery_mechanism} [{self.label}]"
        return f"{self.fsp} [{self.label}]"


class PaymentInstructionState(models.TextChoices):
    DRAFT = ("DRAFT", "Draft")
    OPEN = ("OPEN", "Open")
    CLOSED = ("CLOSED", "Closed")
    READY = ("READY", "Ready")
    PROCESSED = ("PROCESSED", "Processed")
    FINALIZED = ("FINALIZED", "Finalized")
    ABORTED = ("ABORTED", "Aborted")


class PaymentInstruction(TimeStampedModel):
    fsp = models.ForeignKey(FinancialServiceProvider, on_delete=models.CASCADE)
    system = models.ForeignKey(System, on_delete=models.CASCADE)
    external_code = models.CharField(max_length=255, db_index=True)
    remote_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    status = models.CharField(
        max_length=50,
        default=PaymentInstructionState.DRAFT,
        choices=PaymentInstructionState.choices,
        db_index=True,
    )
    office = models.ForeignKey(Office, on_delete=models.SET_NULL, null=True, blank=True)

    tag = models.CharField(null=True, blank=True)
    payload = models.JSONField(default=dict, null=True, blank=True)
    active = models.BooleanField(default=True)
    extra = models.JSONField(default=dict, null=True, blank=True)

    class Meta:
        unique_together = ("system", "remote_id")

    def __str__(self) -> str:
        return f"{self.external_code} - {self.status}"

    def get_payload(self) -> dict:
        payload = self.payload.copy()
        if "config_key" in self.extra:
            config_payload = self.fsp.strategy.get_configuration(
                self.extra["config_key"],
                self.extra.get("delivery_mechanism", "cash_over_the_counter"),  # temp fix
            )
            payload.update(self.extra)
            payload.update(config_payload)
        return payload


class PaymentRecordState(models.TextChoices):
    PENDING = ("PENDING", "Pending")
    TRANSFERRED_TO_FSP = ("TRANSFERRED_TO_FSP", "Transferred to FSP")
    TRANSFERRED_TO_BENEFICIARY = (
        "TRANSFERRED_TO_BENEFICIARY",
        "Transferred to Beneficiary",
    )
    CANCELLED = ("CANCELLED", "Cancelled")
    REFUND = ("REFUND", "Refund")
    PURGED = ("PURGED", "Purged")
    ERROR = ("ERROR", "Error")


class PaymentRecord(TimeStampedModel):
    parent = models.ForeignKey(PaymentInstruction, on_delete=models.CASCADE)
    remote_id = models.CharField(max_length=255, db_index=True, unique=True)  # HOPE UUID
    record_code = models.CharField(max_length=64, unique=True)  # Payment Record ID

    status = models.CharField(
        max_length=50,
        default=PaymentRecordState.PENDING,
        choices=PaymentRecordState.choices,
        db_index=True,
    )
    success = models.BooleanField(null=True, blank=True)
    message = models.CharField(max_length=4096, null=True, blank=True)

    auth_code = models.CharField(
        max_length=64,
        db_index=True,
        null=True,
        blank=True,
        help_text="MTCN for western union, reference number for MoneyGram",
    )

    fsp_code = models.CharField(
        max_length=64,
        db_index=True,
        null=True,
        blank=True,
        help_text="new MTCN for western union, transaction id for MoneyGram",
    )
    payload = models.JSONField(default=dict, null=True, blank=True)
    extra_data = models.JSONField(default=dict, null=True, blank=True)

    payout_amount = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)
    payout_date = models.DateField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.record_code} / {self.status}"

    def get_payload(self) -> dict:
        payload = self.parent.get_payload()
        payload.update(self.payload)
        payload["payment_record_code"] = self.record_code
        payload["remote_id"] = self.remote_id
        return payload


class ExportTemplate(models.Model):
    fsp = models.ForeignKey(FinancialServiceProvider, on_delete=models.CASCADE)
    delivery_mechanism = models.ForeignKey(DeliveryMechanism, on_delete=models.CASCADE, related_name="template")
    config_key = models.CharField(max_length=32)
    strategy = StrategyField(registry=export_registry)
    query = models.TextField()

    header = models.BooleanField(default=True)
    delimiter = models.CharField(choices=list(zip(delimiters, delimiters, strict=True)), default=",")
    quotechar = models.CharField(choices=list(zip(quotes, quotes, strict=True)), default="'")
    quoting = models.IntegerField(
        choices=(
            (csv.QUOTE_ALL, _("All")),
            (csv.QUOTE_MINIMAL, _("Minimal")),
            (csv.QUOTE_NONE, _("None")),
            (csv.QUOTE_NONNUMERIC, _("Non Numeric")),
        ),
        default=csv.QUOTE_ALL,
    )
    escapechar = models.CharField(choices=(("", ""), ("\\", "\\")), default="", null=True, blank=True)

    class Meta:
        unique_together = ("fsp", "config_key")
        permissions = (
            ("can_import_records", "Can Import Records"),
            ("can_export_records", "Can Export Records"),
        )

    def __str__(self) -> str:
        return f"{self.fsp} / {self.config_key}"


class AsyncJob(AsyncJobModel):
    instruction = models.ForeignKey(
        PaymentInstruction, related_name="jobs", on_delete=models.CASCADE, null=True, blank=True
    )
    celery_task_name = "hope_payment_gateway.apps.core.tasks.sync_job_task"

import csv

from django.db import models
from django.utils.translation import gettext_lazy as _

from adminactions.api import delimiters, quotes
from model_utils.models import TimeStampedModel
from strategy_field.fields import StrategyField

from hope_payment_gateway.apps.core.models import System
from hope_payment_gateway.apps.gateway.registry import export_registry, registry


class DeliveryMechanism(TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)

    def __str__(self):
        return f"{self.name} [{self.code}]"


class FinancialServiceProvider(TimeStampedModel):
    remote_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    name = models.CharField(max_length=64, unique=True)
    vision_vendor_number = models.CharField(max_length=100, unique=True)
    strategy = StrategyField(registry=registry)
    configuration = models.JSONField(default=dict, null=True, blank=True)

    def __str__(self):
        return f"{self.name} [{self.vision_vendor_number}]"


class FinancialServiceProviderConfig(models.Model):
    key = models.CharField(max_length=16, db_index=True)
    label = models.CharField(max_length=16, db_index=True, null=True, blank=True)
    fsp = models.ForeignKey(FinancialServiceProvider, on_delete=models.CASCADE, related_name="configs")
    delivery_mechanism = models.ForeignKey(DeliveryMechanism, on_delete=models.CASCADE, related_name="fsp")
    configuration = models.JSONField(default=dict, null=True, blank=True)

    def __str__(self):
        if self.delivery_mechanism:
            return f"{self.fsp}/{self.delivery_mechanism} [{self.label}]"
        else:
            return f"{self.fsp} [{self.label}]"

    class Meta:
        unique_together = ("key", "fsp", "delivery_mechanism")


class PaymentInstructionState(models.TextChoices):
    DRAFT = ("DRAFT", "Draft")
    OPEN = ("OPEN", "Open")
    CLOSED = ("CLOSED", "Closed")
    READY = ("READY", "Ready")
    PROCESSED = ("PROCESSED", "Processed")
    ABORTED = ("ABORTED", "Aborted")


class PaymentInstruction(TimeStampedModel):

    remote_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    unicef_id = models.CharField(max_length=255, db_index=True)
    status = models.CharField(
        max_length=50, default=PaymentInstructionState.DRAFT, choices=PaymentInstructionState.choices, db_index=True
    )

    payload = models.JSONField(default=dict, null=True, blank=True)

    fsp = models.ForeignKey(FinancialServiceProvider, on_delete=models.CASCADE)
    system = models.ForeignKey(System, on_delete=models.CASCADE)
    tag = models.CharField(null=True, blank=True)
    extra = models.JSONField(default=dict, null=True, blank=True)

    class Meta:
        unique_together = ("system", "remote_id")

    def __str__(self):
        return f"{self.unicef_id} - {self.status}"

    def get_payload(self):
        payload = self.payload.copy()
        if "config_key" in self.extra:
            config_payload = self.fsp.strategy.get_configuration(
                self.extra["config_key"], self.extra.get("delivery_mechanism", "cash_over_the_counter")  # temp fix
            )
            payload.update(config_payload)
        return payload


class PaymentRecordState(models.TextChoices):
    PENDING = ("PENDING", "Pending")
    TRANSFERRED_TO_FSP = ("TRANSFERRED_TO_FSP", "Transferred to FSP")
    TRANSFERRED_TO_BENEFICIARY = ("TRANSFERRED_TO_BENEFICIARY", "Transferred to Beneficiary")
    CANCELLED = ("CANCELLED", "Cancelled")
    REFUND = ("REFUND", "Refund")
    PURGED = ("PURGED", "Purged")
    ERROR = ("ERROR", "Error")


class PaymentRecord(TimeStampedModel):

    remote_id = models.CharField(max_length=255, db_index=True, unique=True)  # HOPE UUID
    parent = models.ForeignKey(PaymentInstruction, on_delete=models.CASCADE)
    record_code = models.CharField(max_length=64, unique=True)  # Payment Record ID
    fsp_code = models.CharField(max_length=64, db_index=True, null=True, blank=True)
    success = models.BooleanField(null=True, blank=True)
    status = models.CharField(
        max_length=50, default=PaymentRecordState.PENDING, choices=PaymentRecordState.choices, db_index=True
    )
    message = models.CharField(max_length=4096, null=True, blank=True)
    payload = models.JSONField(default=dict, null=True, blank=True)
    extra_data = models.JSONField(default=dict, null=True, blank=True)

    auth_code = models.CharField(max_length=64, db_index=True, null=True, blank=True)  # Western Union MTCN
    payout_amount = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)

    marked_for_payment = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.record_code} / {self.status}"

    def get_payload(self):
        payload = self.parent.get_payload()
        payload.update(self.payload)
        payload["payment_record_code"] = self.record_code
        payload["remote_id"] = self.remote_id
        return payload


class ExportTemplate(models.Model):
    query = models.TextField()
    fsp = models.ForeignKey(FinancialServiceProvider, on_delete=models.CASCADE)
    config_key = models.CharField(max_length=32)
    delivery_mechanism = models.ForeignKey(DeliveryMechanism, on_delete=models.CASCADE, related_name="template")
    strategy = StrategyField(registry=export_registry)

    header = models.BooleanField(default=True)
    delimiter = models.CharField(choices=list(zip(delimiters, delimiters)), default=",")
    quotechar = models.CharField(choices=list(zip(quotes, quotes)), default="'")
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

    def __str__(self):
        return f"{self.fsp} / {self.config_key}"

    class Meta:
        unique_together = ("fsp", "config_key")

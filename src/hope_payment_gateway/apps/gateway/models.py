import csv

from adminactions.api import delimiters, quotes
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import F
from django.utils.translation import gettext_lazy as _
from django_celery_boost.models import AsyncJobModel
from model_utils.models import TimeStampedModel
from strategy_field.fields import StrategyField

from hope_payment_gateway.apps.core.models import System
from hope_payment_gateway.apps.gateway.registry import export_registry, registry


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
    account_type = models.ForeignKey(
        AccountType,
        on_delete=models.CASCADE,
        related_name="delivery_mechanisms",
        null=True,
        blank=True,
    )
    transfer_type = models.CharField(choices=DELIVERY_MECHANISM_TYPE, max_length=32)

    def __str__(self) -> str:
        return f"{self.name} [{self.code}]"


class Office(TimeStampedModel):
    remote_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    long_name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    code = models.CharField(max_length=100, blank=True, null=True, db_index=True, unique=True)
    slug = models.SlugField(max_length=100, blank=True, null=True, db_index=True, unique=True)
    supervised = models.BooleanField(
        default=False,
        help_text="Flag to enable/disable offices, which need manual check",
    )

    extra_fields = models.JSONField(default=dict, blank=True, null=False)

    def __str__(self) -> str:
        return str(self.name)


class Country(TimeStampedModel):
    name = models.CharField(max_length=255, db_index=True)
    short_name = models.CharField(max_length=255, db_index=True)
    iso_code2 = models.CharField(max_length=2, unique=True)
    iso_code3 = models.CharField(max_length=3, unique=True)
    iso_num = models.CharField(max_length=4, unique=True)

    def __str__(self) -> str:
        return f"{self.name}"


class FinancialServiceProvider(TimeStampedModel):
    remote_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    name = models.CharField(max_length=64, unique=True)
    vendor_number = models.CharField(max_length=100, unique=True)
    strategy = StrategyField(registry=registry)
    configuration = models.JSONField(default=dict, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.name} [{self.vendor_number}]"


class FinancialServiceProviderConfig(models.Model):
    label = models.CharField(max_length=64, db_index=True, null=True, blank=True)
    key = models.CharField(max_length=16, db_index=True)
    delivery_mechanism = models.ForeignKey(DeliveryMechanism, on_delete=models.CASCADE, related_name="fsp")
    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name="configs", null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="configs", null=True, blank=True)
    fsp = models.ForeignKey(FinancialServiceProvider, on_delete=models.CASCADE, related_name="configs")
    required_fields = ArrayField(
        default=list,
        base_field=models.CharField(max_length=255),
        help_text="comma separated list of unique fields",
        blank=True,
        null=True,
    )
    configuration = models.JSONField(default=dict, null=True, blank=True)

    class Meta:
        unique_together = ("country", "fsp", "delivery_mechanism")

    def __str__(self) -> str:
        if self.delivery_mechanism:
            return f"{self.fsp}/{self.delivery_mechanism} [{self.label}]"
        return f"{self.fsp} [{self.label}]"


class ExportTemplate(models.Model):
    fsp = models.ForeignKey(FinancialServiceProvider, on_delete=models.PROTECT)
    delivery_mechanism = models.ForeignKey(DeliveryMechanism, on_delete=models.PROTECT, related_name="template")
    office = models.ForeignKey(Office, on_delete=models.PROTECT, related_name="template", null=True, blank=True)
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="template",
        null=True,
        blank=True,
    )
    config_key = models.CharField(max_length=32)
    strategy = StrategyField(registry=export_registry, null=True, blank=True)
    query = models.TextField()

    header = models.BooleanField(default=True)
    delimiter = models.CharField(
        choices=list(zip(delimiters, delimiters, strict=True)),
        default=",",
        max_length=1,
    )
    quotechar = models.CharField(choices=list(zip(quotes, quotes, strict=True)), default="'", max_length=1)
    quoting = models.IntegerField(
        choices=(
            (csv.QUOTE_ALL, _("All")),
            (csv.QUOTE_MINIMAL, _("Minimal")),
            (csv.QUOTE_NONE, _("None")),
            (csv.QUOTE_NONNUMERIC, _("Non Numeric")),
        ),
        default=csv.QUOTE_ALL,
    )
    escapechar = models.CharField(
        choices=(("", ""), ("\\", "\\")),
        default="",
        null=True,
        blank=True,
        max_length=1,
    )

    class Meta:
        unique_together = ("fsp", "config_key")
        permissions = (
            ("can_import_records", "Can Import Records"),
            ("can_export_records", "Can Export Records"),
        )

    def __str__(self) -> str:
        return f"{self.fsp} / {self.config_key}"


class PaymentInstructionState(models.TextChoices):
    DRAFT = ("DRAFT", "Draft")
    OPEN = ("OPEN", "Open")
    CLOSED = ("CLOSED", "Closed")
    READY = ("READY", "Ready")
    PROCESSED = ("PROCESSED", "Processed")
    FINALIZED = ("FINALIZED", "Finalized")
    ABORTED = ("ABORTED", "Aborted")


class PaymentInstruction(TimeStampedModel):
    fsp = models.ForeignKey(FinancialServiceProvider, on_delete=models.PROTECT)
    delivery_mechanism = models.ForeignKey(DeliveryMechanism, on_delete=models.PROTECT, null=True, blank=True)
    office = models.ForeignKey(Office, on_delete=models.SET_NULL, null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    export = models.ForeignKey(
        ExportTemplate,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="this is intent to be used only to force a template for a payment instruction",
    )
    system = models.ForeignKey(System, on_delete=models.CASCADE)
    external_code = models.CharField(max_length=255, db_index=True)
    remote_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    status = models.CharField(
        max_length=50,
        default=PaymentInstructionState.DRAFT,
        choices=PaymentInstructionState,
        db_index=True,
    )

    tag = models.CharField(null=True, blank=True, max_length=128)
    payload = models.JSONField(default=dict, null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("system", "remote_id")

    def __str__(self) -> str:
        return f"{self.external_code} - {self.status}"

    def get_payload(self) -> dict:
        payload = self.payload.copy()
        if self.delivery_mechanism:
            payload["delivery_mechanism"] = self.delivery_mechanism.code
        payload["destination_country"] = (
            self.country.iso_code2 if self.country else self.payload.get("destination_country_iso_code2", None)
        )
        destination_country = self.country.iso_code2 if self.country else self.payload.get("destination_country", None)
        if destination_country:
            config_payload = self.fsp.strategy.get_configuration(
                destination_country,
                self.payload.get("delivery_mechanism", "cash_over_the_counter"),
            )
            payload.update(config_payload)
        return payload

    @property
    def configuration(self):
        return (
            FinancialServiceProviderConfig.objects.filter(
                delivery_mechanism=self.delivery_mechanism,
                fsp=self.fsp,
                office=self.office,
                country=self.country,
            )
            .order_by(F("office").asc(nulls_last=True))
            .first()
        )

    @property
    def selected_export(self):
        if self.export:
            return self.export
        return (
            ExportTemplate.objects.filter(
                fsp=self.fsp,
                delivery_mechanism=self.delivery_mechanism,
                office=self.office,
                country=self.country,
            )
            .order_by(F("office").asc(nulls_last=True))
            .first()
        )


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
    parent = models.ForeignKey(PaymentInstruction, on_delete=models.CASCADE, related_name="records")
    remote_id = models.CharField(max_length=255, db_index=True, unique=True, help_text="Remote system ID")
    record_code = models.CharField(max_length=64, db_index=True, unique=True, help_text="Payment record code")

    status = models.CharField(
        max_length=50,
        default=PaymentRecordState.PENDING,
        choices=PaymentRecordState,
        db_index=True,
    )
    success = models.BooleanField(null=True, blank=True)
    message = models.CharField(
        max_length=4096,
        null=True,
        blank=True,
        help_text="Help Text message from latest FSP call",
    )

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

    payout_amount = models.DecimalField(
        decimal_places=2,
        max_digits=12,
        null=True,
        blank=True,
        help_text="Amount paid by FSP",
    )
    payout_date = models.DateField(null=True, blank=True, help_text="Date of payout from FSP")

    fsp_data = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        help_text="FSP data stored for troubleshooting",
    )
    extra_data = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        help_text="Useful information related original record",
    )

    def __str__(self) -> str:
        return f"{self.record_code} / {self.status}"

    def get_payload(self) -> dict:
        payload = self.parent.get_payload()
        payload.update(self.payload)
        payload["payment_record_code"] = self.record_code
        payload["remote_id"] = self.remote_id
        return payload

    def add_push_notification(self, payload):
        if self.fsp_data is None:
            self.fsp_data = {}
        if "push_notification" not in self.fsp_data:
            self.fsp_data["push_notification"] = []
        self.fsp_data["push_notification"].append(payload)


class AsyncJob(AsyncJobModel):
    instruction = models.ForeignKey(
        PaymentInstruction,
        related_name="jobs",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    celery_task_name = "hope_payment_gateway.apps.core.tasks.sync_job_task"

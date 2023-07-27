from django.db import models
from django.utils.translation import gettext_lazy as _


class ReadOnlyModelException(BaseException):
    pass


class ReadOnlyModel(models.Model):
    def save(self, *args, **kwargs):
        raise ReadOnlyModelException

    def delete(self, *args, **kwargs):
        raise ReadOnlyModelException

    class Meta:
        abstract = True


class LimitedUpdateModel(models.Model):
    def save(self, *args, **kwargs) -> None:
        kwargs["update_fields"] = self.CustomMeta.updatable_fields
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ReadOnlyModelException

    class Meta:
        abstract = True


class BusinessArea(ReadOnlyModel):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
    )
    slug = models.CharField(
        max_length=250,
        unique=True,
        db_index=True,
    )
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = "core_businessarea"


class Programme(ReadOnlyModel):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
    )
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    FINISHED = "FINISHED"
    STATUS_CHOICE = (
        (ACTIVE, _("Active")),
        (DRAFT, _("Draft")),
        (FINISHED, _("Finished")),
    )
    business_area = models.ForeignKey(BusinessArea, on_delete=models.CASCADE)
    name = models.CharField(
        max_length=255,
        db_index=True,
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICE, db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)

    class Meta:
        managed = False
        db_table = "program_program"


class ProgrammeCycle(ReadOnlyModel):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
    )
    program = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name="cycles")
    iteration = models.PositiveIntegerField()
    status = models.CharField(max_length=10)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.CharField(blank=True, max_length=255)

    class Meta:
        managed = False
        db_table = "program_programcycle"


class PaymentPlan(ReadOnlyModel):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
    )
    unicef_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    business_area = models.ForeignKey(BusinessArea, on_delete=models.CASCADE)
    program = models.ForeignKey(Programme, on_delete=models.CASCADE)
    program_cycle = models.ForeignKey(ProgrammeCycle, null=True, blank=True, on_delete=models.CASCADE)

    status = models.TextField()
    dispersion_start_date = models.DateField()
    dispersion_end_date = models.DateField()
    start_date = models.DateTimeField(db_index=True)
    end_date = models.DateTimeField(db_index=True)
    total_entitled_quantity = models.DecimalField(
        decimal_places=2,
        max_digits=12,
        db_index=True,
        null=True,
    )
    total_entitled_quantity_usd = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)

    is_follow_up = models.BooleanField(default=False)
    total_delivered_quantity = models.DecimalField(
        decimal_places=2,
        max_digits=12,
        db_index=True,
        null=True,
        blank=True,
    )
    total_delivered_quantity_usd = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)
    total_undelivered_quantity = models.DecimalField(
        decimal_places=2,
        max_digits=12,
        db_index=True,
        null=True,
        blank=True,
    )
    total_undelivered_quantity_usd = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)

    class Status(models.TextChoices):
        PREPARING = "PREPARING", "Preparing"
        OPEN = "OPEN", "Open"
        LOCKED = "LOCKED", "Locked"
        LOCKED_FSP = "LOCKED_FSP", "Locked FSP"
        IN_APPROVAL = "IN_APPROVAL", "In Approval"
        IN_AUTHORIZATION = "IN_AUTHORIZATION", "In Authorization"
        IN_REVIEW = "IN_REVIEW", "In Review"
        ACCEPTED = "ACCEPTED", "Accepted"
        FINISHED = "FINISHED", "Finished"

    # currency = models.TextField()
    class Meta:
        managed = False
        db_table = "payment_paymentplan"


class FinancialServiceProvider(ReadOnlyModel):
    COMMUNICATION_CHANNEL_API = "API"
    COMMUNICATION_CHANNEL_SFTP = "SFTP"
    COMMUNICATION_CHANNEL_XLSX = "XLSX"
    COMMUNICATION_CHANNEL_CHOICES = (
        (COMMUNICATION_CHANNEL_API, "API"),
        (COMMUNICATION_CHANNEL_SFTP, "SFTP"),
        (COMMUNICATION_CHANNEL_XLSX, "XLSX"),
    )
    id = models.UUIDField(
        primary_key=True,
        editable=False,
    )
    name = models.CharField(max_length=100, unique=True)
    communication_channel = models.CharField(max_length=6, choices=COMMUNICATION_CHANNEL_CHOICES, db_index=True)

    class Meta:
        managed = False
        db_table = "payment_financialserviceprovider"


class PaymentRecord(LimitedUpdateModel):
    STATUS_SUCCESS = "Transaction Successful"
    STATUS_ERROR = "Transaction Erroneous"
    STATUS_DISTRIBUTION_SUCCESS = "Distribution Successful"
    STATUS_NOT_DISTRIBUTED = "Not Distributed"
    STATUS_FORCE_FAILED = "Force failed"
    STATUS_DISTRIBUTION_PARTIAL = "Partially Distributed"
    STATUS_PENDING = "Pending"

    # WESTERN UNION STATUSES
    STATUS_VALIDATION_OK = "Validation OK"
    STATUS_VALIDATION_KO = "Validation KO"
    STATUS_STORE_OK = "Store OK"
    STATUS_STORE_KO = "Store KO"

    STATUS_CHOICE = (
        (STATUS_DISTRIBUTION_SUCCESS, _("Distribution Successful")),
        (STATUS_NOT_DISTRIBUTED, _("Not Distributed")),
        (STATUS_SUCCESS, _("Transaction Successful")),
        (STATUS_ERROR, _("Transaction Erroneous")),
        (STATUS_FORCE_FAILED, _("Force failed")),
        (STATUS_DISTRIBUTION_PARTIAL, _("Partially Distributed")),
        (STATUS_PENDING, _("Pending")),
        (STATUS_VALIDATION_OK, _("Validation OK")),
        (STATUS_VALIDATION_KO, _("Validation KO")),
        (STATUS_STORE_OK, _("Store OK")),
        (STATUS_STORE_KO, _("Store KO")),
    )
    unicef_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    id = models.UUIDField(
        primary_key=True,
        editable=False,
    )
    parent = models.ForeignKey(
        PaymentPlan,
        on_delete=models.CASCADE,
        related_name="payment_items",
    )
    program = models.ForeignKey(Programme, on_delete=models.SET_NULL, null=True, blank=True)
    business_area = models.ForeignKey(BusinessArea, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=255,
        choices=STATUS_CHOICE,
        default=STATUS_PENDING,
    )
    currency = models.CharField(
        max_length=4,
    )

    conflicted = models.BooleanField(default=False)
    excluded = models.BooleanField(default=False)
    entitlement_date = models.DateTimeField(null=True, blank=True)
    is_follow_up = models.BooleanField(default=False)

    financial_service_provider = models.ForeignKey(FinancialServiceProvider, on_delete=models.PROTECT, null=True)

    delivery_type = models.CharField(max_length=24, null=True)

    entitlement_quantity = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)
    entitlement_quantity_usd = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)
    delivered_quantity = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)
    delivered_quantity_usd = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)
    delivery_date = models.DateTimeField(null=True, blank=True)
    transaction_reference_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "payment_payment"

    class CustomMeta:
        updatable_fields = [
            "status",
            "delivered_quantity",
            "delivered_quantity_usd",
            "delivery_date",
            "transaction_reference_id",
        ]


class PaymentHouseholdSnapshot(ReadOnlyModel):
    snapshot_data = models.JSONField(default=dict)
    household_id = models.UUIDField()
    payment = models.OneToOneField(PaymentRecord, on_delete=models.CASCADE, related_name="household_snapshot")

    class Meta:
        managed = False
        db_table = "payment_paymenthouseholdsnapshot"

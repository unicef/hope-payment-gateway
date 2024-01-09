from django.db import models

from django_fsm import FSMField, transition
from model_utils.models import TimeStampedModel
from strategy_field.fields import StrategyField

from hope_payment_gateway.apps.core.models import System
from hope_payment_gateway.apps.gateway.registry import registry


class FinancialServiceProvider(models.Model):
    remote_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    name = models.CharField(max_length=64, unique=True)
    vision_vendor_number = models.CharField(max_length=100)
    strategy = StrategyField(registry=registry)
    configuration = models.JSONField(default=dict, null=True, blank=True)

    def __str__(self):
        return f"{self.name} [{self.vision_vendor_number}]"


class PaymentInstruction(TimeStampedModel):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    READY = "READY"
    CLOSED = "CLOSED"
    ABORTED = "ABORTED"
    PROCESSED = "PROCESSED"

    STATUSES = (
        (DRAFT, "Draft"),
        (OPEN, "Open"),
        (CLOSED, "Closed"),
        (READY, "Ready"),
        (PROCESSED, "Processed"),
        (ABORTED, "Aborted"),
    )
    remote_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    unicef_id = models.CharField(max_length=255, db_index=True)
    status = FSMField(default=DRAFT, protected=False, db_index=True, choices=STATUSES)
    payload = models.JSONField(default=dict, null=True, blank=True)

    fsp = models.ForeignKey(FinancialServiceProvider, on_delete=models.CASCADE)
    system = models.ForeignKey(System, on_delete=models.CASCADE)
    tag = models.CharField(null=True, blank=True)

    def __str__(self):
        return f"{self.unicef_id} - {self.status}"

    @transition(field=status, source=DRAFT, target=OPEN, permission="western_union.change_paymentinstruction")
    def open(self):
        pass

    @transition(field=status, source=OPEN, target=CLOSED, permission="western_union.change_paymentinstruction")
    def close(self):
        pass

    @transition(field=status, source=CLOSED, target=READY, permission="western_union.change_paymentinstruction")
    def ready(self):
        pass

    @transition(field=status, source=READY, target=PROCESSED, permission="western_union.change_paymentinstruction")
    def process(self):
        pass

    @transition(field=status, source="*", target=ABORTED, permission="western_union.change_paymentinstruction")
    def abort(self):
        pass

    def get_payload(self):
        payload = self.payload.copy()
        if self.fsp:
            payload.update(self.fsp.configuration)
        return payload


class PaymentRecord(TimeStampedModel):
    PENDING = "PENDING"
    TRANSFERRED_TO_FSP = "TRANSFERRED_TO_FSP"
    TRANSFERRED_TO_BENEFICIARY = "TRANSFERRED_TO_BENEFICIARY"
    CANCELLED = "CANCELLED"
    REFUND = "REFUND"
    PURGED = "PURGED"
    ERROR = "ERROR"

    STATUSES = (
        (PENDING, "Pending"),
        (TRANSFERRED_TO_FSP, "Transferred to FSP"),
        (TRANSFERRED_TO_BENEFICIARY, "Transferred to Beneficiary"),
        (CANCELLED, "Cancelled"),
        (REFUND, "Refund"),
        (PURGED, "Purged"),
        (ERROR, "Error"),
    )

    remote_id = models.CharField(max_length=255, db_index=True, unique=True)
    parent = models.ForeignKey(PaymentInstruction, on_delete=models.CASCADE)
    record_code = models.CharField(max_length=64)
    success = models.BooleanField(null=True, blank=True)
    status = FSMField(default=PENDING, protected=False, db_index=True, choices=STATUSES)
    message = models.CharField(max_length=4096, null=True, blank=True)
    payload = models.JSONField(default=dict, null=True, blank=True)
    extra_data = models.JSONField(default=dict, null=True, blank=True)

    def __str__(self):
        return f"{self.record_code} / {self.status}"

    def get_payload(self):
        payload = self.parent.get_payload()
        payload.update(self.payload)
        payload["payment_record_code"] = self.record_code
        payload["remote_id"] = self.remote_id
        return payload

    @transition(
        field=status,
        source=PENDING,
        target=TRANSFERRED_TO_FSP,
        permission="western_union.change_paymentrecordlog",
    )
    def store(self):
        pass

    @transition(
        field=status,
        source=TRANSFERRED_TO_FSP,
        target=TRANSFERRED_TO_BENEFICIARY,
        permission="western_union.change_paymentrecordlog",
    )
    def confirm(self):
        pass

    @transition(
        field=status,
        source=TRANSFERRED_TO_FSP,
        target=PURGED,
        permission="western_union.change_paymentrecordlog",
    )
    def purge(self):
        pass

    @transition(
        field=status,
        source=TRANSFERRED_TO_FSP,
        target=REFUND,
        permission="western_union.change_paymentrecordlog",
    )
    def refund(self):
        pass

    @transition(field=status, source="*", target=CANCELLED, permission="western_union.change_paymentrecordlog")
    def cancel(self):
        pass

    @transition(field=status, source="*", target=ERROR, permission="western_union.change_paymentrecordlog")
    def fail(self):
        pass

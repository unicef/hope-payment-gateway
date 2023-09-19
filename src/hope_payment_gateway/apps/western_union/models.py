import uuid

from django.db import models

from django_fsm import FSMField, transition
from model_utils.models import TimeStampedModel


class Corridor(models.Model):  # delivery mechanism
    description = models.CharField(max_length=1024)
    destination_country = models.CharField(max_length=2)
    destination_currency = models.CharField(max_length=3)
    template_code = models.CharField(max_length=4)
    template = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.description} / {self.template_code}"

    # example_dict = {
    #     "wallet_details": {
    #         "service_provider_code": ["06301", "06302", "06304"]
    #     },
    #     "receiver": {
    #         "mobile_phone": {
    #             "phone_number": {
    #                 "country_code": 63,
    #                 "national_number": None
    #             }
    #         },
    #         "reason_for_sending": ["P012", "P020", "P014"]
    #     }
    # }


class PaymentInstruction(TimeStampedModel):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

    STATUSES = (
        (DRAFT, "Draft"),
        (OPEN, "Open"),
        (CLOSED, "Closed"),
        (CANCELLED, "Cancelled"),
    )
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    unicef_id = models.CharField(max_length=255, db_index=True)
    status = FSMField(default=DRAFT, protected=False, db_index=True, choices=STATUSES)
    payload = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.unicef_id} - {self.status}"

    @transition(field=status, source=DRAFT, target=OPEN, permission="western_union.change_paymentinstruction")
    def open(self):
        pass

    @transition(field=status, source=OPEN, target=CLOSED, permission="western_union.change_paymentinstruction")
    def close(self):
        pass

    @transition(field=status, source="*", target=CANCELLED, permission="western_union.change_paymentinstruction")
    def cancel(self):
        pass


class PaymentRecordLog(TimeStampedModel):
    PENDING = "PENDING"
    VALIDATION_OK = "VALIDATION_OK"
    TRANSFERRED_TO_FSP = "TRANSFERRED_TO_FSP"
    TRANSFERRED_TO_BENEFICIARY = "TRANSFERRED_TO_BENEFICIARY"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"

    STATUSES = (
        (PENDING, "Pending"),
        (VALIDATION_OK, "Validation OK"),
        (TRANSFERRED_TO_FSP, "Transferred to FSP"),
        (TRANSFERRED_TO_BENEFICIARY, "Transferred to Beneficiary"),
        (CANCELLED, "Cancelled"),
        (ERROR, "Error"),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    parent = models.ForeignKey(PaymentInstruction, on_delete=models.CASCADE)
    record_code = models.CharField(max_length=64)
    success = models.BooleanField(null=True, blank=True)
    status = FSMField(default=PENDING, protected=False, db_index=True, choices=STATUSES)
    message = models.CharField(max_length=1024, null=True, blank=True)
    payload = models.JSONField(default=dict)
    extra_data = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.record_code} / {self.message}"

    def get_payload(self):
        payload = self.parent.payload.copy()
        payload.update(self.payload)
        payload["payment_record_code"] = self.record_code
        payload["record_uuid"] = self.uuid
        return payload

    @transition(field=status, source=PENDING, target=VALIDATION_OK, permission="western_union.change_paymentrecordlog")
    def validate(self):
        pass

    @transition(
        field=status,
        source=VALIDATION_OK,
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
        field=status, source=TRANSFERRED_TO_FSP, target=CANCELLED, permission="western_union.change_paymentrecordlog"
    )
    def cancel(self):
        pass

    @transition(field=status, source="*", target=ERROR, permission="western_union.change_paymentrecordlog")
    def fail(self):
        pass

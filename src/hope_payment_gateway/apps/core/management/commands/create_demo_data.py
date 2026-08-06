import uuid

from django.conf import settings
from django.core.management import BaseCommand

from hope_payment_gateway.apps.core.models import System, User
from hope_payment_gateway.apps.gateway.models import (
    DeliveryMechanism,
    FinancialServiceProvider,
    PaymentInstruction,
    PaymentInstructionState,
    PaymentRecord,
    PaymentRecordState,
)
from hope_payment_gateway.apps.gateway.registry import DefaultProcessor
from strategy_field.utils import fqn


class Command(BaseCommand):
    help = "Create demo FSP, PaymentInstruction, and PaymentRecords for local testing"

    def handle(self, *args, **options):
        echo = self.stdout.write

        if not settings.DEBUG:
            echo("Demo data can only be populated when in debug mode")
            return

        owner, _ = User.objects.get_or_create(
            username="demo-user",
            defaults={"email": "demo@example.com", "is_staff": True},
        )

        system, created = System.objects.get_or_create(name="demo-system", defaults={"owner": owner})
        echo(f"{'Created' if created else 'Found'} System: {system}")

        dm, created = DeliveryMechanism.objects.get_or_create(
            code="cash_over_the_counter",
            defaults={"name": "Cash Over The Counter"},
        )
        echo(f"{'Created' if created else 'Found'} DeliveryMechanism: {dm}")

        fsp, created = FinancialServiceProvider.objects.get_or_create(
            name="Demo FSP",
            defaults={
                "remote_id": "demo-fsp-001",
                "vendor_number": "DEMO-001",
                "strategy": fqn(DefaultProcessor),
            },
        )
        echo(f"{'Created' if created else 'Found'} FSP: {fsp}")

        instruction, created = PaymentInstruction.objects.get_or_create(
            system=system,
            remote_id="DEMO-PI-001",
            defaults={
                "fsp": fsp,
                "delivery_mechanism": dm,
                "external_code": "DEMO-PI-001",
                "status": PaymentInstructionState.OPEN,
            },
        )
        echo(f"{'Created' if created else 'Found'} PaymentInstruction: {instruction}")

        for i in range(1, 4):
            record_code = f"DEMO-PR-00{i}"
            record, created = PaymentRecord.objects.get_or_create(
                record_code=record_code,
                defaults={
                    "remote_id": f"demo-remote-{i}-{uuid.uuid4().hex[:8]}",
                    "parent": instruction,
                    "status": PaymentRecordState.PENDING,
                },
            )
            echo(f"  {'Created' if created else 'Found'} PaymentRecord: {record}")

        echo(self.style.SUCCESS("\nDemo data ready."))

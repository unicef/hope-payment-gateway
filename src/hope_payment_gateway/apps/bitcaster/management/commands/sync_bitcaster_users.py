from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from hope_payment_gateway.apps.bitcaster.client import get_hope_bitcaster_client


class Command(BaseCommand):
    help = "Sync all Hope users to Bitcaster as application members"

    def handle(self, *args: object, **options: object) -> None:
        client = get_hope_bitcaster_client()
        if client is None:
            self.stdout.write(self.style.WARNING("Bitcaster is not enabled or configured — skipping sync"))
            return
        user_model = get_user_model()
        count = 0
        for user in user_model.objects.iterator():
            client.register_user(user)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Synced {count} users to Bitcaster"))

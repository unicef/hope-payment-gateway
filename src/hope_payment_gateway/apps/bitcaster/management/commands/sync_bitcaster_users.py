from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from hope_payment_gateway.apps.bitcaster.tasks import sync_user_to_bitcaster


class Command(BaseCommand):
    help = "Sync all Hope users to Bitcaster as application members"

    def handle(self, *args: object, **options: object) -> None:
        user_model = get_user_model()
        qs = user_model.objects.all()
        count = qs.count()
        for user in qs.iterator():
            sync_user_to_bitcaster.delay(user.pk)
        self.stdout.write(self.style.SUCCESS(f"Queued {count} users for Bitcaster sync"))

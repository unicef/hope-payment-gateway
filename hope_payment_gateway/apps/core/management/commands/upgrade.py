import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = ""

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            dest="all",
            default=False,
            help="select all options but `demo`",
        )

        parser.add_argument(
            "--collectstatic",
            action="store_true",
            dest="collectstatic",
            default=False,
            help="",
        )

        parser.add_argument("--users", action="store_true", dest="users", default=False, help="")

        parser.add_argument(
            "--migrate",
            action="store_true",
            dest="migrate",
            default=False,
            help="select all production deployment options",
        )

    def handle(self, *args, **options):
        verbosity = options["verbosity"]
        migrate = options["migrate"]
        _all = options["all"]
        ModelUser = get_user_model()
        if options["collectstatic"] or _all:
            self.stdout.write("Run collectstatic")
            call_command("collectstatic", verbosity=verbosity - 1, interactive=False)

        if migrate or _all:
            self.stdout.write("Run migrations")
            call_command("migrate", verbosity=verbosity - 1)

        if options["users"] or _all:
            call_command("update_notifications", verbosity=verbosity - 1)
            if settings.DEBUG:
                pwd = "123"
                admin = os.environ.get("USER", "admin")
            else:
                pwd = os.environ.get("ADMIN_PASSWORD", ModelUser.objects.make_random_password())
                admin = os.environ.get("ADMIN_USERNAME", "admin")

            _, created = ModelUser.objects.get_or_create(
                username=admin,
                defaults={
                    "is_superuser": True,
                    "is_staff": True,
                    "password": make_password(pwd),
                },
            )

            if created:  # pragma: no cover
                self.stdout.write(f"Created superuser `{admin}` with password `{pwd}`")
            else:  # pragma: no cover
                self.stdout.write(f"Superuser `{admin}` already exists`.")

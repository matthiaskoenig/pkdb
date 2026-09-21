"""Management command that creates a superuser with a password and a verified email."""

from django.contrib.auth.management.commands import createsuperuser
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import CommandError
from rest_email_auth.models import EmailAddress


class Command(createsuperuser.Command):
    """Extend the built-in createsuperuser command with a password argument."""

    help = "Create a superuser, and allow password to be provided"

    def add_arguments(self, parser):
        """Add the --password argument on top of the base command's arguments."""
        super().add_arguments(parser)
        parser.add_argument(
            "--password",
            dest="password",
            default=None,
            help="Specifies the password for the superuser.",
        )

    def handle(self, *args, **options):
        """Create the superuser with the given password and a verified email.

        The superuser is created only when it does not exist yet.
        """
        password = options.get("password")
        username = options.get("username")
        email = options.get("email")
        database = options.get("database")

        if not username:
            raise CommandError("--username is required.")
        if not password:
            raise CommandError("--password is required.")
        if not email:
            raise CommandError("--email is required.")

        # only create admin if not existing
        try:
            user = self.UserModel._default_manager.db_manager(database).get(
                username=username
            )
        except ObjectDoesNotExist:
            super().handle(*args, **options)
            if password:
                user = self.UserModel._default_manager.db_manager(database).get(
                    username=username
                )
                user.set_password(password)
                user.save()
                email_dict = {
                    "email": email,
                    "is_primary": True,
                    "is_verified": True,
                    "user": user,
                }
                email = EmailAddress.objects.create(**email_dict)

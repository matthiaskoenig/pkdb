from django.contrib.auth.management.commands import createsuperuser
from django.core.management import CommandError
from django.core.exceptions import ObjectDoesNotExist
from rest_email_auth.models import EmailAddress


class Command(createsuperuser.Command):
    help = 'Create a superuser, and allow password to be provided'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--password', dest='password', default=None,
            help='Specifies the password for the superuser.',
        )

    def handle(self, *args, **options):
        password = options.get('password')
        username = options.get('username')
        email = options.get('email')
        database = options.get('database')

        if not username:
            raise CommandError("--username is required.")
        if not password:
            raise CommandError("--password is required.")
        if not email:
            raise CommandError("--email is required.")

        # only create admin if not existing
        try:
            user = self.UserModel._default_manager.db_manager(database).get(username=username)
        except ObjectDoesNotExist:
            super(Command, self).handle(*args, **options)
            if password:
                user = self.UserModel._default_manager.db_manager(database).get(username=username)
                user.set_password(password)
                user.save()
                email_dict = {"email": email, "is_primary": True, "is_verified": True, "user": user}
                email = EmailAddress.objects.create(**email_dict)

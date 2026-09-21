"""Management command that updates or inserts an allauth social provider entry.

See: https://django-allauth.readthedocs.io/en/latest/providers.html#github

# manage.py set_auth_provider google google GOOGLE_CLIENT_ID GOOGLE_SECRET_ID
python manage.py set_auth_provider github github $GITHUB_CLIENT_ID $GITHUB_SECRET_ID
docker compose run web python manage.py set_auth_provider github $GITHUB_CLIENT_ID $GITHUB_SECRET_ID

"""

from allauth.socialaccount.models import (  # ty: ignore[unresolved-import]  # known defect, reported: django-allauth is not a dependency
    SocialApp,
)
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand

from pkdb_app.settings import (
    SITE_ID,  # ty: ignore[unresolved-import]  # known defect, reported: settings defines no SITE_ID
)


class Command(BaseCommand):
    """Update or insert a specific allauth provider entry like Google or Facebook."""

    help = "Update or insert a specific allauth provider entry like Google or Facebook"

    def add_arguments(self, parser):
        """Add the provider, name, client_id and client_secret arguments."""
        parser.add_argument("provider", type=str, help="Provider ID like 'google'")
        parser.add_argument(
            "--name",
            default=None,
            type=str,
            help="Display name like 'Google' (optional)",
        )
        parser.add_argument(
            "client_id", type=str, help="Client ID from provider (==Facebook App ID)"
        )
        parser.add_argument(
            "client_secret",
            type=str,
            help="Secret from provider (==Facebook App Secret)",
        )

    def handle(self, *args, **options):
        """Replace the SocialApp entry of the provider.

        The entry is associated with the configured site.
        """
        provider = options["provider"]
        name = options.get("name") or provider.title()
        client_id = options["client_id"]
        client_secret = options["client_secret"]

        # Delete the specific provider if it exists.
        # Note that QuerySet.update_or_create is an alternative.
        SocialApp.objects.filter(provider=provider).delete()
        a = SocialApp(
            provider=provider,
            name=name,
            secret=client_secret,
            client_id=client_id,
            key="",
        )
        a.save()

        # Now associate this provider with all site instances.
        site = Site.objects.get(pk=SITE_ID)
        site.domain = "pk-db.com"
        site.name = "pk-db.com"
        site.save()
        a.sites.add(site)

        self.stdout.write(
            self.style.SUCCESS(f"Provider '{a.name}' -> client ID '{a.client_id}'")
        )
        self.stdout.write(self.style.SUCCESS(f"Associated with site: {site}"))

"""The PK-DB user model and its authentication token creation signal."""

import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token


class User(AbstractUser):
    """PK-DB user, identified by a UUID instead of the default auto-incrementing id."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    def __str__(self):
        """Return the username."""
        return self.username


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """Create a REST framework auth token for every newly created user."""
    if created:
        Token.objects.create(user=instance)


PUBLIC = "public"
PRIVATE = "private"

from django.db import models
from .utils import CHAR_MAX_LENGTH


class Sidable(models.Model):
    sid = models.CharField(max_length=CHAR_MAX_LENGTH, unique=True)

    class Meta:
        abstract = True


class Commentable(models.Model):
    comment = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True


class Describable(models.Model):
    description = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True

class Hashable(models.Model):
    hash = models.CharField(max_length=CHAR_MAX_LENGTH,blank=True, null=True)

    class Meta:
        abstract = True
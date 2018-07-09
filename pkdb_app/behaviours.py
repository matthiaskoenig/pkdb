"""
Reusable behavior for models.
"""

from django.db import models
from pkdb_app.utils import CHAR_MAX_LENGTH
from .categoricals import UNITS_CHOICES


class Sidable(models.Model):
    """ Model has an sid. """
    sid = models.CharField(max_length=CHAR_MAX_LENGTH)

    class Meta:
        abstract = True


# FIXME: This has to be more complicated.
'''
- multiple users can comment and every comment should be tracked to user with provenance information like
  timestamp (last modified)

    Comment(model):
       text
       user
       timestamp

- Annotation (annotatable), at some point, but not now
'''



class Commentable(models.Model):
    """ Model has a comment field. """
    comment = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True


class Describable(models.Model):
    """

    """
    description = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True

class Hashable(models.Model):
    hash = models.CharField(max_length=CHAR_MAX_LENGTH,blank=True, null=True)

    class Meta:
        abstract = True


class Values(models.Model):

    choice = models.CharField(max_length=CHAR_MAX_LENGTH, null=True,
                              blank=True)  # check in validation that allowed choice

    count = models.IntegerField()  # how many participants in characteristics
    value = models.FloatField(null=True, blank=True)

    mean = models.FloatField(null=True, blank=True)
    median = models.FloatField(null=True, blank=True)
    min = models.FloatField(null=True, blank=True)
    max = models.FloatField(null=True, blank=True)
    sd = models.FloatField(null=True, blank=True)
    se = models.FloatField(null=True, blank=True)
    cv = models.FloatField(null=True, blank=True)

    unit = models.CharField(choices=UNITS_CHOICES, max_length=CHAR_MAX_LENGTH, null=True, blank=True)

    class Meta:
        abstract = True
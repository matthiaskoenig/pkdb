"""
Reusable behavior for models.
"""
from django.db import models
from .utils import CHAR_MAX_LENGTH_LONG, CHAR_MAX_LENGTH



class Sidable(models.Model):
    """ Model has an sid. """
    sid = models.CharField(max_length=CHAR_MAX_LENGTH, primary_key=True)

    class Meta:
        abstract = True

class Externable(models.Model):
    format = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    subset_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    groupby = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)

    class Meta:
        abstract = True

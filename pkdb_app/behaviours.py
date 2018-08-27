"""
Reusable behavior for models.
"""

from django.db import models

from pkdb_app.utils import CHAR_MAX_LENGTH
from .categoricals import UNITS_CHOICES
CHAR_MAX_LENGTH_LONG = CHAR_MAX_LENGTH * 3


class Sidable(models.Model):
    """ Model has an sid. """
    sid = models.CharField(max_length=CHAR_MAX_LENGTH, primary_key=True)

    class Meta:
        abstract = True


class Externable(models.Model):
    format = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    subset_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)

    class Meta:
        abstract = True


class Valueable(models.Model):
    """ Valuable.

    Adds fields to store values with their statistics.
    """
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


class ValueableMap(models.Model):
    """ ValuableMap. """
    value_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)

    mean_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)
    median_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)
    min_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)
    max_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)
    sd_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)
    se_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)
    cv_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)

    unit_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True, blank=True)

    class Meta:
        abstract = True
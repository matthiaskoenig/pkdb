"""
Reusable behavior for models.
"""

from django.db import models
from django.core.exceptions import ValidationError
from pkdb_app.utils import CHAR_MAX_LENGTH
from .categoricals import UNITS_CHOICES



class Sidable(models.Model):
    """ Model has an sid. """
    sid = models.CharField(max_length=CHAR_MAX_LENGTH, primary_key=True)

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





class Blankable(models.Model):
    # when creating the BlankAble class object it will add a __blank_together__
    # attribute corresponding to the same in {YourModel}.MyMeta.blank_together
    def __new__(cls, *args, **kwargs):
        new = super().__new__(cls)
        if hasattr(cls, 'MyMeta'):
            if hasattr(cls.MyMeta, 'blank_together'):
                setattr(new, '__blank_together__', cls.MyMeta.blank_together)
        return new

    def save(self, *args, **kwargs):
        # returns False if any but not all of the __blank_together__ fields
        # are not blank
        not_blank_together = not (any([getattr(self, field, None) for field in getattr(self, '__not_blank_together__', None)]) and \
                              not all([getattr(self, field, None) for field in getattr(self, '__not_blank_together__', None)]))
        if not_blank_together:
            raise ValidationError(f"{getattr(self, '__not_blank_together__', None)} one of them cannot be blank.")
        return super().save(*args, **kwargs)

    class Meta:
        # prevents Django from having some bad behavior surrounding
        # inheritance of models that are not explicitly abstract
        abstract = True


class Describable(models.Model):
    """ Add description field. """
    description = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True


class Hashable(models.Model):
    """ Add hash key field. """
    hash = models.CharField(max_length=CHAR_MAX_LENGTH,blank=True, null=True)

    class Meta:
        abstract = True

class Sourceable(models.Model):
    source = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)  # todo: to file_filed
    figure = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)  # todo: to file_filed
    format = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)

    class Meta:
        abstract = True

    @staticmethod
    def fields():
        return ["source","figure","format"]

class Valueable(models.Model):
    """ Add fields to store values.

    In addition all the statistical values are stored.
    """
    count = models.IntegerField(null=True, blank=True)  # how many participants in characteristics
    value = models.DecimalField(max_digits = 40,decimal_places=20, null=True, blank=True)

    mean = models.DecimalField(max_digits = 40,decimal_places=20, null=True, blank=True)
    median = models.DecimalField(max_digits = 40,decimal_places=20, null=True, blank=True)
    min = models.DecimalField(max_digits = 40,decimal_places=20, null=True, blank=True)
    max = models.DecimalField(max_digits = 40,decimal_places=20, null=True, blank=True)
    sd = models.DecimalField(max_digits = 40,decimal_places=20, null=True, blank=True)
    se = models.DecimalField(max_digits = 40,decimal_places=20, null=True, blank=True)
    cv = models.DecimalField(max_digits = 40,decimal_places=20, null=True, blank=True)

    unit = models.CharField(choices=UNITS_CHOICES, max_length=CHAR_MAX_LENGTH, null=True, blank=True)

    class Meta:
        abstract = True

    #@staticmethod
    #def fields():
    #    return ["value",  "mean",  "median",  "min", "max", "sd",  "se",  "cv",  "unit", ]


class ValueableMap(models.Model):
    count_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)  # how many participants in characteristics
    value_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)

    mean_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    median_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    min_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    max_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    sd_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    se_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    cv_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)

    unit_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)

    class Meta:
        abstract = True

    #@staticmethod
    #def fields():
    #    return ["value_map", "mean_map", "median_map",  "min_map", "max_map","sd_map", "se_map", "cv_map", "unit_map" ]


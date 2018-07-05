"""
Describe group of subjects or individual (i.e. define the characteristics of the
group or individual).

How is different from things which will be measured?
From the data structure this has to be handled very similar.
"""

from django.db import models

from ..studies.models import Reference
from ..behaviours import Sidable, Describable
from ..categoricals import CHARACTERISTIC_DICT, CHARACTERISTIC_CHOICES, UNITS_CHOICES
from ..utils import CHAR_MAX_LENGTH


class Timecourse(models.Model):
    """ Storing of time course data.

    Store a binary blop of the data (json, pandas dataframe or similar, backwards compatible).
    """
    data = models.BinaryField()


class Characteristic(Sidable, models.Model):
    """ Characteristic.
    Characteristics are used to store the information about subjects.
    """
    value = models.CharField(choices=CHARACTERISTIC_CHOICES, max_length=CHAR_MAX_LENGTH)

    @property
    def characteristic_data(self):
        """ Returns the full information about the characteristic.

        :return:
        """
        return CHARACTERISTIC_DICT[self.value]

    @property
    def choices(self):
        return self.characteristic_data.choices

    class Meta:
        abstract = True


class CharacteristicValue(Characteristic):
    """
    This is the concrete selection/information of the characteristics.
    This stores the raw information. Derived values can be calculated.
    """
    choice = models.CharField(max_length=CHAR_MAX_LENGTH)  # check in validation that allowed choice

    count = models.IntegerField()  # how many participants in characteristics
    value = models.FloatField(null=True, blank=True)

    mean = models.FloatField(null=True, blank=True)
    median = models.FloatField(null=True, blank=True)
    min = models.FloatField(null=True, blank=True)
    max = models.FloatField(null=True, blank=True)
    sd = models.FloatField(null=True, blank=True)
    se = models.FloatField(null=True, blank=True)
    cv = models.FloatField(null=True, blank=True)

    unit = models.CharField(choices=UNITS_CHOICES, max_length=CHAR_MAX_LENGTH)

    #timecourse = models.ForeignKey(Timecourse)

    def validate(self):
        """ Check that choices are valid. I.e. that choice is allowed choice from choices for
        characteristics.

        Add checks for individuals and groups. For instance if count==1 than value must be filled,
        but not entries in mean, median, ...

        :return:
        """
        raise NotImplemented


class ProcessedCharacteristicValue(CharacteristicValue):
    """ Processed and normalized data (calculated on change from
    corresponding raw CharacteristicValue.
    """
    raw = models.OneToOneField(CharacteristicValue,parent_link=True, on_delete=True)


class Group(Sidable,Describable, models.Model):
    """ Individual or group of people.

    Groups are defined via their characteristics.
    """
    reference = models.ForeignKey(Reference, on_delete=True)
    # = models.TextField(null=True)
    count = models.IntegerField()
    characteristic_value = models.ManyToManyField(CharacteristicValue)

# TODO: How to handle Pharmacokinetics data?

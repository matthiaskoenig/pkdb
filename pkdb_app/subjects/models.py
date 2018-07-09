"""
Describe group of subjects or individual (i.e. define the characteristics of the
group or individual).

How is different from things which will be measured?
From the data structure this has to be handled very similar.
"""

from django.db import models

from ..studies.models import Reference
from ..behaviours import Sidable, Describable, Values
from ..categoricals import CHARACTERISTIC_DICT, CHARACTERISTIC_CHOICES
from ..utils import CHAR_MAX_LENGTH
from .managers import GroupManager


class Timecourse(models.Model):
    """ Storing of time course data.

    Store a binary blop of the data (json, pandas dataframe or similar, backwards compatible).
    """
    data = models.BinaryField()


class Characteristic(models.Model):
    """ Characteristic.
    Characteristics are used to store the information about subjects.
    """
    category = models.CharField(choices=CHARACTERISTIC_CHOICES, max_length=CHAR_MAX_LENGTH)

    @property
    def characteristic_data(self):
        """ Returns the full information about the characteristic.

        :return:
        """
        return CHARACTERISTIC_DICT[self.category]

    @property
    def choices(self):
        return self.characteristic_data.choices

    class Meta:
        abstract = True


class Group(Sidable,Describable, models.Model):
    """ Individual or group of people.

    Groups are defined via their characteristics.
    """
    reference = models.ForeignKey(Reference, on_delete=True, related_name='groups', null=True, blank=True)
    # = models.TextField(null=True)
    count = models.IntegerField()
    objects = GroupManager()


class CharacteristicValue(Values,Characteristic):
    """
    This is the concrete selection/information of the characteristics.
    This stores the raw information. Derived values can be calculated.
    """
    group = models.ForeignKey(Group, related_name="characteristic_values", null=True, on_delete=True)


    #def validate(self):
    #    """ Check that choices are valid. I.e. that choice is allowed choice from choices for
    #    characteristics.

    #    Add checks for individuals and groups. For instance if count==1 than value must be filled,
    #    but not entries in mean, median, ...

    #    :return:
    #    """
    #    raise NotImplemented


class ProcessedCharacteristicValue(Values,Characteristic,models.Model):
    """ Processed and normalized data (calculated on change from
    corresponding raw CharacteristicValue.
    """
    raw = models.ForeignKey(CharacteristicValue, null=True, on_delete=True)




# TODO: How to handle Pharmacokinetics data?

"""
Describe group of subjects or individual (i.e. define the characteristics of the
group or individual).

How is different from things which will be measured?
From the data structure this has to be handled very similar.
"""

from django.db import models

from ..studies.models import Study, Reference
from ..behaviours import Sidable, Describable, Valueable
from ..categoricals import CHARACTERISTIC_DICT, CHARACTERISTIC_CHOICES
from ..utils import CHAR_MAX_LENGTH
from .managers import GroupManager


# TODO: Add ExclusionCriteria as extra class on group | or via field ?
# Not clear what is best: The important thing is that stated exclusion criteria
# must be encodable and be found as such (often via cutoffs)
# - how to represent cutoff & negation

# - Exclusion/Inclusion
# - Group
# - Intervention

# - DataSets/Output



# Idea: GroupSet

class Group(Describable, models.Model):
    """ Individual or group of people.

    Groups are defined via their characteristics.
    """
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    study = models.ForeignKey(Study, on_delete=True, related_name='groups',to_field="sid", db_column="study_sid",null=True, blank=True)
    count = models.IntegerField()  # number of people/animals/objects in group
    objects = GroupManager()

    @property
    def reference(self):
        return self.study.reference


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


class CharacteristicValue(Valueable, Characteristic):
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


class ProcessedCharacteristicValue(Valueable, Characteristic, models.Model):
    """ Processed and normalized data (calculated on change from
    corresponding raw CharacteristicValue.
    """
    raw = models.ForeignKey(CharacteristicValue, null=True, on_delete=True)
    # method field? for different processing?

    # TODO: add methods for doing the processing & automatic update if corresponding
    # Value is changed.
    # -> move to a ProcessedValuable

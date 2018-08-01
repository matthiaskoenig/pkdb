"""
Describe group of subjects or individual (i.e. define the characteristics of the
group or individual).

How is different from things which will be measured?
From the data structure this has to be handled very similar.
"""

from django.db import models

from ..studies.models import Study, Reference
from ..behaviours import Sidable, Describable, Valueable
from ..categoricals import CHARACTERISTIC_DICT, CHARACTERISTIC_CHOICES, CHARACTERISTICA_CHOICES, GROUP_CRITERIA, \
    INCLUSION_CRITERIA, EXCLUSION_CRITERIA
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
class GroupSet(Describable,models.Model):
    study = models.ForeignKey(Study, on_delete=True, related_name='groups',to_field="sid", db_column="study_sid",null=True, blank=True)


    @property
    def reference(self):
        return self.study.reference

class Group(models.Model):
    """ Individual or group of people.

    Groups are defined via their characteristics.
    """
    groupset = models.ForeignKey(GroupSet,on_delete=True, related_name="groups")
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    count = models.IntegerField()  # number of people/animals/objects in group
    objects = GroupManager()

    @property
    def reference(self):
        return self.groupset.reference


class Characteristic(models.Model):
    """ Characteristic.

    Characteristics are used to store information about a group of subjects.
    Such a group is defined by
    - Inclusion criteria, which define general characteristics (often via cutoffs, i.e. min or max) of which
      subjects are in a group.
    - Exclusion criteria, analogue to inclusion criteria but defines which subjects are excluded.
    - Group criteria, concrete properties/characteristics of the group of subjects.

    The type of characteristic is defined via the cvtype.
    When group characterists are curated it is important to specify the inclusion/exclusion criteria in
    addition to the group criteria.
    """
    category = models.CharField(choices=CHARACTERISTIC_CHOICES, max_length=CHAR_MAX_LENGTH)
    choice = models.CharField(max_length=CHAR_MAX_LENGTH, null=True,
                              blank=True)  # check in validation that allowed choice
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


class Characteristica(Valueable, Characteristic):
    """
    This is the concrete selection/information of the characteristics.
    This stores the raw information. Derived values can be calculated.
    """
    groupset = models.ForeignKey(GroupSet, related_name="characteristica", null=True, on_delete=True)
    group = models.ForeignKey(Group, related_name="characteristica", null=True, on_delete=True)
    ctype = models.CharField(choices=CHARACTERISTICA_CHOICES, max_length=CHAR_MAX_LENGTH, default=GROUP_CRITERIA)

    @property
    def is_inclusion(self):
        return self.ctype == INCLUSION_CRITERIA

    @property
    def is_exclusion(self):
        return self.ctype == EXCLUSION_CRITERIA

    #def validate(self):
    #    """ Check that choices are valid. I.e. that choice is allowed choice from choices for
    #    characteristics.

    #    Add checks for individuals and groups. For instance if count==1 than value must be filled,
    #    but not entries in mean, median, ...

    #    :return:
    #    """
    #    raise NotImplemented


class CleanCharacteristica(Valueable, Characteristic, models.Model):
    """ Processed and normalized data (calculated on change from
    corresponding raw CharacteristicValue.

    - convert exclusion to inclusion criteria
    """
    raw = models.ForeignKey(Characteristica, related_name="clean", null=True, on_delete=True)




    # method field? for different processing?

    # TODO: add methods for doing the processing & automatic update if corresponding
    # Value is changed.
    # -> move to a ProcessedValuable

"""
Describe group of subjects or individual (i.e. define the characteristics of the
group or individual).

How is different from things which will be measured?
From the data structure this has to be handled very similar.
"""

from django.db import models
from ..behaviours import Valueable, Describable
from ..categoricals import CHARACTERISTIC_DICT, CHARACTERISTIC_CHOICES, CHARACTERISTICA_CHOICES, GROUP_CRITERIA, \
    INCLUSION_CRITERIA, EXCLUSION_CRITERIA
from ..utils import CHAR_MAX_LENGTH
from .managers import GroupManager, GroupSetManager


# TODO: Add ExclusionCriteria as extra class on group | or via field ?
# Not clear what is best: The important thing is that stated exclusion criteria
# must be encodable and be found as such (often via cutoffs)
# - how to represent cutoff & negation

# - Exclusion/Inclusion
# - Group
# - Intervention

# - DataSets/Output





class Set(Describable, models.Model):
    """
    abstarct class for all set classes
    """

    @property
    def reference(self):
        return self.reference

    class Meta:
        abstract = True

class GroupSet(Set):
    objects = GroupSetManager()


class Group(models.Model):
    """ Individual or group of people.

    Groups are defined via their characteristics.
    """
    groupset = models.ForeignKey(GroupSet,on_delete=models.SET_NULL,null=True,related_name="groups")
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    count = models.IntegerField()  # number of people/animals/objects in group
    objects = GroupManager()

    @property
    def reference(self):
        return self.groupset.reference


class IndividualSet(Set):
    pass


class Individual(models.Model):
    """ Individual or group of people.

    Individuals are defined via their characteristics.
    """
    individualset = models.ForeignKey(IndividualSet,on_delete=models.CASCADE, related_name="individuals")
    group =  models.ForeignKey(Group, on_delete=models.CASCADE, related_name="individuals")

    name = models.CharField(max_length=CHAR_MAX_LENGTH)

    #objects = GroupManager()

    @property
    def reference(self):
        return self.individualset.reference


class Characteristica(Valueable, models.Model):
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

    This is the concrete selection/information of the characteristics.
    This stores the raw information. Derived values can be calculated.
    """
    category = models.CharField(choices=CHARACTERISTIC_CHOICES, max_length=CHAR_MAX_LENGTH)
    choice = models.CharField(max_length=CHAR_MAX_LENGTH*3, null=True,blank=True)  # check in validation that allowed choice
    groupset = models.ForeignKey(GroupSet, related_name="characteristica", null=True, blank=True,on_delete=models.CASCADE)
    group = models.ForeignKey(Group, related_name="characteristica", null=True, blank=True,on_delete=models.CASCADE)
    individualset = models.ForeignKey(IndividualSet, related_name="characteristica", null=True,blank=True, on_delete=models.CASCADE)
    individual = models.ForeignKey(Individual, related_name="characteristica", null=True,blank=True, on_delete=models.CASCADE)
    ctype = models.CharField(choices=CHARACTERISTICA_CHOICES, max_length=CHAR_MAX_LENGTH, default=GROUP_CRITERIA) #this is for exclusion and inclustion


    @property
    def is_inclusion(self):
        return self.ctype == INCLUSION_CRITERIA

    @property
    def is_exclusion(self):
        return self.ctype == EXCLUSION_CRITERIA

    @property
    def characteristic_data(self):
        """ Returns the full information about the characteristic.

        :return:
        """
        return CHARACTERISTIC_DICT[self.category]

    @property
    def choices(self):
        return self.characteristic_data.choices


    #def validate(self):
    #    """ Check that choices are valid. I.e. that choice is allowed choice from choices for
    #    characteristics.

    #    Add checks for individuals and groups. For instance if count==1 than value must be filled,
    #    but not entries in mean, median, ...

    #    :return:
    #    """
    #    raise NotImplemented


class CleanCharacteristica(Characteristica):
    """ Processed and normalized data (calculated on change from
    corresponding raw CharacteristicValue.

    - convert exclusion to inclusion criteria
    """
    raw = models.ForeignKey(Characteristica, related_name="clean", null=True, on_delete=True)

    # method field? for different processing?

    # TODO: add methods for doing the processing & automatic update if corresponding
    # Value is changed.
    # -> move to a ProcessedValuable



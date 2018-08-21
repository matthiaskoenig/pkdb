"""
Describe group of subjects or individual (i.e. define the characteristics of the
group or individual).

How is different from things which will be measured?
From the data structure this has to be handled very similar.
"""
from django.db import models

from pkdb_app.storage import OverwriteStorage
from ..behaviours import Valueable, ValueableMap
from ..categoricals import CHARACTERISTIC_DICT, CHARACTERISTIC_CHOICES, CHARACTERISTICA_CHOICES, GROUP_CRITERIA, \
    INCLUSION_CRITERIA, EXCLUSION_CRITERIA
from ..utils import CHAR_MAX_LENGTH
from .managers import GroupManager, GroupSetManager, IndividualManager, IndividualSetManager


# ----------------------------------
# DataFile
# ----------------------------------
class DataFile(models.Model):
    """ Table or figure from where the data comes from (png).

    This should be in a separate class, so that they can be easily displayed/filtered/...
    """

    file = models.FileField(upload_to="data", storage=OverwriteStorage() ,null=True, blank=True)  # table or figure
    filetype = models.CharField(null=True, blank=True, max_length=CHAR_MAX_LENGTH)  # XLSX, PNG, CSV

    def __str__(self):
        return self.file.name


# ----------------------------------
# Group
# ----------------------------------
class GroupSet(models.Model):
    objects = GroupSetManager()


class AbstractGroup(models.Model):
    objects = GroupManager()

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class GroupEx(AbstractGroup):
    """ Group (external curated layer).

    Groups are defined via their characteristica.
    A group can be a subgroup of another group via the parent field.
    """
    source = models.ForeignKey(DataFile, related_name="s_group_exs", null=True, blank=True,
                                on_delete=models.SET_NULL)
    format = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    figure = models.ForeignKey(DataFile, related_name="f_group_exs", null=True, blank=True,
                               on_delete=models.SET_NULL)
    groupset = models.ForeignKey(GroupSet, on_delete=models.CASCADE, null=True, related_name="group_exs")

    parent = models.ForeignKey("Group", null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    name_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    count = models.IntegerField()
    count_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)

    objects = GroupManager()

    @property
    def study(self):
        return self.groupset.study

    @property
    def reference(self):
        return self.study.reference

    class Meta:
        unique_together = ('groupset', 'name', 'name_map', 'source')


class Group(models.Model):
    """ Group. """
    ex = models.ForeignKey(GroupEx, related_name="groups", null=True, on_delete=models.CASCADE)

    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    count = models.IntegerField()
    parent = models.ForeignKey("Group", null=True, blank=True, on_delete=models.CASCADE)

    objects = GroupManager()

    #class Meta:
    #todo: in validator unique_together = ('ex__groupset', 'name')

    @property
    def source(self):
        return self.ex.source

    @property
    def figure(self):
        return self.ex.figure


# ----------------------------------
# Individual
# ----------------------------------
class IndividualSet(models.Model):
    objects = IndividualSetManager()


class AbstractIndividual(models.Model):
    objects = IndividualManager()

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class IndividualEx(AbstractIndividual):
    """ Individual (external curated layer).

    This contains maps and splittings.
    Individuals are defined via their characteristics, analogue to groups.
    """
    source = models.ForeignKey(DataFile, related_name="s_individual_exs", null=True, blank=True,
                               on_delete=models.SET_NULL)
    format = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    figure = models.ForeignKey(DataFile, related_name="f_individual_exs", null=True, blank=True,
                               on_delete=models.SET_NULL)

    individualset = models.ForeignKey(IndividualSet, on_delete=models.CASCADE, related_name="individual_exs")
    group_ex = models.ForeignKey(GroupEx, on_delete=models.CASCADE, related_name="individual_exs", null=True, blank=True)
    group_ex_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    name = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    name_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)

    class Meta:
        unique_together = ('individualset', 'name', 'name_map', 'source')

    @property
    def study(self):
        return self.individualset.study

    @property
    def reference(self):
        return self.study.reference

    def groups_in_study(self):
        return self.study.groupset.groups

    # TODO: validation in one place
    # TODO: validation: either name or name_map must be set


class Individual(AbstractIndividual):
    """ Single individual in data base.

    This does not contain any mappings are splits any more.
    """
    ex = models.ForeignKey(IndividualEx, related_name="individuals", null=True, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="individuals")
    name = models.CharField(max_length=CHAR_MAX_LENGTH)

    # TODO: unique together  unique_together = ('ex__individualset', 'name')

    @property
    def source(self):
        return self.ex.source

    @property
    def figure(self):
        return self.ex.figure



# ----------------------------------
# Characteristica
# ----------------------------------
class AbstractCharacteristica(models.Model):
    category = models.CharField(choices=CHARACTERISTIC_CHOICES, max_length=CHAR_MAX_LENGTH)
    choice = models.CharField(max_length=CHAR_MAX_LENGTH * 3, null=True,
                              blank=True)
    ctype = models.CharField(choices=CHARACTERISTICA_CHOICES, max_length=CHAR_MAX_LENGTH,
                             default=GROUP_CRITERIA)  # this is for exclusion and inclusion

    class Meta:
        abstract = True

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


class CharacteristicaEx(AbstractCharacteristica, ValueableMap, Valueable):
    """ Characteristica  (external curated layer).

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
    count = models.IntegerField(null=True, blank=True)
    count_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    choice_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)

    group_ex = models.ForeignKey(GroupEx, related_name="characteristica_ex", null=True, blank=True,on_delete=models.CASCADE)
    individual_ex = models.ForeignKey(IndividualEx, related_name="characteristica_ex", null=True, blank=True, on_delete=models.CASCADE)


class Characteristica(AbstractCharacteristica, Valueable, models.Model):
    """ Characteristic. """

    group = models.ForeignKey(Group, related_name="characteristica", null=True, blank=True,on_delete=models.CASCADE)
    individual = models.ForeignKey(Individual, related_name="characteristica", null=True, blank=True, on_delete=models.CASCADE)

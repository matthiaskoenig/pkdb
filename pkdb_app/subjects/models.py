"""
Describe group of subjects or individual (i.e. define the characteristics of the
group or individual).

How is different from things which will be measured?
From the data structure this has to be handled very similar.
"""
from django.db import models

from pkdb_app.storage import OverwriteStorage
from ..behaviours import Valueable, Describable, ValueableMap, Sourceable
from ..categoricals import CHARACTERISTIC_DICT, CHARACTERISTIC_CHOICES, CHARACTERISTICA_CHOICES, GROUP_CRITERIA, \
    INCLUSION_CRITERIA, EXCLUSION_CRITERIA
from ..utils import CHAR_MAX_LENGTH
from .managers import GroupManager, GroupSetManager, IndividualManager, IndividualSetManager

# TODO: Add ExclusionCriteria as extra class on group | or via field ?
# Not clear what is best: The important thing is that stated exclusion criteria
# must be encodable and be found as such (often via cutoffs)
# - how to represent cutoff & negation
# - Exclusion/Inclusion
# - Group
# - Intervention
# - DataSets/Output

class DataFile(models.Model):
    """ Table or figure from where the data comes from (png).

    This should be in a separate class, so that they can be easily displayed/filtered/...
    """

    file = models.FileField(upload_to="data", storage=OverwriteStorage() ,null=True, blank=True)  # table or figure
    filetype = models.CharField(null=True, blank=True, max_length=CHAR_MAX_LENGTH)  # XLSX, PNG, CSV

    def __str__(self):
        return self.file.nam
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

    @property
    def study(self):
        return self.groupset.study

    class Meta:
        unique_together = ('groupset', 'name')


class IndividualSet(Set):
    objects = IndividualSetManager()


class IndividualMap(models.Model):
    group_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    name_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)

    class Meta:
        abstract = True


class Individual(IndividualMap,Sourceable,models.Model):
    """ Individual or group of people.

    Individuals are defined via their characteristics.
    """
    source = models.ForeignKey(DataFile,related_name="individual_sources", null=True,blank=True, on_delete=models.SET_NULL)
    figure = models.ForeignKey(DataFile, related_name="individual_figures", null=True,blank=True, on_delete=models.SET_NULL)

    individualset = models.ForeignKey(IndividualSet,on_delete=models.CASCADE, related_name="individuals")
    group =  models.ForeignKey(Group, on_delete=models.CASCADE, related_name="individuals",null=True, blank=True)
    name = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    ###############

    objects = IndividualManager()



    @property
    def reference(self):
        return self.individualset.reference

    @property
    def study(self):
        return self.individualset.study

    def groups_in_study(self):
        return self.study.groupset.groups

    class Meta:
        unique_together = ('individualset','name','name_map','source')

    def __str__(self):
        return self.name


class CharacteristicaBase(models.Model):

    category = models.CharField(choices=CHARACTERISTIC_CHOICES, max_length=CHAR_MAX_LENGTH)
    choice = models.CharField(max_length=CHAR_MAX_LENGTH * 3, null=True,
                              blank=True)  # check in validation that allowed choice
    ctype = models.CharField(choices=CHARACTERISTICA_CHOICES, max_length=CHAR_MAX_LENGTH,
                             default=GROUP_CRITERIA)  # this is for exclusion and inclustion

    category_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    choice_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    ctype_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)

    class Meta:
        abstract = True


class Characteristica(CharacteristicaBase,ValueableMap,Valueable, models.Model):
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

    groupset = models.ForeignKey(GroupSet, related_name="characteristica", null=True, blank=True,on_delete=models.CASCADE)
    group = models.ForeignKey(Group, related_name="characteristica", null=True, blank=True,on_delete=models.CASCADE)
    individual = models.ForeignKey(Individual, related_name="characteristica", null=True,blank=True, on_delete=models.CASCADE)
    individualset = models.ForeignKey(IndividualSet, related_name="characteristica", null=True,blank=True, on_delete=models.CASCADE)


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


class CleanCharacteristica(Characteristica):
    """ Processed and normalized data (calculated on change from
    corresponding raw CharacteristicValue.

    - convert exclusion to inclusion criteria
    """
    raw = models.ForeignKey(Characteristica, related_name="clean", null=True, on_delete=True)
    # TODO: add methods for doing the processing & automatic update if corresponding

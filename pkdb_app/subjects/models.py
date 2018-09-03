"""
Describe group of subjects or individual (i.e. define the characteristics of the
group or individual).

How is different from things which will be measured?
From the data structure this has to be handled very similar.
"""
from django.db import models

from pkdb_app.normalization import get_sd, get_se, get_cv
from pkdb_app.storage import OverwriteStorage
from ..behaviours import (
    Valueable,
    ValueableMap,
    Externable,
    ValueableMapNotBlank,
    ValueableNotBlank,
)
from ..categoricals import (
    CHARACTERISTIC_DICT,
    CHARACTERISTIC_CHOICES,
    CHARACTERISTICA_CHOICES,
    GROUP_CRITERIA,
    INCLUSION_CRITERIA,
    EXCLUSION_CRITERIA,
)
from ..utils import CHAR_MAX_LENGTH
from .managers import (
    GroupExManager,
    GroupSetManager,
    IndividualExManager,
    IndividualSetManager,
    IndividualManager,
    GroupManager,
    CharacteristicaManager,
)


# ----------------------------------
# DataFile
# ----------------------------------
class DataFile(models.Model):
    """ Table or figure from where the data comes from (png).

    This should be in a separate class, so that they can be easily displayed/filtered/...
    """

    file = models.FileField(
        upload_to="data", storage=OverwriteStorage(), null=True, blank=True
    )  # table or figure
    filetype = models.CharField(
        null=True, blank=True, max_length=CHAR_MAX_LENGTH
    )  # XLSX, PNG, CSV

    def __str__(self):
        return self.file.name


# ----------------------------------
# Group
# ----------------------------------
class GroupSet(models.Model):
    objects = GroupSetManager()

    @property
    def groups(self):
        groups = Group.objects.filter(ex__in=self.group_exs.all())
        return groups


class AbstractGroup(models.Model):
    objects = GroupExManager()

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class GroupEx(Externable, AbstractGroup):
    """ Group (external curated layer).

    Groups are defined via their characteristica.
    A group can be a subgroup of another group via the parent field.
    """

    source = models.ForeignKey(
        DataFile, related_name="s_group_exs", null=True, on_delete=models.SET_NULL
    )
    figure = models.ForeignKey(
        DataFile, related_name="f_group_exs", null=True, on_delete=models.SET_NULL
    )
    groupset = models.ForeignKey(
        GroupSet, on_delete=models.CASCADE, null=True, related_name="group_exs"
    )

    parent_ex = models.ForeignKey("GroupEX", null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    name_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    count = models.IntegerField()
    count_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    objects = GroupExManager()

    @property
    def study(self):
        return self.groupset.study

    @property
    def reference(self):
        return self.study.reference

    class Meta:
        unique_together = ("groupset", "name", "name_map", "source")


class Group(models.Model):
    """ Group. """

    ex = models.ForeignKey(
        GroupEx, related_name="groups", null=True, on_delete=models.CASCADE
    )

    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    count = models.IntegerField()
    parent = models.ForeignKey("Group", null=True, on_delete=models.CASCADE)
    objects = GroupManager()

    # class Meta:
    # todo: in validator unique_together = ('ex__groupset', 'name')

    @property
    def source(self):
        return self.ex.source

    @property
    def figure(self):
        return self.ex.figure

    @property
    def characteristica_all(self):
        characteristica_all = self.characteristica.all()
        if self.parent:
            characteristica_all = characteristica_all | self.parent.characteristica_all
        return characteristica_all


# ----------------------------------
# Individual
# ----------------------------------
class IndividualSet(models.Model):
    objects = IndividualSetManager()

    @property
    def individuals(self):
        individuals = Individual.objects.filter(ex__in=self.individual_exs.all())
        return individuals


class AbstractIndividual(models.Model):
    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class IndividualEx(Externable, AbstractIndividual):
    """ Individual (external curated layer).
    This contains maps and splittings.
    Individuals are defined via their characteristics, analogue to groups.
    """

    source = models.ForeignKey(
        DataFile, related_name="s_individual_exs", null=True, on_delete=models.SET_NULL
    )
    format = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    figure = models.ForeignKey(
        DataFile, related_name="f_individual_exs", null=True, on_delete=models.SET_NULL
    )

    individualset = models.ForeignKey(
        IndividualSet, on_delete=models.CASCADE, related_name="individual_exs"
    )
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="individual_exs", null=True
    )
    group_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    name = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    name_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    objects = IndividualExManager()

    class Meta:
        unique_together = ("individualset", "name", "name_map", "source")

    @property
    def study(self):
        return self.individualset.study

    @property
    def reference(self):
        return self.study.reference

    def groups_in_study(self):
        return self.study.groupset.group_exs

    # TODO: validation in one place
    # TODO: validation: either name or name_map must be set


class Individual(AbstractIndividual):
    """ Single individual in data base.

    This does not contain any mappings are splits any more.
    """

    ex = models.ForeignKey(
        IndividualEx, related_name="individuals", null=True, on_delete=models.CASCADE
    )
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="individuals"
    )
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    objects = IndividualManager()

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
    category = models.CharField(
        choices=CHARACTERISTIC_CHOICES, max_length=CHAR_MAX_LENGTH
    )
    choice = models.CharField(max_length=CHAR_MAX_LENGTH * 3, null=True)
    ctype = models.CharField(
        choices=CHARACTERISTICA_CHOICES,
        max_length=CHAR_MAX_LENGTH,
        default=GROUP_CRITERIA,
    )  # this is for exclusion and inclusion
    count = models.IntegerField(null=True)

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


class CharacteristicaEx(
    AbstractCharacteristica, ValueableMapNotBlank, ValueableNotBlank
):
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

    count_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    choice_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    group_ex = models.ForeignKey(
        GroupEx, related_name="characteristica_ex", null=True, on_delete=models.CASCADE
    )
    individual_ex = models.ForeignKey(
        IndividualEx,
        related_name="characteristica_ex",
        null=True,
        on_delete=models.CASCADE,
    )
    objects = CharacteristicaManager()


class Characteristica(AbstractCharacteristica, Valueable, models.Model):
    """ Characteristic. """

    group = models.ForeignKey(
        Group, related_name="characteristica", null=True, on_delete=models.CASCADE
    )
    individual = models.ForeignKey(
        Individual, related_name="characteristica", null=True, on_delete=models.CASCADE
    )

    def save(self, *args, **kwargs):
        if not self.sd:
            self.sd = get_sd(se=self.se, count=self.count, mean=self.mean, cv=self.cv)

        if not self.se:
            self.se = get_se(sd=self.sd, count=self.count, mean=self.mean, cv=self.cv)

        if not self.cv:
            self.cv = get_cv(se=self.se, count=self.count, mean=self.mean, sd=self.sd)

        super().save(*args, **kwargs)

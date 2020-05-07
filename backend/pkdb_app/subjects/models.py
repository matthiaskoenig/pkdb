"""
Describe group of subjects or individual (i.e. define the characteristics of the
group or individual).

How is different from things which will be measured?
From the data structure this has to be handled very similar.
"""

from django.apps import apps
from django.db import models

from pkdb_app.behaviours import Normalizable, ExMeasurementTypeable
from .managers import (
    IndividualManager,
    GroupManager,
    CharacteristicaExManager,
)
from ..behaviours import (
    Externable, Accessible)
from ..storage import OverwriteStorage
from ..utils import CHAR_MAX_LENGTH, CHAR_MAX_LENGTH_LONG

SUBJECT_TYPE_GROUP = "group"
SUBJECT_TYPE_INDIVIDUAL = "individual"

ADDITIVE_CHARACTERISTICA = ["disease", "abstinence"]


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

    @property
    def name(self):
        return self.file.name

    @property
    def timecourses(self):
        Timecourse = apps.get_model('outputs', 'Timecourse')
        tc = Timecourse.objects.filter(ex__in=self.f_timecourse_exs.all()).filter(normed=True)
        return tc

    def __str__(self):
        return self.file.name


# ----------------------------------
# Group
# ----------------------------------


class GroupSet(models.Model):

    @property
    def groups(self):
        groups = Group.objects.filter(ex__in=self.group_exs.all())
        return groups

    @property
    def count(self):
        if self.groups:
            return self.groups.count()
        else:
            return 0


class GroupEx(Externable):
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

    @property
    def study(self):
        return self.groupset.study

    @property
    def reference(self):
        return self.study.reference


class Group(Accessible):
    """ Group. """

    ex = models.ForeignKey(
        GroupEx, related_name="groups", null=True, on_delete=models.CASCADE
    )

    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    count = models.IntegerField()
    parent = models.ForeignKey("Group", null=True, on_delete=models.CASCADE)
    characteristica_all_normed = models.ManyToManyField("Characteristica", related_name="groups",
                                                        through="GroupCharacteristica")

    study = models.ForeignKey('studies.Study', on_delete=models.CASCADE, related_name="groups")

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
    def parents(self):
        parents = []
        if self.parent:
            parents = [self.parent.pk] + self.parent.parents
        return parents

    @property
    def _characteristica_all(self):
        _characteristica_all = self.characteristica.all()
        this_measurements = _characteristica_all.exclude(
            measurement_type__info_node__name__in=ADDITIVE_CHARACTERISTICA).values_list("measurement_type", flat=True)
        if self.parent:
            _characteristica_all = _characteristica_all | self.parent._characteristica_all.exclude(
                measurement_type__in=this_measurements)
        return _characteristica_all

    @property
    def _characteristica_all_normed(self):
        return self._characteristica_all.filter(normed=True)


# ----------------------------------
# Individual
# ----------------------------------
class IndividualSet(models.Model):
    @property
    def individuals(self):
        individuals = Individual.objects.filter(ex__in=self.individual_exs.all())
        return individuals

    @property
    def count(self):
        if self.individuals:
            return self.individuals.count()
        else:
            return 0


class AbstractIndividual(models.Model):
    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class IndividualEx(Externable):
    """ Individual (external curated layer).
    This contains maps and splittings.
    Individuals are defined via their characteristics, analogue to groups.
    """

    source = models.ForeignKey(DataFile, related_name="s_individual_exs", null=True, on_delete=models.SET_NULL)
    figure = models.ForeignKey(DataFile, related_name="f_individual_exs", null=True, on_delete=models.SET_NULL)
    individualset = models.ForeignKey(IndividualSet, on_delete=models.CASCADE, related_name="individual_exs")

    @property
    def study(self):
        return self.individualset.study

    @property
    def reference(self):
        return self.study.reference

    def groups_in_study(self):
        return self.study.groupset.group_exs


class Individual(AbstractIndividual, Accessible):
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
    characteristica_all_normed = models.ManyToManyField("Characteristica", related_name="individuals",
                                                        through="IndividualCharacteristica")

    study = models.ForeignKey('studies.Study', on_delete=models.CASCADE, related_name="individuals")

    objects = IndividualManager()

    @property
    def source(self):
        return self.ex.source

    @property
    def figure(self):
        return self.ex.figure

    @property
    def _characteristica_normed(self):
        return self.characteristica.filter(normed=True)

    @property
    def _characteristica_all_normed(self):
        _characteristica_normed = self._characteristica_normed

        # charcteristica from related groups with the same measurement type as these used in the individual are excluded.
        # this_measurements = characteristica_normed.values_list("measurement_type", flat=True)
        this_measurements = _characteristica_normed.exclude(
            measurement_type__info_node__name__in=ADDITIVE_CHARACTERISTICA).values_list("measurement_type", flat=True)
        return (_characteristica_normed | self.group._characteristica_all_normed.exclude(
            measurement_type__in=this_measurements))

    @property
    def group_indexing(self):
        return self.group.name

    @property
    def characteristica_measurements(self):
        return [characteristica.measurement_type for characteristica in self.characteristica_all_normed.all()]

    @property
    def characteristica_choices(self):
        return {characteristica.measurement_type: characteristica.choice for characteristica in
                self.characteristica_all_normed.all()}


# ----------------------------------
# Characteristica
# ----------------------------------

class CharacteristicaEx(models.Model):
    """ Characteristica  (external curated layer).

        Characteristics are used to store information about a group of subjects.
        Such a group is defined by
        - Inclusion criteria, which define general characteristics (often via cutoffs, i.e. min or max) of which
          subjects are in a group.
        - Exclusion criteria, analogue to inclusion criteria but defines which subjects are excluded.
        - Group criteria, concrete properties/characteristics of the group of subjects.

        The type of characteristic is defined via the cvtype.
        When group characteristica are curated it is important to specify the inclusion/exclusion criteria in
        addition to the group criteria.

    This is the concrete selection/information of the characteristics.
    This stores the raw information. Derived values can be calculated.
    """
    group_ex = models.ForeignKey(
        GroupEx, related_name="characteristica_ex", null=True, on_delete=models.CASCADE
    )
    individual_ex = models.ForeignKey(
        IndividualEx,
        related_name="characteristica_ex",
        null=True,
        on_delete=models.CASCADE,
    )

    objects = CharacteristicaExManager()


class Characteristica(Accessible, Normalizable):
    """ Characteristic. """

    group = models.ForeignKey(
        Group, related_name="characteristica", null=True, on_delete=models.CASCADE
    )
    individual = models.ForeignKey(
        Individual, related_name="characteristica", null=True, on_delete=models.CASCADE
    )
    count = models.IntegerField(default=1)

    @property
    def raw_pk(self):
        if self.raw:
            return self.raw.pk
        else:
            return None

    @property
    def study(self):
        if self.group:
            return self.group.study
        else:
            return self.individual.study

    def study_name(self):
        return self.study.name

    def study_sid(self):
        return self.study.sid

    @property
    def all_group_pks(self):
        parents = []
        if self.group:
            parents = [self.group.pk] + self.group.parents
        return parents

    @property
    def subject_type(self):
        if self.group:
            return SUBJECT_TYPE_GROUP
        else:
            return SUBJECT_TYPE_INDIVIDUAL

    @property
    def group_name(self):
        if self.group:
            return self.group.name

    @property
    def group_pk(self):
        if self.group:
            return self.group.pk

    @property
    def group_count(self):
        if self.group:
            return self.group.count

    @property
    def group_parent_pk(self):
        if self.group:
            if self.group.parent:
                return self.group.parent.pk

    @property
    def individual_name(self):
        if self.individual:
            return self.individual.name

    @property
    def individual_pk(self):
        if self.individual:
            return self.individual.pk

    @property
    def individual_group_pk(self):
        if self.individual:
            return self.individual.group.pk


class SubjectCharacteristica(models.Model):
    class Meta:
        abstract = True

    @property
    def characteristica_pk(self):
        return self.characteristica.pk

    @property
    def raw_pk(self):
        return self.characteristica.raw_pk

    @property
    def normed(self):
        return self.characteristica.normed

    @property
    def count(self):
        return self.characteristica.count

    @property
    def measurement_type(self):
        return self.characteristica.measurement_type.info_node.name

    @property
    def choice(self):
        if self.characteristica.choice:
            return self.characteristica.choice.info_node.name

    @property
    def substance(self):
        if self.characteristica.substance:
            return self.characteristica.substance.info_node.name

    @property
    def unit(self):
        return self.characteristica.unit

    @property
    def value(self):
        return self.characteristica.value

    @property
    def mean(self):
        return self.characteristica.mean

    @property
    def median(self):
        return self.characteristica.median

    @property
    def min(self):
        return self.characteristica.min

    @property
    def max(self):
        return self.characteristica.max

    @property
    def sd(self):
        return self.characteristica.sd

    @property
    def se(self):
        return self.characteristica.se

    @property
    def cv(self):
        return self.characteristica.cv


class GroupCharacteristica(Accessible, SubjectCharacteristica):
    characteristica = models.ForeignKey(Characteristica, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("characteristica", "group")

    @property
    def study(self):
        return self.group.study

    @property
    def group_pk(self):
        return self.group.pk

    @property
    def group_parent_pk(self):
        if self.group.parent:
            return self.group.parent.pk

    @property
    def group_name(self):
        return self.group.name

    @property
    def group_count(self):
        return self.group.count


class IndividualCharacteristica(Accessible, SubjectCharacteristica):
    characteristica = models.ForeignKey(Characteristica, on_delete=models.CASCADE)
    individual = models.ForeignKey(Individual, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("characteristica", "individual")

    @property
    def study(self):
        return self.individual.study

    @property
    def individual_pk(self):
        return self.individual.pk

    @property
    def individual_name(self):
        return self.individual.name

    @property
    def individual_group_pk(self):
        return self.individual.group.pk

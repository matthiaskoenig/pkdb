"""Models describing groups and individuals as subjects, and their characteristica.

Data structure wise, subjects are handled very similarly to the things which
are measured on them.
"""

from django.db import models

from pkdb_app.behaviours import Normalizable

from ..behaviours import Accessible, Externable
from ..storage import OverwriteStorage
from ..utils import CHAR_MAX_LENGTH, CHAR_MAX_LENGTH_LONG
from .managers import (
    CharacteristicaExManager,
    GroupManager,
    IndividualManager,
)

SUBJECT_TYPE_GROUP = "group"
SUBJECT_TYPE_INDIVIDUAL = "individual"

ADDITIVE_CHARACTERISTICA = ["disease", "abstinence"]


# ----------------------------------
# DataFile
# ----------------------------------
class DataFile(models.Model):
    """Table or figure from where the data comes from (png).

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
        """Return the name of the uploaded file."""
        return self.file.name

    def __str__(self):
        """Return the name of the uploaded file."""
        return self.file.name


# ----------------------------------
# Group
# ----------------------------------


class GroupSet(models.Model):
    """Collection of groups belonging to the group_exs of a study."""

    @property
    def groups(self):
        """Return all groups created from this set's group_exs."""
        return Group.objects.filter(ex__in=self.group_exs.all())

    @property
    def count(self):
        """Return the number of groups in this set, 0 if there are none."""
        if self.groups:
            return self.groups.count()
        return 0


class GroupEx(Externable):
    """Group (external curated layer).

    Groups are defined via their characteristica.
    A group can be a subgroup of another group via the parent field.
    """

    groupby = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)

    source = models.ForeignKey(
        DataFile, related_name="s_group_exs", null=True, on_delete=models.SET_NULL
    )
    image = models.ForeignKey(
        DataFile, related_name="i_group_exs", null=True, on_delete=models.SET_NULL
    )

    groupset = models.ForeignKey(
        GroupSet, on_delete=models.CASCADE, null=True, related_name="group_exs"
    )

    @property
    def study(self):
        """Return the study this group belongs to, via its group set."""
        return self.groupset.study

    @property
    def reference(self):
        """Return the reference of the study this group belongs to."""
        return self.study.reference


class Group(Accessible):
    """A group of subjects, defined by its characteristica and optionally a parent group."""

    ex = models.ForeignKey(
        GroupEx, related_name="groups", null=True, on_delete=models.CASCADE
    )

    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    count = models.IntegerField()
    parent = models.ForeignKey("Group", null=True, on_delete=models.CASCADE)
    characteristica_all_normed = models.ManyToManyField(
        "Characteristica", related_name="groups", through="GroupCharacteristica"
    )

    study = models.ForeignKey(
        "studies.Study", on_delete=models.CASCADE, related_name="groups"
    )

    objects = GroupManager()

    # class Meta:
    # todo: in validator unique_together = ('ex__groupset', 'name')

    @property
    def source(self):
        """Return the source data file of this group's external layer."""
        return self.ex.source

    @property
    def image(self):
        """Return the image data file of this group's external layer."""
        return self.ex.image

    @property
    def parents(self):
        """Return the primary keys of this group's parent and all its ancestors."""
        parents = []
        if self.parent:
            parents = [self.parent.pk, *self.parent.parents]
        return parents

    @property
    def _characteristica_all(self):
        _characteristica_all = self.characteristica.all()
        this_measurements = _characteristica_all.exclude(
            measurement_type__info_node__name__in=ADDITIVE_CHARACTERISTICA
        ).values_list("measurement_type", flat=True)
        if self.parent:
            _characteristica_all = (
                _characteristica_all
                | self.parent._characteristica_all.exclude(
                    measurement_type__in=this_measurements
                )
            )
        return _characteristica_all

    @property
    def _characteristica_all_normed(self):
        return self._characteristica_all.filter(normed=True)


# ----------------------------------
# Individual
# ----------------------------------
class IndividualSet(models.Model):
    """Collection of individuals belonging to the individual_exs of a study."""

    @property
    def individuals(self):
        """Return all individuals created from this set's individual_exs."""
        return Individual.objects.filter(ex__in=self.individual_exs.all())

    @property
    def count(self):
        """Return the number of individuals in this set, 0 if there are none."""
        if self.individuals:
            return self.individuals.count()
        return 0


class AbstractIndividual(models.Model):
    """Abstract base providing a name-based string representation for individuals."""

    class Meta:
        abstract = True

    def __str__(self):
        """Return the individual's name."""
        return self.name


class IndividualEx(Externable):
    """Individual (external curated layer).

    This contains maps and splittings. Individuals are defined via their
    characteristics, analogue to groups.
    """

    groupby = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    source = models.ForeignKey(
        DataFile, related_name="s_individual_exs", null=True, on_delete=models.SET_NULL
    )
    image = models.ForeignKey(
        DataFile, related_name="i_individual_exs", null=True, on_delete=models.SET_NULL
    )
    individualset = models.ForeignKey(
        IndividualSet, on_delete=models.CASCADE, related_name="individual_exs"
    )

    @property
    def study(self):
        """Return the study this individual belongs to, via its individual set."""
        return self.individualset.study

    @property
    def reference(self):
        """Return the reference of the study this individual belongs to."""
        return self.study.reference

    def groups_in_study(self):
        """Return the group_exs of the study this individual belongs to."""
        return self.study.groupset.group_exs


class Individual(AbstractIndividual, Accessible):
    """Single individual in data base.

    This does not contain any mappings are splits any more.
    """

    ex = models.ForeignKey(
        IndividualEx, related_name="individuals", null=True, on_delete=models.CASCADE
    )
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="individuals"
    )
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    characteristica_all_normed = models.ManyToManyField(
        "Characteristica",
        related_name="individuals",
        through="IndividualCharacteristica",
    )

    study = models.ForeignKey(
        "studies.Study", on_delete=models.CASCADE, related_name="individuals"
    )

    objects = IndividualManager()

    @property
    def source(self):
        """Return the source data file of this individual's external layer."""
        return self.ex.source

    @property
    def image(self):
        """Return the image data file of this individual's external layer."""
        return self.ex.image

    @property
    def _characteristica_normed(self):
        return self.characteristica.filter(normed=True)

    @property
    def _characteristica_all_normed(self):
        _characteristica_normed = self._characteristica_normed

        # charcteristica from related groups with the same measurement type as these used in the individual are excluded.
        # this_measurements = characteristica_normed.values_list("measurement_type", flat=True)
        this_measurements = _characteristica_normed.exclude(
            measurement_type__info_node__name__in=ADDITIVE_CHARACTERISTICA
        ).values_list("measurement_type", flat=True)
        return _characteristica_normed | self.group._characteristica_all_normed.exclude(
            measurement_type__in=this_measurements
        )

    @property
    def group_indexing(self):
        """Return the name of the group this individual belongs to."""
        return self.group.name

    @property
    def characteristica_measurements(self):
        """Return the measurement types of this individual's normed characteristica."""
        return [
            characteristica.measurement_type
            for characteristica in self.characteristica_all_normed.all()
        ]

    @property
    def characteristica_choices(self):
        """Map each normed characteristica's measurement type to its choice."""
        return {
            characteristica.measurement_type: characteristica.choice
            for characteristica in self.characteristica_all_normed.all()
        }


# ----------------------------------
# Characteristica
# ----------------------------------


class CharacteristicaEx(models.Model):
    """Characteristica  (external curated layer).

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
    """A single characteristic (age, weight, sex, ...) of a group or an individual."""

    group = models.ForeignKey(
        Group, related_name="characteristica", null=True, on_delete=models.CASCADE
    )
    individual = models.ForeignKey(
        Individual, related_name="characteristica", null=True, on_delete=models.CASCADE
    )
    count = models.IntegerField(default=1)

    @property
    def raw_pk(self):
        """Return the primary key of the raw (non-normed) characteristica, or None."""
        if self.raw:
            return self.raw.pk
        return None

    @property
    def study(self):
        """Return the study this characteristica belongs to, via its group or individual."""
        if self.group:
            return self.group.study
        return self.individual.study

    def study_name(self):
        """Return the name of the study this characteristica belongs to."""
        return self.study.name

    def study_sid(self):
        """Return the sid of the study this characteristica belongs to."""
        return self.study.sid

    @property
    def all_group_pks(self):
        """Return the primary keys of the group and all its ancestors, if set."""
        parents = []
        if self.group:
            parents = [self.group.pk, *self.group.parents]
        return parents

    @property
    def subject_type(self):
        """Return whether this characteristica belongs to a group or an individual."""
        if self.group:
            return SUBJECT_TYPE_GROUP
        return SUBJECT_TYPE_INDIVIDUAL

    @property
    def group_name(self):
        """Return the name of the group, or None if not set."""
        if self.group:
            return self.group.name
        return None

    @property
    def group_pk(self):
        """Return the primary key of the group, or None if not set."""
        if self.group:
            return self.group.pk
        return None

    @property
    def group_count(self):
        """Return the count of the group, or None if not set."""
        if self.group:
            return self.group.count
        return None

    @property
    def group_parent_pk(self):
        """Return the primary key of the group's parent, or None if not set."""
        if self.group and self.group.parent:
            return self.group.parent.pk
        return None

    @property
    def individual_name(self):
        """Return the name of the individual, or None if not set."""
        if self.individual:
            return self.individual.name
        return None

    @property
    def individual_pk(self):
        """Return the primary key of the individual, or None if not set."""
        if self.individual:
            return self.individual.pk
        return None

    @property
    def individual_group_pk(self):
        """Return the primary key of the individual's group, or None if not set."""
        if self.individual:
            return self.individual.group.pk
        return None


class SubjectCharacteristica(models.Model):
    """Abstract base exposing the fields of the related Characteristica on a subject."""

    class Meta:
        abstract = True

    @property
    def characteristica_pk(self):
        """Return the primary key of the related characteristica."""
        return self.characteristica.pk

    @property
    def raw_pk(self):
        """Return the primary key of the raw (non-normed) characteristica."""
        return self.characteristica.raw_pk

    @property
    def normed(self):
        """Return whether the related characteristica is normed."""
        return self.characteristica.normed

    @property
    def count(self):
        """Return the count of the related characteristica."""
        return self.characteristica.count

    @property
    def measurement_type(self):
        """Return the name of the related characteristica's measurement type."""
        return self.characteristica.measurement_type.info_node.name

    @property
    def calculation_type(self):
        """Return the name of the related characteristica's calculation type, or None."""
        if self.characteristica.calculation_type:
            return self.characteristica.calculation_type.info_node.name
        return None

    @property
    def choice(self):
        """Return the name of the related characteristica's choice, or None if not set."""
        if self.characteristica.choice:
            return self.characteristica.choice.info_node.name
        return None

    @property
    def substance(self):
        """Return the name of the related characteristica's substance, or None if not set."""
        if self.characteristica.substance:
            return self.characteristica.substance.info_node.name
        return None

    @property
    def unit(self):
        """Return the unit of the related characteristica."""
        return self.characteristica.unit

    @property
    def value(self):
        """Return the value of the related characteristica."""
        return self.characteristica.value

    @property
    def mean(self):
        """Return the mean of the related characteristica."""
        return self.characteristica.mean

    @property
    def median(self):
        """Return the median of the related characteristica."""
        return self.characteristica.median

    @property
    def min(self):
        """Return the minimum of the related characteristica."""
        return self.characteristica.min

    @property
    def max(self):
        """Return the maximum of the related characteristica."""
        return self.characteristica.max

    @property
    def sd(self):
        """Return the standard deviation of the related characteristica."""
        return self.characteristica.sd

    @property
    def se(self):
        """Return the standard error of the related characteristica."""
        return self.characteristica.se

    @property
    def cv(self):
        """Return the coefficient of variation of the related characteristica."""
        return self.characteristica.cv


class GroupCharacteristica(Accessible, SubjectCharacteristica):
    """Through model linking a group to one of its characteristica."""

    characteristica = models.ForeignKey(Characteristica, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("characteristica", "group")

    @property
    def study(self):
        """Return the study the group belongs to."""
        return self.group.study

    @property
    def group_pk(self):
        """Return the primary key of the group."""
        return self.group.pk

    @property
    def group_parent_pk(self):
        """Return the primary key of the group's parent, or None if not set."""
        if self.group.parent:
            return self.group.parent.pk
        return None

    @property
    def group_name(self):
        """Return the name of the group."""
        return self.group.name

    @property
    def group_count(self):
        """Return the count of the group."""
        return self.group.count


class IndividualCharacteristica(Accessible, SubjectCharacteristica):
    """Through model linking an individual to one of its characteristica."""

    characteristica = models.ForeignKey(Characteristica, on_delete=models.CASCADE)
    individual = models.ForeignKey(Individual, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("characteristica", "individual")

    @property
    def study(self):
        """Return the study the individual belongs to."""
        return self.individual.study

    @property
    def individual_pk(self):
        """Return the primary key of the individual."""
        return self.individual.pk

    @property
    def individual_name(self):
        """Return the name of the individual."""
        return self.individual.name

    @property
    def individual_group_pk(self):
        """Return the primary key of the individual's group."""
        return self.individual.group.pk

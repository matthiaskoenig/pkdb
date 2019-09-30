"""
Describe group of subjects or individual (i.e. define the characteristics of the
group or individual).

How is different from things which will be measured?
From the data structure this has to be handled very similar.
"""

from django.db import models
from ..storage import OverwriteStorage
from ..behaviours import (
    Externable, Accessible)

from pkdb_app.categorials.behaviours import Normalizable, ExMeasurementTypeable

from ..utils import CHAR_MAX_LENGTH, CHAR_MAX_LENGTH_LONG
from .managers import (
    GroupExManager,
    GroupSetManager,
    IndividualExManager,
    IndividualSetManager,
    IndividualManager,
    GroupManager,
    CharacteristicaExManager,
)

from django.apps import apps

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
    objects = GroupSetManager()

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
        DataFile, related_name="s_group_exs", null=True, on_delete=models.CASCADE
    )
    figure = models.ForeignKey(
        DataFile, related_name="f_group_exs", null=True, on_delete=models.CASCADE
    )
    groupset = models.ForeignKey(
        GroupSet, on_delete=models.CASCADE, null=True, related_name="group_exs"
    )

    parent_ex = models.ForeignKey("GroupEX", null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    name_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    count = models.IntegerField(null=True)
    count_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)

    objects = GroupExManager()

    @property
    def study(self):
        return self.groupset.study

    @property
    def reference(self):
        return self.study.reference

    class Meta:
        unique_together = ("groupset", "name", "name_map", "source")


class Group(Accessible):
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
    def study(self):
        return self.ex.groupset.study

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
    def characteristica_all(self):
        characteristica_all = self.characteristica.all()
        additive_characteristica = ["disease","abstinence"]
        this_measurements = characteristica_all.exclude(measurement_type__name__in=additive_characteristica).values_list("measurement_type", flat=True)
        if self.parent:
            characteristica_all = characteristica_all | self.parent.characteristica_all.exclude(measurement_type__in=this_measurements)
        return characteristica_all

    @property
    def characteristica_all_normed(self):
        return self.characteristica_all.filter(normed=True)



# ----------------------------------
# Individual
# ----------------------------------
class IndividualSet(models.Model):
    objects = IndividualSetManager()

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


class IndividualEx(Externable, AbstractIndividual):
    """ Individual (external curated layer).
    This contains maps and splittings.
    Individuals are defined via their characteristics, analogue to groups.
    """

    source = models.ForeignKey( DataFile, related_name="s_individual_exs", null=True, on_delete=models.CASCADE)
    figure = models.ForeignKey(DataFile, related_name="f_individual_exs", null=True, on_delete=models.CASCADE)
    individualset = models.ForeignKey(IndividualSet, on_delete=models.CASCADE, related_name="individual_exs")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="individual_exs", null=True)
    group_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    name = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    name_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)

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
    objects = IndividualManager()

    @property
    def source(self):
        return self.ex.source

    @property
    def figure(self):
        return self.ex.figure

    @property
    def characteristica_normed(self):
        return self.characteristica.filter(normed=True)

    @property
    def group_characteristica_normed(self):
        return self.group.characteristica_all_normed

    @property
    def characteristica_all_normed(self):
        characteristica_normed = self.characteristica_normed
        this_measurements = characteristica_normed.values_list("measurement_type", flat=True)

        return (characteristica_normed | self.group_characteristica_normed.exclude(measurement_type__in=this_measurements))

    @property
    def study(self):
        return self.ex.individualset.study

    @property
    def group_indexing(self):
        return self.group.name

    @property
    def characteristica_measurements(self):
        return [characteristica.measurement_type for characteristica in self.characteristica_all_normed.all()]

    @property
    def characteristica_choices(self):
        return {characteristica.measurement_type: characteristica.choice for characteristica in self.characteristica_all_normed.all()}


# ----------------------------------
# Characteristica
# ----------------------------------


class AbstractCharacteristica(models.Model):

    count = models.IntegerField(null=True)

    class Meta:
        abstract = True


class CharacteristicaEx(
    ExMeasurementTypeable,
    AbstractCharacteristica):
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

    count_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)

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


class Characteristica(Accessible, Normalizable, AbstractCharacteristica):
    """ Characteristic. """

    group = models.ForeignKey(
        Group, related_name="characteristica", null=True, on_delete=models.CASCADE
    )
    individual = models.ForeignKey(
        Individual, related_name="characteristica", null=True, on_delete=models.CASCADE
    )
    count = models.IntegerField(default=1)

    @property
    def study(self):
        if self.group:
            return self.group.study
        else:
            return self.individual.study

    @property
    def all_group_pks(self):
        parents = []
        if self.group:
            parents = [self.group.pk] + self.group.parents
        return parents

    @property
    def group_name(self):
        if self.group:
            return self.group.name

    @property
    def group_pk(self):
        if self.group:
            return self.group.pk

    @property
    def individual_name(self):
        if self.individual:
            return self.individual.name

    @property
    def individual_pk(self):
        if self.individual:
            return self.individual.pk

"""
Django model for Study.
"""
import datetime

from django.db import models
from pkdb_app.data.models import DataSet, Data

from pkdb_app.info_nodes.models import Substance, InfoNode
from pkdb_app.users.models import PUBLIC, PRIVATE
from ..behaviours import Sidable
from ..interventions.models import InterventionSet, DataFile, Intervention
from ..outputs.models import OutputSet, Output, OutputIntervention
from ..subjects.models import GroupSet, IndividualSet, Characteristica, Group, Individual
from ..users.models import User
from ..utils import CHAR_MAX_LENGTH, CHAR_MAX_LENGTH_LONG


CURRENT_VERSION = [1.0]
VERSIONS = [1.0]

# ---------------------------------------------------
# Study licence
# ---------------------------------------------------
OPEN = "open"
CLOSED = "closed"

STUDY_LICENCE_DATA = [
    OPEN,  # (open reference)
    CLOSED,
]

STUDY_LICENCE_CHOICES = [(t, t) for t in STUDY_LICENCE_DATA]

STUDY_ACCESS_DATA = [
    PUBLIC,
    PRIVATE
]
STUDY_ACCESS_CHOICES = [(t, t) for t in STUDY_ACCESS_DATA]


# ---------------------------------------------------
class Author(models.Model):
    """ Author in reference. """
    first_name = models.CharField(max_length=CHAR_MAX_LENGTH, blank=True)
    last_name = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, blank=True)

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)

from django.core.validators import RegexValidator
alphanumeric = RegexValidator(r'^[0-9a-zA-Z]*$', 'Only alphanumeric characters are allowed.')


class Reference(models.Model):
    """
    This is the main class describing the publication or reference which describes the study.
    In most cases this is a published paper, but could be a thesis or unpublished.
    """
    sid = models.CharField(max_length=CHAR_MAX_LENGTH, unique=True, validators=[alphanumeric])
    pmid = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, validators=[alphanumeric])  # optional
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    doi = models.CharField(max_length=150, null=True)  # optional
    title = models.TextField()
    abstract = models.TextField(null=True)
    journal = models.TextField(null=True)
    date = models.DateField()
    authors = models.ManyToManyField(Author, related_name="references")

    def __str__(self):
        return self.title

    # FIXME: Remove
    @property
    def study_pk(self):
        if self.study:
            return self.study.pk
        return ""

    @property
    def study_name(self):
        if self.study:
            return self.study.name
        return ""


class Rating(models.Model):
    """ Rating.

    Used to encode quality of curation status.
    """
    rating = models.FloatField(default=0)
    study = models.ForeignKey("Study", related_name="ratings", on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="ratings", on_delete=models.CASCADE)


class Study(Sidable, models.Model):
    """ A study containing PKDB information.

    Mainly reported as a single publication.
    """
    sid = models.CharField(max_length=CHAR_MAX_LENGTH, unique=True, validators=[alphanumeric])
    date = models.DateField(default=datetime.date.today)
    name = models.CharField(max_length=CHAR_MAX_LENGTH, unique=True)
    access = models.CharField(max_length=CHAR_MAX_LENGTH, choices=STUDY_ACCESS_CHOICES)

    reference = models.OneToOneField(
        Reference, on_delete=models.CASCADE, related_name="study", null=True
    )
    licence = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, choices=STUDY_LICENCE_CHOICES)
    creator = models.ForeignKey(
        User, related_name="creator_of_studies", on_delete=models.CASCADE, null=True
    )
    curators = models.ManyToManyField(
        User, related_name="curator_of_studies", through=Rating
    )
    collaborators = models.ManyToManyField(
        User, related_name="collaborator_of_studies"
    )
    groupset = models.OneToOneField(
        GroupSet, related_name="study", on_delete=models.SET_NULL, null=True
    )
    interventionset = models.OneToOneField(
        InterventionSet, related_name="study", on_delete=models.SET_NULL, null=True
    )
    individualset = models.OneToOneField(
        IndividualSet, related_name="study", on_delete=models.SET_NULL, null=True
    )
    outputset = models.OneToOneField(
        OutputSet, related_name="study", on_delete=models.SET_NULL, null=True
    )

    dataset = models.OneToOneField(
        DataSet, related_name="study", on_delete=models.SET_NULL, null=True
    )

    files = models.ManyToManyField(DataFile)


    class Meta:
        verbose_name_plural = "studies"

    def __unicode__(self):
        return '%s' % self.name

    def __str__(self):
        return '%s' % self.name

    @property
    def reference_date(self):
        return self.reference.date

    @property
    def individuals(self):
        try:
            return self.individualset.individuals.all()
        except AttributeError:
            return Individual.objects.none()

    @property
    def groups(self):
        try:
            return self.groupset.groups.all()
        except AttributeError:
            return Group.objects.none()

    @property
    def characteristica(self):
        empty_characteristica = Characteristica.objects.none()
        for group in self.groups.all():
            empty_characteristica = empty_characteristica.union(group.characteristica.all())
        for individual in self.individuals.all():
            empty_characteristica = empty_characteristica.union(individual.characteristica.all())

        return empty_characteristica

    @property
    def interventions(self):
        try:
            return self.interventionset.interventions.all()
        except AttributeError:
            return Intervention.objects.none()


    @property
    def outputs_interventions(self):
        try:
            return self.outputs.outputs_interventions.all()
        except AttributeError:
            return OutputIntervention.objects.none()

    @property
    def get_substances(self):
        """ Get all substances for given study.

        Substances are collected from interventions, outputs, timecourses.
        """
        all_substances = []
        basic_substances = []

        if self.interventions:
            all_substances.extend(
                list(self.interventions.filter(substance__isnull=False).values_list("substance__pk", flat=True))
            )

        if self.outputs:
            all_substances.extend(
                list(self.outputs.filter(substance__isnull=False).values_list("substance__pk", flat=True))
            )

        substances_dj = Substance.objects.filter(pk__in=set(all_substances))

        basic_substances_dj = substances_dj.filter(info_node__parents__isnull=True)
        if basic_substances_dj:
            basic_substances.extend(list(basic_substances_dj.values_list("info_node__pk", flat=True)))

        substances_derived_dj = substances_dj.filter(info_node__parents__isnull=False)
        if substances_derived_dj:
            basic_substances.extend(
                list(substances_derived_dj.values_list("info_node__parents__pk", flat=True))
            )

        return InfoNode.objects.filter(pk__in=set(basic_substances))

    @property
    def files_url(self):
        return [file.file.name for file in self.files.all()]

    @property
    def files_ordered(self):
        return self.files.all().order_by("file")

    @property
    def reference_name(self):
        return self.reference.name

    @property
    def reference_pk(self):
        return self.reference.pk

    @property
    def group_count(self):
        if self.groupset:
            return self.groupset.groups.count()
        return 0

    @property
    def individual_count(self):
        if self.individualset:
            return self.individualset.individuals.count()
        return 0

    @property
    def intervention_count(self):
        if self.interventionset:
            return self.interventionset.interventions.filter(normed=True).count()
        return 0

    @property
    def output_count(self):
        return self.outputs.filter(normed=True).count()

    @property
    def output_calculated_count(self):
        return self.outputs.filter(normed=True, calculated=True).count()

    @property
    def subset_count(self):
        return self.subsets.count()

    @property
    def timecourse_count(self):
        return self.subsets.filter(data__data_type=Data.DataTypes.Timecourse).count()

    @property
    def scatter_count(self):
        return self.subsets.filter(data__data_type=Data.DataTypes.Scatter).count()

    def delete(self, *args, **kwargs):
        if self.outputset:
            self.outputset.delete()
        if self.dataset:
            self.dataset.delete()
        if self.interventionset:
            self.interventionset.delete()
        if self.individualset:
            self.individualset.delete()
        if self.groupset:
            self.groupset.delete()
        if self.reference:
            self.reference.delete()
        super().delete(*args, **kwargs)


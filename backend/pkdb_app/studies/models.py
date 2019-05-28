"""
Django model for Study.
"""
from django.db import models
from pkdb_app.users.models import PUBLIC, PRIVATE

from ..categorials.models import Keyword
from ..outputs.models import OutputSet

from ..interventions.models import InterventionSet, DataFile
from ..substances.models import Substance

from ..storage import OverwriteStorage
from ..subjects.models import GroupSet, IndividualSet
from ..utils import CHAR_MAX_LENGTH, CHAR_MAX_LENGTH_LONG
from ..behaviours import Sidable
from ..users.models import User

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
#
# ---------------------------------------------------


class Author(models.Model):
    """ Author in reference. """
    first_name = models.CharField(max_length=CHAR_MAX_LENGTH, blank=True)
    last_name = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, blank=True)

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)


class Reference(models.Model):
    """
    This is the main class describing the publication or reference which describes the study.
    In most cases this is a published paper, but could be a thesis or unpublished.
    """
    sid = models.CharField(max_length=CHAR_MAX_LENGTH, unique=True)
    pmid = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)  # optional
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    doi = models.CharField(max_length=150, null=True)  # optional
    title = models.TextField()
    abstract = models.TextField(null=True)
    journal = models.TextField(null=True)
    date = models.DateField()
    pdf = models.FileField(upload_to="study", storage=OverwriteStorage(), null=True)
    authors = models.ManyToManyField(Author, related_name="references")

    def __str__(self):
        return self.title



    @property
    def study_pk(self):
        if self.study:
            return self.study.pk
        else:
            return ""

    @property
    def study_name(self):
        if self.study:
            return self.study.name
        else:
            return ""


class Rating(models.Model):
    """ General rating model.

    Used for quality of curation status.
    """
    rating = models.FloatField(default=0)
    study = models.ForeignKey("Study", related_name="ratings", on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="ratings", on_delete=models.CASCADE)


class Study(Sidable, models.Model):
    """ Single clinical study.

    Mainly reported as a single publication.
    """

    sid = models.CharField(max_length=CHAR_MAX_LENGTH, unique=True)
    pkdb_version = models.IntegerField(default=CURRENT_VERSION)

    creator = models.ForeignKey(
        User, related_name="creator_of_studies", on_delete=models.CASCADE, null=True
    )

    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    reference = models.OneToOneField(
        Reference, on_delete=models.CASCADE, related_name="study", null=True
    )
    curators = models.ManyToManyField(User,related_name="curator_of_studies", through=Rating)
    collaborators = models.ManyToManyField(User,related_name="collaborator_of_studies")

    substances = models.ManyToManyField(Substance, related_name="studies")
    keywords = models.ManyToManyField(Keyword, related_name="studies")

    groupset = models.OneToOneField(GroupSet,related_name="study", on_delete=models.SET_NULL, null=True)
    interventionset = models.OneToOneField(
        InterventionSet, related_name="study",on_delete=models.SET_NULL, null=True
    )
    individualset = models.OneToOneField(
        IndividualSet,related_name="study", on_delete=models.SET_NULL, null=True
    )
    outputset = models.OneToOneField(OutputSet,related_name="study", on_delete=models.SET_NULL, null=True)
    files = models.ManyToManyField(DataFile)

    licence = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, choices=STUDY_LICENCE_CHOICES)
    access = models.CharField(max_length=CHAR_MAX_LENGTH, choices=STUDY_ACCESS_CHOICES)

    class Meta:
        verbose_name_plural = "studies"

    def __unicode__(self):
        return '%s' % self.name

    def __str__(self):
        return '%s' % self.name

    @property
    def individuals(self):
        try:
            return self.individualset.individuals.all()
        except AttributeError:
            return []

    @property
    def groups(self):
        try:
            return self.groupset.groups.all()
        except AttributeError:
            return []

    @property
    def interventions(self):
        try:
            return self.interventionset.interventions.all()
        except AttributeError:
            return []

    @property
    def outputs(self):
        try:
            return self.outputset.outputs.all()
        except AttributeError:
            return []

    @property
    def timecourses(self):
        try:
            return self.outputset.timecourses.all()
        except AttributeError:
            return []

    def get_substances(self):
        """Get all substances for given study.
        Substances are collected from
        - interventions
        - outputs
        - timecourses

        """

        all_substances = []
        basic_substances = []

        # todo: add characteristica substance

        if self.interventions:
            all_substances.extend(list(self.interventions.filter(substance__isnull=False).values_list("substance__pk", flat=True)))

        if self.outputs:
            all_substances.extend(list(self.outputs.filter(substance__isnull=False).values_list("substance__pk", flat=True)))

        if self.timecourses:
            all_substances.extend(list(self.timecourses.filter(substance__isnull=False).values_list("substance__pk", flat=True)))

        substances_dj = Substance.objects.filter(pk__in=set(all_substances))

        basic_substances_dj = substances_dj.filter(parents__isnull=True)
        if basic_substances_dj:
            basic_substances.extend(list(basic_substances_dj.values_list("pk", flat=True)))

        substances_derived_dj = substances_dj.filter(parents__isnull=False)
        if substances_derived_dj:
            basic_substances.extend(list(substances_derived_dj.values_list("parents__pk",flat=True)))

        return set(basic_substances)


    @property
    def substances_name(self):
        return [substance.name for substance in self.substances.all()]

    @property
    def files_url(self):
        return [file.file.name for file in self.files.all()]

    @property
    def keywords_name(self):
        return [keyword.name for keyword in self.keywords.all()]

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
    def timecourse_count(self):
        if self.outputset:
            return self.outputset.timecourses.filter(normed=True).count()
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
        if self.outputset:
            return self.outputset.outputs.filter(normed=True).count()

        return 0


    @property
    def output_calculated_count(self):
        if self.outputset:
            return self.outputset.outputs.filter(normed=True, calculated=True).count()

        return 0




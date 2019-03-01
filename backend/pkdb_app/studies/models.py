"""
Django model for Study.
"""
from django.db import models

from ..interventions.models import (
    OutputSet,
    InterventionSet,
    DataFile,
    Substance,
)
from ..storage import OverwriteStorage
from ..subjects.models import GroupSet, IndividualSet
from ..utils import CHAR_MAX_LENGTH
from ..behaviours import Sidable, CHAR_MAX_LENGTH_LONG
from ..categoricals import CURRENT_VERSION, KEYWORDS_DATA_CHOICES, STUDY_LICENCE_CHOICES
from ..users.models import User


class Keyword(models.Model):
    """
    This class describes the keywords / tags of a study.
    """
    name = models.CharField(max_length=CHAR_MAX_LENGTH, choices=KEYWORDS_DATA_CHOICES)


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
    pmid = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)  # optional
    sid = models.CharField(max_length=CHAR_MAX_LENGTH, primary_key=True)
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
    def id(self):
        return self.pk
    @property
    def study_pk(self):
        if self.study.first():
            return self.study.first().pk
        else:
            return ""

    @property
    def study_name(self):
        if self.study.first():
            return self.study.first().name
        else:
            return ""

class Rating(models.Model):
    """ General rating model.

    Used for quality of curation status.
    """
    rating = models.FloatField(default=0)
    study = models.ForeignKey("Study",related_name="ratings", on_delete=models.CASCADE)
    user = models.ForeignKey(User,related_name="ratings", on_delete=models.CASCADE)


class Study(Sidable, models.Model):
    """ Single clinical study.

    Mainly reported as a single publication.
    """
    pkdb_version = models.IntegerField(default=CURRENT_VERSION)

    creator = models.ForeignKey(
        User, related_name="creator_of_studies", on_delete=models.CASCADE, null=True
    )

    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    reference = models.ForeignKey(
        Reference, on_delete=True, related_name="study", null=True
    )
    curators = models.ManyToManyField(User,related_name="curator_of_studies", through=Rating)

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

    class Meta:
        verbose_name_plural = "studies"

    def __unicode__(self):
        return '%s' % (self.name)

    def __str__(self):
        return '%s' % (self.name)

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
        #substances = self.substances.values_list("pk",flat=True)
        substances = Substance.objects.none()

        if self.interventions:
            substances2 = self.interventions.filter(substance__isnull=False).values_list("substance",flat=True)
            substances = substances.union(substances2)

        if self.outputs:
            substances2 = self.outputs.filter(substance__isnull=False).values_list("substance", flat=True)
            substances = substances.union(substances2)

        if self.timecourses:
            substances2 = self.timecourses.filter(substance__isnull=False).values_list("substance", flat=True)
            substances = substances.union(substances2).distinct()

        return substances

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



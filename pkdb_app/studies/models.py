"""
Django model for Study.
"""
from django.db import models

from pkdb_app.interventions.models import (
    OutputSet,
    Substance,
    InterventionSet,
    DataFile,
)
from pkdb_app.storage import OverwriteStorage
from pkdb_app.subjects.models import GroupSet, IndividualSet
from ..utils import CHAR_MAX_LENGTH
from ..behaviours import Sidable, CHAR_MAX_LENGTH_LONG
from ..categoricals import STUDY_DESIGN_CHOICES, CURRENT_VERSION, KEYWORDS_DATA_CHOICES
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


class Study(Sidable, models.Model):
    """ Single clinical study.

    Mainly reported as a single publication.
    """

    pkdb_version = models.IntegerField(default=CURRENT_VERSION)
    creator = models.ForeignKey(
        User, related_name="creator_of_studies", on_delete=models.CASCADE, null=True
    )
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    design = models.CharField(
        max_length=CHAR_MAX_LENGTH, null=True, choices=STUDY_DESIGN_CHOICES
    )
    reference = models.ForeignKey(
        Reference, on_delete=True, related_name="study", null=True
    )
    curators = models.ManyToManyField(User, related_name="curator_of_studies")
    substances = models.ManyToManyField(Substance, related_name="studies")
    keywords = models.ManyToManyField(Keyword, related_name="studies")

    groupset = models.OneToOneField(GroupSet, on_delete=models.SET_NULL, null=True)
    interventionset = models.OneToOneField(
        InterventionSet, on_delete=models.SET_NULL, null=True
    )
    individualset = models.OneToOneField(
        IndividualSet, on_delete=models.SET_NULL, null=True
    )
    outputset = models.OneToOneField(OutputSet, on_delete=models.SET_NULL, null=True)
    files = models.ManyToManyField(DataFile)

    @property
    def individuals(self):
        return self.individualset.individual_exs.individuals.all()

    @property
    def groups(self):
        return self.groupset.group_exs.groups.all()

    @property
    def interventions(self):
        return self.interventionset.intervention_exs.interventions.all()

    @property
    def outputs(self):
        return self.outputset.output_exs.outputs.all()

    @property
    def timecourses(self):
        return self.outputset.timecourse_exs.timecourses.all()

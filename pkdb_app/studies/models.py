"""
Django model for Study.
"""
from django.db import models

from pkdb_app.interventions.models import OutputSet, Substance, InterventionSet, DataFile
from pkdb_app.storage import OverwriteStorage
from pkdb_app.subjects.models import GroupSet, IndividualSet
from ..utils import CHAR_MAX_LENGTH
from ..behaviours import Sidable
from ..categoricals import STUDY_DESIGN_CHOICES, CURRENT_VERSION
from ..users.models import User


class Author(models.Model):
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)


class Reference(models.Model):
    """
    This is the main class describing the publication or reference which describes the study.
    In most cases this is a published paper, but could be a thesis or unpublished.
    """
    pmid = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True) #optional
    sid = models.CharField(max_length=CHAR_MAX_LENGTH, primary_key=True)
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    doi = models.CharField(max_length=150, null=True, blank=True) #optional
    title = models.TextField()
    abstract = models.TextField(blank=True, null=True)
    journal = models.TextField(blank=True, null=True)
    date = models.DateField()
    pdf = models.FileField(upload_to="study",storage=OverwriteStorage(), null=True, blank=True)
    authors = models.ManyToManyField(Author, blank=True, related_name='references')

    def __str__(self):
        return self.title


class Study(Sidable, models.Model):
    """ Single clinical study.

    Mainly reported as a single publication.
    """
    pkdb_version = models.IntegerField(default=CURRENT_VERSION)
    creator =  models.ForeignKey(User,related_name="studies",on_delete=False,null=True, blank=True)  # any creator needs an account.
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    design = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True, choices=STUDY_DESIGN_CHOICES)
    reference = models.ForeignKey(Reference, on_delete=True, to_field="sid", db_column="reference_sid", related_name='studies', null=True, blank=True)
    curators = models.ManyToManyField(User)  # any curator needs an account.
    substances = models.ManyToManyField(Substance)
    groupset = models.OneToOneField(GroupSet, on_delete=models.CASCADE,null=True, blank=True)
    interventionset = models.OneToOneField(InterventionSet, on_delete=models.CASCADE,null=True, blank=True)
    individualset = models.OneToOneField(IndividualSet, on_delete=models.CASCADE,null=True, blank=True)
    outputset = models.OneToOneField(OutputSet, on_delete=models.CASCADE,null=True, blank=True)
    files = models.ManyToManyField(DataFile)


# not yet used
class KeyWord(models.Model):
    """
    This class describes the keyowrds / tags of a  publication or any other reference.
    """
    #name = models.IntegerField(choices=KEY_WORD_CHOICES)
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
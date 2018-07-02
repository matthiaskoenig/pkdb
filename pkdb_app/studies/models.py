"""
Django model for Study.
"""
from django.db import models
from pkdb_app.utils import CHAR_MAX_LENGTH
from pkdb_app.behaviours import Sidable, Describable, Commentable
from pkdb_app.categoricals import INTERVENTION_CHOICES


class Author(models.Model):
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)

class Files(models.Model):
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    file = models.FileField(null=True, blank=True)

class KeyWord(models.Model):
    """
    This class describes the keyowrds / tags of a  publication or any other reference.
    """
    #name = models.IntegerField(choices=KEY_WORD_CHOICES)
    name = models.CharField(max_length=CHAR_MAX_LENGTH)

# All models should be commentable

class Reference(models.Model):
    """
    This is the main class describing the publication or reference which describes the study.
    In most cases this is a published paper, but could be a thesis or unpublished.
    """

    pmid = models.CharField(max_length=CHAR_MAX_LENGTH) #optional
    doi = models.CharField(max_length=CHAR_MAX_LENGTH) #optional
    title = models.TextField()
    abstract = models.TextField(blank=True, null=True)
    journal = models.CharField(max_length=CHAR_MAX_LENGTH)
    year = models.DateField()
    pdf = models.FileField(upload_to="study", null=True, blank=True)
    authors = models.ManyToManyField(Author, blank=True, related_name='authors')

class Study(Sidable, Commentable, Describable, models.Model):
    """ Single clinical study.

    Mainly reported as a single publication.

    """
    # sid should be the AuthorYear if possible
    # comments
    #description (if no description is provided, this is filled with the abstract)
    #files (PNG, CSV) (all files with exception of pdf)
    files = models.ManyToManyField(Files, related_name="files")
    reference = models.ForeignKey(Reference, null=True, blank=True, on_delete=True)
    keywords = models.ManyToManyField(KeyWord, blank=True, related_name='keywords')

    #interventions
    #subjects



# -------------------------------------------------
# Intervention
# -------------------------------------------------
# Here only the different (two or more) groups which were compared in the study have to be defined.
# In a single study/paper multiple groups are compared (these can be defined as groups).


# class Intervention(Sidable, Commentable, Describable, models.Model):
#    type = models.IntegerField(choices=INTERVENTION_CHOICES)
#    study = models.ForeignKey(Study, null=True, blank=True, on_delete=True)


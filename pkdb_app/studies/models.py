"""
Django model for Study.
"""
from django.db import models
from pkdb_app.utils import CHAR_MAX_LENGTH
from pkdb_app.behaviours import Sidable, Describable, Commentable
from pkdb_app.categoricals import STUDY_DESIGN_CHOICES


class Author(models.Model):
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return '%s %s' % (self.id, self.first_name, self.last_name)


class Files(models.Model):
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    file = models.FileField(null=True, blank=True)


class KeyWord(models.Model):
    """
    This class describes the keyowrds / tags of a  publication or any other reference.
    """
    #name = models.IntegerField(choices=KEY_WORD_CHOICES)
    name = models.CharField(max_length=CHAR_MAX_LENGTH)


class Reference(models.Model):
    """
    This is the main class describing the publication or reference which describes the study.
    In most cases this is a published paper, but could be a thesis or unpublished.
    """
    pmid = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True) #optional
    sid = models.CharField(max_length=CHAR_MAX_LENGTH, primary_key=True, default=pmid)
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    doi = models.CharField(max_length=150, null=True, blank=True) #optional
    title = models.TextField()
    abstract = models.TextField(blank=True, null=True)
    journal = models.TextField(blank=True, null=True)
    date = models.DateField()
    pdf = models.FileField(upload_to="study", null=True, blank=True)
    authors = models.ManyToManyField(Author, blank=True, related_name='references')


class Study(Sidable, Commentable, Describable, models.Model):
    """ Single clinical study.

    Mainly reported as a single publication.
    """
    reference = models.ForeignKey(Reference, on_delete=True, to_field="sid", db_column="reference_sid", related_name='studies', null=True, blank=True)
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    design = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True, choices=STUDY_DESIGN_CHOICES)

    # TODO: substances, e.g. caffeine, acetaminophen
    # TODO: datafiles (DataFile)


# TODO: substances here


class DataFile(models.Model):
    """ Table or figure from where the data comes from (png).

    This should be in a separate class, so that they can be easily displayed/filtered/...
    """
    file = models.FileField(upload_to="output", null=True, blank=True)  # table or figure
    filetype # XLSX, PNG, CSV
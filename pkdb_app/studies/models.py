"""
Django model for Study.
"""
from django.db import models
from .utils import CHAR_MAX_LENGTH
from pkdb_app.behaviours import Sidable, Describable, Commentable
from pkdb_app.choices import INTERVENTION_CHOICES


class Author(models.Model):
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)


class Study(Commentable, Describable, models.Model):
    """ Single clinical study.

    Mainly reported as a single publication.
    """


    title = models.TextField()
    pmid = models.CharField(max_length=CHAR_MAX_LENGTH)
    abstract = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="study", null=True, blank=True)
    authors = models.ManyToManyField(Author, blank=True, related_name='authors')


class Intervention(Sidable, Commentable, Describable, models.Model):
    type = models.IntegerField(choices=INTERVENTION_CHOICES)
    study = models.ForeignKey(Study, null=True, blank=True, on_delete=True)


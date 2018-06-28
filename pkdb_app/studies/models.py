from django.db import models
from .utils import CHAR_MAX_LENGTH
from .behaviours import Sidable, Describable, Commentable
from .choices import INTERVENTION_CHOICES


class Author(models.Model):
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)


class Study(Sidable, Commentable, Describable, models.Model):
    title = models.CharField(max_length=CHAR_MAX_LENGTH)
    pmid = models.CharField(max_length=CHAR_MAX_LENGTH)
    authors = models.ManyToManyField(Author, blank=True)
    file = models.FileField(upload_to="study", null=True, blank=True)


class Intervention(Sidable, Commentable, Describable, models.Model):
    type = models.IntegerField(choices=INTERVENTION_CHOICES)
    study = models.ForeignKey(Study, null=True, blank=True, on_delete=True)


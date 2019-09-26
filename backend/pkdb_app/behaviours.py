"""
Reusable behavior for models.
"""
from django.contrib.auth import get_user_model
from django.db import models
from .utils import CHAR_MAX_LENGTH_LONG, CHAR_MAX_LENGTH



class Sidable(models.Model):
    """ Model has an sid. """
    sid = models.CharField(max_length=CHAR_MAX_LENGTH, primary_key=True)

    class Meta:
        abstract = True

class Externable(models.Model):
    #format = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    subset_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    groupby = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)

    class Meta:
        abstract = True


class Accessible(models.Model):
    class Meta:
        abstract = True

    @property
    def access(self):
        return self.study.access

    @property
    def allowed_users(self):
        creator = self.study.creator
        creator_queryset = get_user_model().objects.filter(id=creator.id)
        curators = self.study.curators.all()
        collaborators = self.study.collaborators.all()
        return collaborators.union(curators).union(creator_queryset)

    @property
    def study_name(self):
        return self.study.name

    @property
    def study_pk(self):
        return self.study.pk



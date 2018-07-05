"""
Reusable behavior for models.
"""

from django.db import models
from pkdb_app.utils import CHAR_MAX_LENGTH


class Sidable(models.Model):
    """ Model has an sid. """
    sid = models.CharField(max_length=CHAR_MAX_LENGTH)

    class Meta:
        abstract = True


# FIXME: This has to be more complicated.
'''
- multiple users can comment and every comment should be tracked to user with provenance information like
  timestamp (last modified)

    Comment(model):
       text
       user
       timestamp

- Annotation (annotatable), at some point, but not now
'''



class Commentable(models.Model):
    """ Model has a comment field. """
    comment = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True


class Describable(models.Model):
    """

    """
    description = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True

class Hashable(models.Model):
    hash = models.CharField(max_length=CHAR_MAX_LENGTH,blank=True, null=True)

    class Meta:
        abstract = True
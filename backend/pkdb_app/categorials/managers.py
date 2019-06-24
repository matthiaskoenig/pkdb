from django.db import models
from pkdb_app.utils import update_or_create_multiple


class ChoiceManager(models.Manager):
    def create(self, *args, **kwargs):
        annotations = kwargs.pop('annotations', [])
        choice = super().create(*args, **kwargs)
        update_or_create_multiple(choice, annotations, 'annotations', lookup_fields=["term","relation"])
        choice.save()
        return choice

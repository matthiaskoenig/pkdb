from django.db import models
from pkdb_app.utils import update_or_create_multiple


class AnnotatableManager(models.Manager):
    def create(self, *args, **kwargs):
        annotations = kwargs.pop('annotations', [])
        instance = super().create(*args, **kwargs)
        update_or_create_multiple(instance, annotations, 'annotations', lookup_fields=["term", "relation"])
        instance.save()
        return instance

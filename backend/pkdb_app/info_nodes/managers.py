from django.db import models
from pkdb_app.utils import update_or_create_multiple


class InfoNodeManager(models.Manager):
    def update_or_create(self, *args, **kwargs):

        annotations = kwargs.pop('annotations', [])
        parents = kwargs.pop('parents', [])
        synonyms = kwargs.pop('synonyms', [])


        instance = super().create(*args, **kwargs)

        update_or_create_multiple(instance, annotations, 'annotations', lookup_fields=["term", "relation"])
        update_or_create_multiple(instance, synonyms, 'synonyms', lookup_fields=["name"])
        update_or_create_multiple(instance, parents, 'parents', lookup_fields=["name"])

        instance.save()
        return instance
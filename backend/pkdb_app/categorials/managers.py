from django.db import models
from pkdb_app.utils import update_or_create_multiple


class AnnotatableManager(models.Manager):
    def create(self, *args, **kwargs):
        annotations = kwargs.pop('annotations', [])
        synonyms = kwargs.pop('synonyms', [])

        instance = super().create(*args, **kwargs)
        if synonyms:
            print("*" * 100)
            print("here I am")
            print(synonyms)
            print("*" * 100)
        update_or_create_multiple(instance, annotations, 'annotations', lookup_fields=["term", "relation"])
        update_or_create_multiple(instance, synonyms, 'synonyms', lookup_fields=["name"])

        instance.save()
        return instance

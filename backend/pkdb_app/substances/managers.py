"""
the managers can be used to overwrite class methods of the models module.
"""
from django.db import models


class SubstanceManager(models.Manager):
    def update_or_create(self, *args, **kwargs):
        parents = kwargs["defaults"].pop('parents', [])
        synonyms = kwargs["defaults"].pop('synonyms', [])
        substance, created = super().update_or_create(*args, **kwargs)
        substance.parents.add(*parents)
        substance.synonyms.add(*synonyms)
        substance.save()
        return substance

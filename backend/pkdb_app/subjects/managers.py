"""
the managers can be used to overwrite class methods of the models module.
"""
from django.apps import apps
from django.db import models

from pkdb_app.utils import create_multiple, create_multiple_bulk, create_multiple_bulk_normalized



class GroupManager(models.Manager):
    def create(self, *args, **kwargs):
        characteristica = kwargs.pop("characteristica", [])
        study_groups = kwargs.pop("study_groups")

        if kwargs.get("parent"):
            kwargs["parent"] = self.model.objects.filter(pk__in=study_groups).get(name=kwargs.get("parent"))

        group = super().create(*args, **kwargs)
        characteristica_updated = []
        Characteristica = apps.get_model('subjects', 'Characteristica')

        for characteristica_single in characteristica:
            characteristica_single["count"] = characteristica_single.get("count", group.count)
            characteristica_updated.append(characteristica_single)

        not_norm_group = create_multiple_bulk(group, "group", characteristica_updated, Characteristica)
        create_multiple_bulk_normalized(not_norm_group, Characteristica)

        group.save()
        return group


class CharacteristicaExManager(models.Manager):
    def create(self, *args, **kwargs):
        comments = kwargs.pop("comments", [])
        descriptions = kwargs.pop("descriptions", [])
        instance = super().create(*args, **kwargs)
        create_multiple(instance, comments, "comments")
        create_multiple(instance, descriptions, "descriptions")
        instance.save()
        return instance



class IndividualManager(models.Manager):
    def create(self, *args, **kwargs):
        characteristica = kwargs.pop("characteristica", [])
        individual = super().create(*args, **kwargs)
        Characteristica = apps.get_model('subjects', 'Characteristica')
        not_norm_individual = create_multiple_bulk(individual, "individual", characteristica, Characteristica)
        create_multiple_bulk_normalized(not_norm_individual, Characteristica)
        individual.save()
        return individual

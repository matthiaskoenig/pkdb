"""
the managers can be used to overwrite class methods of the models module.
"""
from django.apps import apps
from django.db import models

from pkdb_app.utils import create_multiple, create_multiple_bulk, create_multiple_bulk_normalized


class GroupExManager(models.Manager):
    def create(self, *args, **kwargs):
        characteristica_ex = kwargs.pop("characteristica_ex", [])
        groups = kwargs.pop("groups", [])
        study_groups = kwargs.pop("study_groups", [])

        comments = kwargs.pop("comments", [])
        descriptions = kwargs.pop("descriptions", [])

        group_ex = super().create(*args, **kwargs)
        for characteristica_ex_single in characteristica_ex:
            characteristica_ex_single["count"] = characteristica_ex_single.get(
                "count", group_ex.count
            )
            group_ex.characteristica_ex.create(**characteristica_ex_single)

        for group in groups:
            group["study_groups"] = study_groups
            dj_group = group_ex.groups.create(**group)
            study_groups.add(dj_group.pk)

        create_multiple(group_ex, comments, "comments")
        create_multiple(group_ex, descriptions, "descriptions")

        group_ex.save()
        return group_ex


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


class IndividualExManager(models.Manager):
    def create(self, *args, **kwargs):
        characteristica_ex = kwargs.pop("characteristica_ex", [])
        individuals = kwargs.pop("individuals", [])
        comments = kwargs.pop("comments", [])
        descriptions = kwargs.pop("descriptions", [])

        comment_model = apps.get_model('comments', 'Comment')
        description_model = apps.get_model('comments', 'Description')

        individual_ex = super().create(*args, **kwargs)

        create_multiple(individual_ex, characteristica_ex, "characteristica_ex")
        create_multiple(individual_ex, individuals, "individuals")

        # create_multiple(individual_ex, comments, "comments")
        create_multiple_bulk(individual_ex, "ex", comments, comment_model)
        create_multiple_bulk(individual_ex, "ex", descriptions, description_model)

        individual_ex.save()
        return individual_ex


class IndividualManager(models.Manager):
    def create(self, *args, **kwargs):
        characteristica = kwargs.pop("characteristica", [])
        individual = super().create(*args, **kwargs)
        Characteristica = apps.get_model('subjects', 'Characteristica')
        not_norm_individual = create_multiple_bulk(individual, "individual", characteristica, Characteristica)
        create_multiple_bulk_normalized(not_norm_individual, Characteristica)
        individual.save()
        return individual

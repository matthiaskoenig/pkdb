"""
the managers can be used to overwrite class methods of the models module.
"""
from django.db import models
from django.apps import apps
from pkdb_app.utils import create_multiple, create_multiple_bulk, create_multiple_bulk_normalized


class GroupSetManager(models.Manager):
    def create(self, *args, **kwargs):
        study = kwargs.pop("study")
        group_exs = kwargs.pop("group_exs", [])

        descriptions = kwargs.pop("descriptions", [])
        comments = kwargs.pop("comments", [])
        groupset = super().create(*args, **kwargs)
        create_multiple(groupset, descriptions, "descriptions")
        create_multiple(groupset, comments, "comments")

        study_group_exs = []
        for group_ex in group_exs:
            if "parent_ex" in group_ex:
                for study_group_ex in study_group_exs:
                    if study_group_ex.name == group_ex["parent_ex"]:
                        group_ex["parent_ex"] = study_group_ex

            # create single group_ex
            group_ex["study"] = study
            group_ex["group_exs"] = study_group_exs

            study_group_ex = groupset.group_exs.create(**group_ex)

            study_group_exs.append(study_group_ex)

        groupset.save()

        # add characteristica from parents to the all_characteristica_normed if each group
        for group in groupset.groups:
            group.characteristica_all_normed.add(*group._characteristica_all_normed)

        return groupset


class GroupExManager(models.Manager):
    def create(self, *args, **kwargs):
        characteristica_ex = kwargs.pop("characteristica_ex", [])
        groups = kwargs.pop("groups", [])
        study = kwargs.pop("study")
        group_exs = kwargs.pop("group_exs")
        comments = kwargs.pop("comments", [])
        descriptions = kwargs.pop("descriptions", [])

        group_ex = super().create(*args, **kwargs)
        for characteristica_ex_single in characteristica_ex:
            characteristica_ex_single["count"] = characteristica_ex_single.get(
                "count", group_ex.count
            )
            group_ex.characteristica_ex.create(**characteristica_ex_single)

        for group in groups:
            group["study"] = study
            group["group_exs"] = group_exs
            group_ex.groups.create(**group)

        create_multiple(group_ex, comments, "comments")
        create_multiple(group_ex, descriptions, "descriptions")

        group_ex.save()
        return group_ex


class GroupManager(models.Manager):
    def create(self, *args, **kwargs):
        kwargs.pop("study")
        characteristica = kwargs.pop("characteristica", [])
        group_exs = kwargs.pop("group_exs")

        if kwargs.get("parent"):
            for group_ex in group_exs:
                if group_ex.name == kwargs["parent"]:
                    ex = group_ex
            kwargs["parent"] = self.model.objects.get(name=kwargs.get("parent"), ex=ex)

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


class IndividualSetManager(models.Manager):

    def create(self, *args, **kwargs):
        individual_exs = kwargs.pop("individual_exs", [])
        descriptions = kwargs.pop("descriptions", [])
        kwargs.pop("study")
        comments = kwargs.pop("comments", [])

        Comment = apps.get_model('comments', 'Comment')
        Description = apps.get_model('comments', 'Description')

        individualset = super().create(*args, **kwargs)

        # create_multiple(individualset, descriptions, "descriptions")
        # create_multiple_bulk(individualset,"individualset", individual_exs, IndividualEx)
        create_multiple(individualset, individual_exs, "individual_exs")
        create_multiple_bulk(individualset, "individualset", descriptions, Description)
        create_multiple_bulk(individualset, "individualset", comments, Comment)
        individualset.save()

        # add characteristica from parents to the all_characteristica_normed if each individual
        for individual in individualset.individuals:
            # print(individual._characteristica_all_normed.all())
            individual.characteristica_all_normed.add(*individual._characteristica_all_normed)
        return individualset


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

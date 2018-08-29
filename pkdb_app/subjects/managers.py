"""
the managers can be used to overwrite class methods of the models module.
"""
from django.db import models

from pkdb_app.utils import create_multiple


class GroupSetManager(models.Manager):
    def create(self, *args, **kwargs):
        study = kwargs.pop("study")

        descriptions = kwargs.pop("descriptions", [])
        group_exs = kwargs.pop("group_exs", [])
        comments = kwargs.pop("comments", [])

        groupset = super().create(*args, **kwargs)

        create_multiple(groupset,descriptions,"descriptions")
        create_multiple(groupset,comments,"comments")


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
        return groupset


class GroupExManager(models.Manager):
    def create(self, *args, **kwargs):
        characteristica_ex = kwargs.pop("characteristica_ex", [])
        groups = kwargs.pop("groups", [])
        study = kwargs.pop("study")
        group_exs = kwargs.pop("group_exs")
        comments = kwargs.pop("comments", [])


        group_ex = super().create(*args, **kwargs)
        for characteristica_ex_single in characteristica_ex:
            characteristica_ex_single["count"] = characteristica_ex_single.get("count", group_ex.count)
            group_ex.characteristica_ex.create(**characteristica_ex_single)


        for group in groups:
            group["study"] = study
            group["group_exs"] = group_exs
            group_ex.groups.create(**group)

        create_multiple(group_ex,comments,"comments")

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

        create_multiple(group, characteristica, "characteristica")

        group.save()
        return group


class CharacteristicaManager(models.Manager):
    def create(self, *args, **kwargs):
        comments = kwargs.pop("comments", [])
        instance = super().create(*args, **kwargs)

        create_multiple(instance,comments,"comments")
        instance.save()
        return instance



class IndividualSetManager(models.Manager):
    def create(self, *args, **kwargs):
        individual_exs = kwargs.pop("individual_exs", [])
        descriptions = kwargs.pop("descriptions", [])
        kwargs.pop("study")
        comments = kwargs.pop("comments", [])

        individualset = super().create(*args, **kwargs)


        create_multiple(individualset,descriptions,"descriptions")
        create_multiple(individualset,individual_exs,"individual_exs")
        create_multiple(individualset,comments,"comments")

        individualset.save()
        return individualset


class IndividualExManager(models.Manager):
    def create(self, *args, **kwargs):

        characteristica_ex = kwargs.pop("characteristica_ex", [])
        individuals = kwargs.pop("individuals", [])
        comments = kwargs.pop("comments", [])

        individual_ex = super().create(*args, **kwargs)

        create_multiple(individual_ex,characteristica_ex,"characteristica_ex")
        create_multiple(individual_ex,individuals,"individuals")
        create_multiple(individual_ex,comments,"comments")

        individual_ex.save()
        return individual_ex


class IndividualManager(models.Manager):
    def create(self, *args, **kwargs):
        characteristica = kwargs.pop("characteristica", [])
        individual = super().create(*args, **kwargs)

        create_multiple(individual,characteristica,"characteristica")
        individual.save()
        return individual

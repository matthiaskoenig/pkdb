"""
the managers can be used to overwrite class methods of the models module.
"""
from django.db import models


class GroupSetManager(models.Manager):
    def create(self, *args, **kwargs):
        study = kwargs.pop("study")

        descriptions = kwargs.pop("descriptions", [])
        group_exs = kwargs.pop("group_exs", [])
        groupset = super().create(*args, **kwargs)

        for description in descriptions:
            groupset.descriptions.create(**description)

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


        group_ex = super().create(*args, **kwargs)
        for characteristica_ex_single in characteristica_ex:
            characteristica_ex_single["count"] = characteristica_ex_single.get("count", group_ex.count)
            group_ex.characteristica_ex.create(**characteristica_ex_single)


        for group in groups:


            group["study"] = study
            group["group_exs"] = group_exs

            g = group_ex.groups.create(**group)

        group_ex.save()
        return group_ex

class GroupManager(models.Manager):
    def create(self, *args, **kwargs):
        study = kwargs.pop("study")
        characteristica = kwargs.pop("characteristica", [])
        group_exs = kwargs.pop("group_exs")


        if kwargs.get("parent"):
            for group_ex in group_exs:
                if group_ex.name == kwargs["parent"]:
                    ex = group_ex
            kwargs["parent"] = self.model.objects.get(name=kwargs.get("parent"), ex=ex)

        group = super().create(*args, **kwargs)

        for characteristica_single in characteristica:
            group.characteristica.create(**characteristica_single)

        group.save()
        return group


class IndividualSetManager(models.Manager):
    def create(self, *args, **kwargs):
        individual_exs = kwargs.pop("individual_exs", [])
        descriptions = kwargs.pop("descriptions", [])
        study = kwargs.pop("study")


        individualset = super().create(*args, **kwargs)

        for description in descriptions:
            individualset.descriptions.create(**description)

        # create single individual_ex
        for individual_ex in individual_exs:
            individualset.individual_exs.create(**individual_ex)

        individualset.save()
        return individualset


class IndividualExManager(models.Manager):
    def create(self, *args, **kwargs):
        characteristica_ex = kwargs.pop("characteristica_ex", [])
        individuals = kwargs.pop("individuals", [])
        individual_ex = super().create(*args, **kwargs)

        for characteristica_ex_single in characteristica_ex:
            individual_ex.characteristica_ex.create(**characteristica_ex_single)
        for individual in individuals:
        #    print('*'*100)
        #    print(individual)
        #    print('*'*100)


            individual_ex.individuals.create(**individual)
        individual_ex.save()
        return individual_ex


class IndividualManager(models.Manager):
    def create(self, *args, **kwargs):
        characteristica = kwargs.pop("characteristica", [])
        individual = super().create(*args, **kwargs)

        for characteristica_single in characteristica:
            individual.characteristica.create(**characteristica_single)

        individual.save()
        return individual

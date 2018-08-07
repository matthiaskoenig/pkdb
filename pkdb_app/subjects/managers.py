"""
the managers can be used to overwrite class methods of the models module.
"""
from django.db import models


class GroupManager(models.Manager):
    def create(self, *args, **kwargs):
        characteristica = kwargs.pop("characteristica", [])
        group = super(GroupManager, self).create(*args, **kwargs)
        group.characteristica.all().delete()
        for characteristica_single in characteristica:
            characteristica_single["count"] = characteristica_single.get("count",group.count)
            group.characteristica.create(**characteristica_single)

        group.save()

        return group

class GroupSetManager(models.Manager):
    def create(self, *args, **kwargs):
        characteristica = kwargs.pop("characteristica", [])
        groups = kwargs.pop("groups", [])

        groupset = super(GroupSetManager, self).create(*args, **kwargs)
        groupset.characteristica.all().delete()
        groupset.groups.all().delete()


        for characteristica_single in characteristica:
            groupset.characteristica.create(**characteristica_single)

        for group in groups:
            groupset.groups.create(**group)

        groupset.save()

        return groupset

class IndividualManager(models.Manager):
    def create(self, *args, **kwargs):
        characteristica = kwargs.pop("characteristica", [])
        individual = super(IndividualManager, self).create(*args, **kwargs)
        individual.characteristica.all().delete()
        for characteristica_single in characteristica:
            individual.characteristica.create(**characteristica_single)
        individual.save()
        return individual


class IndividualSetManager(models.Manager):
    def create(self, *args, **kwargs):
        characteristica = kwargs.pop("characteristica", [])
        individuals = kwargs.pop("individuals", [])

        individualset = super(IndividualSetManager, self).create(*args, **kwargs)
        individualset.characteristica.all().delete()
        individualset.individuals.all().delete()


        for characteristica_single in characteristica:
            individualset.characteristica.create(**characteristica_single)

        for individual in individuals:
            individualset.individuals.create(**individual)

        individualset.save()

        return individualset
"""
the managers can be used to overwrite class methods of the models module.
"""
from django.db import models


class InterventionSetManager(models.Manager):
    def create(self, *args, **kwargs):

        interventions = kwargs.pop("interventions", [])

        interventionset = super().create(*args, **kwargs)
        interventionset.interventions.all().delete()

        for intervention in interventions:
            interventionset.interventions.create(**intervention)
            interventionset.save()


        return interventionset

class OutputSetManager(models.Manager):

    def create(self, *args, **kwargs):
        outputs = kwargs.pop("outputs", [])
        outputset = super().create(*args, **kwargs)
        outputset.outputs.all().delete()

        for output in outputs:
            outputset.outputs.create(**output)
            outputset.save()

        return outputset

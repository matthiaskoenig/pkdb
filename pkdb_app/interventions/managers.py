"""
the managers can be used to overwrite class methods of the models module.
"""
from django.db import models


class InterventionSetManager(models.Manager):
    def create(self, *args, **kwargs):

        interventions = kwargs.pop("interventions", [])
        interventionset = super(InterventionSetManager, self).create(*args, **kwargs)
        interventionset.interventions.all().delete()

        for intervention in interventions:
            interventionset.interventions.create(**intervention)
            interventionset.save()

        return interventionset

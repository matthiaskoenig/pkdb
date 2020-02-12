"""
the managers can be used to overwrite class methods of the models module.
"""
from django.apps import apps
from django.db import models

from ..utils import create_multiple, create_multiple_bulk, create_multiple_bulk_normalized



class InterventionExManager(models.Manager):
    def create(self, *args, **kwargs):
        interventions = kwargs.pop('interventions', [])
        comments = kwargs.pop('comments', [])
        descriptions = kwargs.pop('descriptions', [])

        intervention_ex = super().create(*args, **kwargs)

        create_multiple(intervention_ex, descriptions, 'descriptions')
        create_multiple(intervention_ex, comments, 'comments')
        Intervention = apps.get_model('interventions', 'Intervention')
        not_norm_interventions = create_multiple_bulk(intervention_ex, "ex", interventions, Intervention)
        create_multiple_bulk_normalized(not_norm_interventions, Intervention)
        intervention_ex.save()

        return intervention_ex

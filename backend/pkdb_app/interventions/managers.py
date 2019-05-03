"""
the managers can be used to overwrite class methods of the models module.
"""
from datetime import timedelta
from django.db import models
from django.apps import apps
import time
import pandas as pd
import numpy as np

from ..utils import create_multiple, create_multiple_bulk, create_multiple_bulk_normalized
from ..analysis.pharmacokinetic import f_pk

class InterventionSetManager(models.Manager):
    def create(self, *args, **kwargs):

        intervention_exs = kwargs.pop('intervention_exs', [])
        descriptions = kwargs.pop('descriptions', [])
        comments = kwargs.pop('comments', [])

        kwargs.pop('study')

        interventionset = super().create(*args, **kwargs)

        create_multiple(interventionset, descriptions, 'descriptions')
        create_multiple(interventionset, intervention_exs, 'intervention_exs')
        create_multiple(interventionset, comments, 'comments')
        interventionset.save()

        return interventionset


class InterventionExManager(models.Manager):
    def create(self, *args, **kwargs):

        interventions = kwargs.pop('interventions', [])
        comments = kwargs.pop('comments', [])

        intervention_ex = super().create(*args, **kwargs)

        create_multiple(intervention_ex, comments, 'comments')
        Intervention = apps.get_model('interventions', 'Intervention')
        not_norm_interventions = create_multiple_bulk(intervention_ex, "ex", interventions, Intervention)
        create_multiple_bulk_normalized(not_norm_interventions, Intervention)
        intervention_ex.save()

        return intervention_ex

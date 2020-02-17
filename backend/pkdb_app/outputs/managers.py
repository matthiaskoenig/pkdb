"""
the managers can be used to overwrite class methods of the models module.
"""
from django.db import models
from ..utils import _create

class OutputManager(models.Manager):
    def create(self, *args, **kwargs):
        kwargs["_interventions"] = kwargs.pop('interventions', [])
        output, _ = _create(model_manager=super(), validated_data=kwargs, add_multiple_keys=['_interventions'])
        return output

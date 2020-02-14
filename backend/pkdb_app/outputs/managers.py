"""
the managers can be used to overwrite class methods of the models module.
"""
from django.apps import apps
from django.db import models
from ..utils import create_multiple_bulk_normalized, _create

class OutputExManager(models.Manager):
    def create(self, **kwargs):
        output_ex, _ = _create(model_manager=super(),
                               validated_data=kwargs,
                               add_multiple_keys=['interventions'],
                               create_multiple_keys=['comments', 'descriptions', 'outputs'])
        Output = apps.get_model('outputs', 'Output')
        outputs_normed = create_multiple_bulk_normalized(output_ex.outputs.all(), Output)
        if outputs_normed:
            for output in outputs_normed:
                output._interventions.add(*output.interventions.all())
        return output_ex


class OutputManager(models.Manager):
    def create(self, *args, **kwargs):
        kwargs["_interventions"] = kwargs.pop('interventions', [])
        output, _ = _create(model_manager=super(), validated_data=kwargs,
                               add_multiple_keys=['_interventions'])
        return output

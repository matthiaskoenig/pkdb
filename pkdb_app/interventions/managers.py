"""
the managers can be used to overwrite class methods of the models module.
"""
from django.db import models
from django.apps import apps


class InterventionSetManager(models.Manager):
    def create(self, *args, **kwargs):

        interventions = kwargs.pop("interventions", [])
        descriptions = kwargs.pop("descriptions", [])


        interventionset = super().create(*args, **kwargs)
        interventionset.interventions.all().delete()

        for description in descriptions:
            interventionset.descriptions.create(**description)

        for intervention in interventions:
            interventionset.interventions.create(**intervention)
            interventionset.save()


        return interventionset

class OutputSetManager(models.Manager):

    def create(self, *args, **kwargs):
        outputs = kwargs.pop("outputs", [])
        timecourses = kwargs.pop("timecourses", [])
        descriptions = kwargs.pop("descriptions", [])
        outputset = super().create(*args, **kwargs)
        outputset.outputs.all().delete()

        for description in descriptions:
            outputset.descriptions.create(**description)

        for output in outputs:
            intervention_ids = output.pop("interventions", [])
            output_instance = outputset.outputs.create(**output)
            output_instance.interventions.add(*intervention_ids)
            output_instance.save()
            outputset.save()

        for timecourse in timecourses:
            intervention_ids = timecourse.pop("interventions", [])
            timecourse_instance = outputset.timecourses.create(**timecourse)
            timecourse_instance.interventions.add(*intervention_ids)
            timecourse_instance.save()
            outputset.save()

        return outputset

class OutputManager(models.Manager):
    def create(self, *args, **kwargs):
        cleaned = kwargs.pop("cleaned", [])
        output = super().create(*args, **kwargs)
        for clean_single in cleaned:
            output.cleaned.create(outputset=output.outputset, **clean_single)
        output.save()
        return output
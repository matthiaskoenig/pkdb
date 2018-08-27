"""
the managers can be used to overwrite class methods of the models module.
"""
from django.db import models
from django.apps import apps


class InterventionSetManager(models.Manager):
    def create(self, *args, **kwargs):

        intervention_exs = kwargs.pop("intervention_exs", [])
        descriptions = kwargs.pop("descriptions", [])
        study = kwargs.pop("study")



        interventionset = super().create(*args, **kwargs)

        for description in descriptions:
            interventionset.descriptions.create(**description)

        for intervention_ex in intervention_exs:
            interventionset.intervention_exs.create(**intervention_ex)
            interventionset.save()


        return interventionset

class InterventionExManager(models.Manager):
    def create(self, *args, **kwargs):
        interventions = kwargs.pop("interventions", [])
        intervention_ex = super().create(*args, **kwargs)
        for intervention in interventions:
            intervention_ex.interventions.create(**intervention)
        intervention_ex.save()
        return intervention_ex

class OutputSetManager(models.Manager):

    def create(self, *args, **kwargs):
        study = kwargs.pop("study")
        output_exs = kwargs.pop("output_exs", [])
        timecourse_exs = kwargs.pop("timecourse_exs", [])
        descriptions = kwargs.pop("descriptions", [])
        outputset = super().create(*args, **kwargs)

        for description in descriptions:
            outputset.descriptions.create(**description)

        for output_ex in output_exs:

            intervention_ids = output_ex.pop("interventions", [])
            output_ex_instance = outputset.output_exs.create(**output_ex)
            output_ex_instance.interventions.add(*intervention_ids)
            output_ex_instance.save()
            outputset.save()

        for timecourse_ex in timecourse_exs:
            intervention_ids = timecourse_ex.pop("interventions", [])
            timecourse_ex_instance = outputset.timecourse_exs.create(**timecourse_ex)
            timecourse_ex_instance.interventions.add(*intervention_ids)
            timecourse_ex_instance.save()
            outputset.save()

        return outputset

class OutputExManager(models.Manager):
    def create(self, *args, **kwargs):
        outputs = kwargs.pop("outputs", [])
        interventions = kwargs.pop("interventions", [])

        output_ex = super().create(*args, **kwargs)
        for internvention in interventions:
            output_ex.interventions.add(internvention)
        for output in outputs:
            output_ex.outputs.create(**output)
        output_ex.save()
        return output_ex

class OutputManager(models.Manager):
    def create(self, *args, **kwargs):
        interventions = kwargs.pop("interventions", [])
        output_ex = super().create(*args, **kwargs)
        for internvention in interventions:
            output_ex.interventions.add(internvention)

        output_ex.save()
        return output_ex

class TimecourseExManager(models.Manager):
    def create(self, *args, **kwargs):
        timecourses = kwargs.pop("timecourses", [])
        timecourse_ex = super().create(*args, **kwargs)
        for timecourse in timecourses:
            timecourse_ex.timecourses.create(**timecourse)
        timecourse_ex.save()
        return timecourse_ex



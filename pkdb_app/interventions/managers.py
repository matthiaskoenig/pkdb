"""
the managers can be used to overwrite class methods of the models module.
"""
from django.db import models
from pkdb_app.utils import create_multiple


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

        create_multiple(intervention_ex, interventions, 'interventions')
        create_multiple(intervention_ex, comments, 'comments')
        intervention_ex.save()

        return intervention_ex


class OutputSetManager(models.Manager):
    def create(self, *args, **kwargs):
        kwargs.pop('study')
        output_exs = kwargs.pop('output_exs', [])
        timecourse_exs = kwargs.pop('timecourse_exs', [])
        descriptions = kwargs.pop('descriptions', [])
        comments = kwargs.pop('comments', [])

        outputset = super().create(*args, **kwargs)

        create_multiple(outputset, descriptions, 'descriptions')
        create_multiple(outputset, comments, 'comments')

        for output_ex in output_exs:

            intervention_ids = output_ex.pop('interventions', [])
            output_ex_instance = outputset.output_exs.create(**output_ex)
            output_ex_instance.interventions.add(*intervention_ids)
            output_ex_instance.save()

        for timecourse_ex in timecourse_exs:
            intervention_ids = timecourse_ex.pop('interventions', [])
            timecourse_ex_instance = outputset.timecourse_exs.create(**timecourse_ex)
            timecourse_ex_instance.interventions.add(*intervention_ids)
            timecourse_ex_instance.save()

        outputset.save()
        return outputset


class OutputExManager(models.Manager):
    def create(self, *args, **kwargs):
        outputs = kwargs.pop('outputs', [])
        interventions = kwargs.pop('interventions', [])
        comments = kwargs.pop('comments', [])

        output_ex = super().create(*args, **kwargs)

        output_ex.interventions.add(*interventions)
        create_multiple(output_ex, comments, 'comments')
        create_multiple(output_ex, outputs, 'outputs')

        output_ex.save()
        return output_ex


class OutputManager(models.Manager):
    def create(self, *args, **kwargs):
        interventions = kwargs.pop('interventions', [])
        output = super().create(*args, **kwargs)

        output.interventions.add(*interventions)

        output.save()
        return output


class TimecourseExManager(models.Manager):
    def create(self, *args, **kwargs):
        timecourses = kwargs.pop('timecourses', [])
        interventions = kwargs.pop('interventions', [])
        comments = kwargs.pop('comments', [])

        timecourse_ex = super().create(*args, **kwargs)

        timecourse_ex.interventions.add(*interventions)
        create_multiple(timecourse_ex, comments, 'comments')
        create_multiple(timecourse_ex, timecourses, 'timecourses')

        timecourse_ex.save()
        return timecourse_ex

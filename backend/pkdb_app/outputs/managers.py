"""
the managers can be used to overwrite class methods of the models module.
"""
from django.apps import apps
from django.db import models
from ..utils import create_multiple_bulk, create_multiple_bulk_normalized, _create

class OutputExManager(models.Manager):
    def create(self, **kwargs):
        output_ex, _ = _create(model_manager= super(), validated_data=kwargs,
                                        add_multiple_keys=['interventions'], create_multiple_keys=[ 'comments', 'descriptions','outputs'])

        Output = apps.get_model('outputs', 'Output')
        outputs_normed = create_multiple_bulk_normalized(output_ex.outputs.all(), Output)
        for output in outputs_normed:
            output._interventions.add(*output.interventions.all())

        return output_ex


class OutputManager(models.Manager):
    def create(self, *args, **kwargs):
        output, _ = _create(model_manager=super(), validated_data=kwargs,
                               add_multiple_keys=['interventions'])
        return output


class TimecourseExManager(models.Manager):

    def create(self, **kwargs):
        timecourse_ex, _ = _create(model_manager=super(), validated_data=kwargs,
                               add_multiple_keys=['interventions'],
                               create_multiple_keys=['comments', 'descriptions', 'timecourses'])

        Output = apps.get_model('outputs', 'Output')
        Timecourse = apps.get_model('outputs', 'Timecourse')

        timecourses_normed = create_multiple_bulk_normalized(timecourse_ex.timecourses.all(), Timecourse)

        for timecourse in timecourses_normed:
            timecourse._interventions.add(*timecourse.interventions.all())

            # calculate pharmacokinetics data from normalized timecourses
            #outputs = self._calculate_outputs(timecourse)
            outputs = []
            outputs_dj = create_multiple_bulk(timecourse, "timecourse", outputs, Output)
            if outputs_dj:
                outputs_normed = create_multiple_bulk_normalized(outputs_dj, Output)
                for output in outputs_normed:
                    output._interventions.add(*output.interventions.all())

        timecourse_ex.save()
        return timecourse_ex



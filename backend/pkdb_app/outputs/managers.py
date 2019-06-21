"""
the managers can be used to overwrite class methods of the models module.
"""
from datetime import timedelta
from django.db import models
from django.apps import apps
import time
import pandas as pd
import numpy as np

from pkdb_app.categorials.models import MeasurementType
from ..utils import create_multiple, create_multiple_bulk, create_multiple_bulk_normalized
from ..analysis.pharmacokinetic import f_pk


class OutputSetManager(models.Manager):
    def create(self, *args, **kwargs):
        start_time = time.time()
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

        outputs_dj = create_multiple(output_ex, outputs, 'outputs')

        Output = apps.get_model('outputs', 'Output')
        create_multiple_bulk_normalized(outputs_dj,Output)
        output_ex.save()

        return output_ex


class OutputManager(models.Manager):
    def create(self, *args, **kwargs):
        interventions = kwargs.pop('interventions', [])
        output = super().create(*args, **kwargs)
        output._interventions.add(*interventions)
        return output


class TimecourseExManager(models.Manager):
    def create(self, *args, **kwargs):

        timecourses = kwargs.pop('timecourses', [])
        interventions = kwargs.pop('interventions', [])
        comments = kwargs.pop('comments', [])

        timecourse_ex = super().create(*args, **kwargs)
        timecourse_ex.interventions.add(*interventions)
        create_multiple(timecourse_ex, comments, 'comments')

        timecourses_dj = create_multiple(timecourse_ex, timecourses, 'timecourses')
        Timecourse = type(timecourses_dj[0])

        Output = apps.get_model('outputs','Output')

        timecourses = create_multiple_bulk_normalized(timecourses_dj,  Timecourse)

        # calculate pharmacokinetics data from normalized timecourses
        for timecourse in timecourses:
            if timecourse.measurement_type.name == "concentration" and timecourse.normed:
                variables = timecourse.get_pharmacokinetic_variables()
                c_type = variables.pop("c_type", None)
                _ = variables.pop("bodyweight_type", None)
                pk = f_pk(**variables)


                key_mapping = {"auc": MeasurementType.objects.get(name="auc_end"),
                               "aucinf":MeasurementType.objects.get(name="auc_inf"),
                               "cl":MeasurementType.objects.get(name="clearance"),
                               "cmax":MeasurementType.objects.get(name="cmax"),
                               "kel":MeasurementType.objects.get(name="kel"),
                               "thalf":MeasurementType.objects.get(name="thalf"),
                               "tmax": MeasurementType.objects.get(name="tmax"),
                               "vd":MeasurementType.objects.get(name="vd"),
                               }
                outputs = []
                for key in ["auc", "aucinf", "cl", "cmax", "kel", "thalf", "vd","tmax"]:
                    pk_unit = pk[f"{key}_unit"]
                    if not np.isnan(pk[key]):
                        output_dict = {}
                        output_dict[c_type] = pk[key]
                        output_dict["unit"] = pk_unit
                        output_dict["measurement_type"] = key_mapping[key]
                        output_dict["calculated"] = True
                        output_dict["tissue"] = timecourse.tissue
                        output_dict["substance"] = timecourse.substance
                        output_dict["group"] = timecourse.group
                        output_dict["individual"] = timecourse.individual
                        if output_dict["measurement_type"].name == "auc_end":
                            output_dict["time"] = max(timecourse.time)
                            output_dict["time_unit"] = timecourse.time_unit
                        outputs.append(output_dict)

                outputs_dj = create_multiple_bulk(timecourse, "timecourse", outputs, Output)
                create_multiple_bulk_normalized(outputs_dj, Output)

        timecourse_ex.save()
        return timecourse_ex

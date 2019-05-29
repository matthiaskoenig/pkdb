"""
Describe outputs and timecourses
"""

import numpy as np
import math
import pandas as pd

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import models
from django.contrib.postgres.fields import ArrayField
from pkdb_app.categorials.models import MeasurementType
from pkdb_app.interventions.models import Intervention

from ..utils import CHAR_MAX_LENGTH, create_choices
from pkdb_app.subjects.models import Group, DataFile, Individual

from .managers import (
    OutputSetManager,
    OutputExManager,
    TimecourseExManager,
    OutputManager
)
from ..normalization import get_cv, get_se, get_sd
from ..behaviours import (
    Externable)

from pkdb_app.categorials.behaviours import Normalizable, ExMeasurementTypeable, ValueableMapNotBlank, \
    ValueableNotBlank, MeasurementTypeable

TIME_NORM_UNIT = "hr"

OUTPUT_TISSUE_DATA = [
    "plasma",
    "saliva",
    "serum",
    "spinal fluid",
    "urine",
    "saliva/plasma",  # this is not a good solution
    "breath",
    "bile duct"
]
OUTPUT_TISSUE_DATA_CHOICES = create_choices(OUTPUT_TISSUE_DATA)

# -------------------------------------------------
# OUTPUTS
# -------------------------------------------------
class OutputSet(models.Model):
    objects = OutputSetManager()

    @property
    def outputs(self):
        outputs = Output.objects.filter(ex__in=self.output_exs.all())
        outputs_timecourses = Output.objects.filter(timecourse__in=self.timecourses.all())
        return outputs | outputs_timecourses

    @property
    def outputs_normed(self):
        outputs = self.outputs.filter(normed=True)
        outputs_timecourses = Output.objects.filter(timecourse__in=self.timecourses.all())
        return outputs | outputs_timecourses

    @property
    def count_outputs(self):
        if self.outputs:
            return self.outputs.count()
        else:
            return 0

    @property
    def timecourses(self):
        timecourses = Timecourse.objects.filter(ex__in=self.timecourse_exs.all())
        return timecourses

    @property
    def timecourses_normed(self):
        timecourses = self.timecourses.filter(normed=True)
        return timecourses

    @property
    def count_timecourses(self):
        if self.timecourses:
            return self.timecourses.count()
        else:
            return 0


class AbstractOutput(models.Model):
    tissue = models.CharField( max_length=CHAR_MAX_LENGTH, choices=OUTPUT_TISSUE_DATA_CHOICES, null=True)
    time = models.FloatField(null=True)
    time_unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    class Meta:
        abstract = True


class AbstractOutputMap(models.Model):
    tissue_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    time_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    time_unit_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    class Meta:
        abstract = True


class OutputEx(Externable,
               AbstractOutput,
               AbstractOutputMap,
               ExMeasurementTypeable
               ):
    source = models.ForeignKey(
        DataFile, related_name="s_output_exs", null=True, on_delete=models.SET_NULL
    )
    figure = models.ForeignKey(
        DataFile, related_name="f_output_exs", null=True, on_delete=models.SET_NULL
    )
    outputset = models.ForeignKey(
        OutputSet, related_name="output_exs", on_delete=models.CASCADE, null=True
    )

    #todo: make this charfields

    group = models.ForeignKey(Group, null=True, on_delete=models.SET_NULL)
    individual = models.ForeignKey(Individual, null=True, on_delete=models.SET_NULL)
    interventions = models.ManyToManyField(Intervention)

    group_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    individual_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    interventions_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    objects = OutputExManager()


class Output(AbstractOutput,Normalizable):
    """ Storage of data sets. """

    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.SET_NULL)
    individual = models.ForeignKey(Individual, null=True, blank=True, on_delete=models.SET_NULL)
    _interventions = models.ManyToManyField(Intervention)
    tissue = models.CharField(max_length=CHAR_MAX_LENGTH, choices=OUTPUT_TISSUE_DATA_CHOICES)
    ex = models.ForeignKey(OutputEx, related_name="outputs", on_delete=models.CASCADE, null=True)

    # calculated by timecourse data
    calculated = models.BooleanField(default=False)
    timecourse = models.ForeignKey("Timecourse", on_delete=models.CASCADE, related_name="pharmacokinetics", null=True)
    objects = OutputManager()

    @property
    def interventions(self):
        interventions = self._interventions
        if interventions.all():
            return interventions

        elif self.timecourse:
            return self.timecourse.interventions
        else:
            return self.raw._interventions


    @property
    def study(self):

        try:
            return self.ex.outputset.study.name

        except AttributeError:
            return self.timecourse.ex.outputset.study.name


    # for elastic search. NaNs are not allowed in elastic search

    def null_attr(self, attr):
        value = getattr(self, attr)
        if value not in ['nan', 'NA', 'NAN', 'na', np.NaN, None] and not math.isnan(value):
            return value

    def null_value(self):
        return self.null_attr('value')

    def null_mean(self):
        return self.null_attr('mean')

    def null_median(self):
        return self.null_attr('median')

    def null_min(self):
        return self.null_attr('min')

    def null_max(self):
        return self.null_attr('max')

    def null_se(self):
        return self.null_attr('se')

    def null_sd(self):
        return self.null_attr('sd')

    def null_cv(self):
        return self.null_attr('cv')

    def null_unit(self):
        return self.null_attr('unit')

    def null_time(self):
        return self.null_attr('time')

    def add_error_measures(self):
        if self.group:
            if not self.sd:
                self.sd = get_sd(
                    se=self.se, count=self.group.count, mean=self.mean, cv=self.cv
                )
            if not self.se:
                self.se = get_se(
                    sd=self.sd, count=self.group.count, mean=self.mean, cv=self.cv
                )
            if not self.cv:
                self.cv = get_cv(
                    se=self.se, count=self.group.count, mean=self.mean, sd=self.sd
                )


class TimecourseEx(
    Externable,
    AbstractOutput,
    AbstractOutputMap,
    ExMeasurementTypeable
):
    """
    Don't split the mappings to csv for
    value
    mean
    median
    min
    max
    sd
    se
    cv
    time
    """
    source = models.ForeignKey(
        DataFile, related_name="s_timecourse_exs", null=True, on_delete=models.SET_NULL
    )
    figure = models.ForeignKey(
        DataFile, related_name="f_timecourse_exs", null=True, on_delete=models.SET_NULL
    )
    outputset = models.ForeignKey(
        OutputSet, related_name="timecourse_exs", on_delete=models.CASCADE, null=True
    )

    group = models.ForeignKey(Group, null=True, on_delete=models.SET_NULL)
    individual = models.ForeignKey(Individual, null=True, on_delete=models.SET_NULL)
    interventions = models.ManyToManyField(Intervention)

    group_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    individual_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    interventions_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    objects = TimecourseExManager()


class Timecourse(AbstractOutput, Normalizable):
    """ Storing of time course data.

    Store a binary blop of the data (json, pandas dataframe or similar, backwards compatible).
    """
    group = models.ForeignKey(Group, null=True, on_delete=models.CASCADE)
    individual = models.ForeignKey(Individual, null=True, on_delete=models.CASCADE)
    _interventions = models.ManyToManyField(Intervention)
    ex = models.ForeignKey(
        TimecourseEx, related_name="timecourses", on_delete=models.CASCADE
    )
    tissue = models.CharField(max_length=CHAR_MAX_LENGTH, choices=OUTPUT_TISSUE_DATA_CHOICES)

    value = ArrayField(models.FloatField(null=True), null=True)
    mean = ArrayField(models.FloatField(null=True), null=True)
    median = ArrayField(models.FloatField(null=True), null=True)
    min = ArrayField(models.FloatField(null=True), null=True)
    max = ArrayField(models.FloatField(null=True), null=True)
    sd = ArrayField(models.FloatField(null=True), null=True)
    se = ArrayField(models.FloatField(null=True), null=True)
    cv = ArrayField(models.FloatField(null=True), null=True)
    time = ArrayField(models.FloatField(null=True), null=True)
    objects = OutputManager()

    @property
    def interventions(self):
        interventions = self._interventions
        if interventions.all():
            return interventions
        else:
            try:
                return self.raw._interventions
            except AttributeError:
                return []

    @property
    def study(self):
        return self.ex.outputset.study.name

    @property
    def figure(self):
        try:
            return self.ex.figure.file.url
        except AttributeError:
            return None

    def add_error_measures(self):
        """ Calculates additional error measures."""
        if self.group:
            if not self.sd:
                sd = get_sd(
                    se=self.se, count=self.group.count, mean=self.mean, cv=self.cv
                )
                if isinstance(sd, np.ndarray):
                    self.sd = list(sd)
            if not self.se:
                se = get_se(
                    sd=self.sd, count=self.group.count, mean=self.mean, cv=self.cv
                )
                if isinstance(se, np.ndarray):
                    self.se = list(se)
            if not self.cv:
                cv = get_cv(
                    se=self.se, count=self.group.count, mean=self.mean, sd=self.sd
                )
                if isinstance(cv, np.ndarray):
                    self.cv = list(cv)

    def normalize(self):
        """Normalizes timecourse."""

        if not self.is_norm:
            for key, value in self.norm_fields.items():
                if value is not None:
                    list_norm_values = list(self.measurement_type.normalize(value, self.unit).magnitude)
                    setattr(self, key, list_norm_values)
            self.unit = self.measurement_type.norm_unit(self.unit).__str__()

        # for time_unit
        if not self.time_unit == TIME_NORM_UNIT:
            p_time_unit = self.measurement_type.p_unit(self.time_unit)
            times = p_time_unit * self.time
            norm_times = times.to(TIME_NORM_UNIT)
            self.time = list(norm_times.m)
            self.time_unit = TIME_NORM_UNIT

    # for elastic search. NaNs are not allowed in elastic search
    @staticmethod
    def _any_not_json(value):
        return any([np.isnan(value), np.isinf(value), np.isneginf(value)])

    def null_attr(self, attr):
        value_list = getattr(self, attr)
        if value_list:
            value_list_none = [None if self._any_not_json(value) else value for value in value_list]
            return value_list_none

    def null_value(self):
        return self.null_attr('value')

    def null_mean(self):
        return self.null_attr('mean')

    def null_median(self):
        return self.null_attr('median')

    def null_min(self):
        return self.null_attr('min')

    def null_max(self):
        return self.null_attr('max')

    def null_se(self):
        return self.null_attr('se')

    def null_sd(self):
        return self.null_attr('sd')

    def null_cv(self):
        return self.null_attr('cv')

    def null_unit(self):
        return self.null_attr('unit')

    def null_time(self):
        return self.null_attr('time')

    ###############################################################################
    @property
    def related_subject(self):
        if self.group:
            return self.group
        elif self.individual:
            return self.individual

    def get_bodyweight(self):
        weight_measurememnt_type = self.related_subject.characteristica_all_normed.filter(measurement_type="weight")
        return weight_measurememnt_type

    def get_dosing(self):

        try:
            dosing_measurement_type = self.interventions.get(normed=True, measurement_type="dosing")
            return dosing_measurement_type

        except (ObjectDoesNotExist, MultipleObjectsReturned):
            return None

    def get_pharmacokinetic_variables(self):
        """Get data for pharmacokinetics calculation

        :return: dict of data for calculation of pharmacokinetics
        """
        # TODO: This should be refactored in the pharmacokinetics module
        pk_dict = {}

        # substance
        pk_dict["compound"] = self.substance.name

        # bodyweight
        bodyweight = self.get_bodyweight().first()

        # time
        pk_dict["t"] = pd.Series(self.time)
        pk_dict["t_unit"] = self.time_unit


        # concentration
        # FIXME: the timecourse data must be filtered based on the dosing times
        #   (or alternatively this should be handled in the pk calculation)
        pk_dict["c_unit"] = self.unit

        if self.mean:
            pk_dict["c"] = pd.Series(self.mean)
            pk_dict["c_type"] = "mean"

        elif self.median:
            pk_dict["c"] = pd.Series(self.median)
            pk_dict["c_type"] = "median"

        elif self.value:
            pk_dict["c"] = pd.Series(self.value)
            pk_dict["c_type"] = "value"

        # dosing
        dosing = self.get_dosing()
        if dosing:
            if MeasurementType.objects.get(name="restricted dosing").is_valid_unit(dosing.unit):
                p_unit_dosing = self.measurement_type.p_unit(dosing.unit)
                p_unit_concentration = self.measurement_type.p_unit(pk_dict["c_unit"])
                vd_unit = p_unit_dosing / p_unit_concentration
                pk_dict["vd_unit"] = str(vd_unit)
                pk_dict["dose"] = dosing.value
                pk_dict["dose_unit"] = dosing.unit

        # bodyweight dependent values
        if bodyweight:
            pk_dict["bodyweight_unit"] = bodyweight.unit

            if bodyweight.value:
                pk_dict["bodyweight"] = bodyweight.value
                pk_dict["bodyweight_type"] = "value"

            elif bodyweight.mean:
                pk_dict["bodyweight"] = bodyweight.mean
                pk_dict["bodyweight_type"] = "mean"

            elif bodyweight.median:
                pk_dict["bodyweight"] = bodyweight.median
                pk_dict["bodyweight_type"] = "median"

        return pk_dict

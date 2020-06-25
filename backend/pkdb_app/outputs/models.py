"""
Describe outputs
"""

import math

import numpy as np
from django.db import models

from pkdb_app.behaviours import Normalizable
from pkdb_app.info_nodes.models import Tissue, Method
from pkdb_app.interventions.models import Intervention
from pkdb_app.subjects.models import Group, DataFile, Individual
from .managers import (
    OutputManager
)
from ..behaviours import (
    Externable, Accessible)
from ..error_measures import calculate_cv, calculate_se, calculate_sd
from ..utils import CHAR_MAX_LENGTH

TIME_NORM_UNIT = "hr"


# -------------------------------------------------
# OUTPUTS
# -------------------------------------------------
class OutputSet(models.Model):

    @property
    def outputs(self):
        return self.study.outputs
        #return Output.objects.filter(ex__in=self.output_exs.all())

    @property
    def outputs_normed(self):
        outputs = self.outputs.filter(normed=True)
        return outputs

    @property
    def count_outputs(self):
        if self.outputs.exists():
            return self.outputs.count()
        else:
            return 0

class AbstractOutput(models.Model):
    time = models.FloatField(null=True)
    time_unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    class Meta:
        abstract = True



class OutputEx(Externable):
    source = models.ForeignKey(
        DataFile, related_name="s_output_exs", null=True, on_delete=models.SET_NULL
    )
    image = models.ForeignKey(
        DataFile, related_name="i_output_exs", null=True, on_delete=models.SET_NULL
    )
    outputset = models.ForeignKey(
        OutputSet, related_name="output_exs", on_delete=models.CASCADE, null=True
    )

class Outputable(Normalizable, models.Model):

    class Meta:
        abstract = True

    @property
    def i_tissue(self):

        return self._i("tissue")

    @property
    def tissue_name(self):
        if self.tissue:
            return self.tissue.info_node.name

    @property
    def i_method(self):

        return self._i("method")

    @property
    def method_name(self):
        if self.method:
            return self.method.info_node.name


class Output(AbstractOutput, Outputable, Accessible):
    """ Storage of data sets. """
    label = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.CASCADE)
    individual = models.ForeignKey(Individual, null=True, blank=True, on_delete=models.CASCADE)
    interventions = models.ManyToManyField(Intervention, through="OutputIntervention", related_name="outputs")
    timecourse = models.ForeignKey('data.Subset', on_delete=models.CASCADE, null=True, blank=True, related_name="pks")

    tissue = models.ForeignKey(Tissue, related_name="outputs", null=True, blank=True, on_delete=models.CASCADE)
    method = models.ForeignKey(Method, related_name="outputs", null=True, blank=True, on_delete=models.CASCADE)

    ex = models.ForeignKey(OutputEx, related_name="outputs", on_delete=models.CASCADE, null=True)

    calculated = models.BooleanField(default=False)
    study = models.ForeignKey('studies.Study', on_delete=models.CASCADE, related_name="outputs")

    objects = OutputManager()

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
                self.sd = calculate_sd(
                    se=self.se, count=self.group.count, mean=self.mean, cv=self.cv
                )
            if not self.se:
                self.se = calculate_se(
                    sd=self.sd, count=self.group.count, mean=self.mean, cv=self.cv
                )
            if not self.cv:
                self.cv = calculate_cv(
                    se=self.se, count=self.group.count, mean=self.mean, sd=self.sd
                )

class OutputIntervention(Accessible, models.Model):
    output = models.ForeignKey(Output, on_delete=models.CASCADE)
    intervention = models.ForeignKey(Intervention, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("output", "intervention")

    @property
    def study(self):
        return self.intervention.study

    @property
    def intervention_pk(self):
        return self.intervention.pk

    @property
    def intervention_name(self):
        return self.intervention.name

    @property
    def output_pk(self):
        return self.output.pk

    @property
    def group_name(self):
        if self.output.group:
            return self.output.group.name

    @property
    def group_pk(self):
        if self.output.group:
            return self.output.group.pk

    @property
    def individual_pk(self):
        if self.output.individual:
            return self.output.individual.pk

    @property
    def individual_name(self):
        if self.output.individual:
            return self.output.individual.name

    @property
    def value(self):
        return self.output.null_value

    @property
    def mean(self):
        return self.output.null_mean

    @property
    def median(self):
        return self.output.null_median

    @property
    def min(self):
        return self.output.null_min

    @property
    def max(self):
        return self.output.null_max

    @property
    def sd(self):
        return self.output.null_sd

    @property
    def se(self):
        return self.output.null_se

    @property
    def cv(self):
        return self.output.null_cv

    @property
    def unit(self):
        return self.output.unit

    @property
    def time(self):
        return self.output.null_time

    @property
    def time_unit(self):
        return self.output.time_unit

    @property
    def tissue(self):
        if self.output.tissue:
            return self.output.tissue.info_node.name


    @property
    def method(self):
        if self.output.method:
            return self.output.method.info_node.name

    @property
    def measurement_type(self):
        return self.output.measurement_type.info_node.name

    @property
    def choice(self):
        if self.output.choice:
            return self.output.choice.info_node.name

    @property
    def label(self):
        return self.output.label

    @property
    def substance(self):
        if self.output.substance:
            return self.output.substance.info_node.name

    @property
    def normed(self):
        return self.output.normed

    @property
    def calculated(self):
        return self.output.calculated
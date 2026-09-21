"""Django models for outputs: single measured or calculated pharmacokinetic values."""

import math

import numpy as np
from django.db import models
from django.utils.translation import gettext_lazy as _

from pkdb_app.behaviours import Normalizable
from pkdb_app.info_nodes.models import Method, Tissue
from pkdb_app.interventions.models import Intervention
from pkdb_app.subjects.models import DataFile, Group, Individual

from ..behaviours import Accessible, Externable
from ..error_measures import calculate_cv, calculate_sd, calculate_se
from ..utils import CHAR_MAX_LENGTH
from .managers import OutputManager

TIME_NORM_UNIT = "hr"


# -------------------------------------------------
# OUTPUTS
# -------------------------------------------------
class OutputSet(models.Model):
    """Collection of outputs uploaded for one study."""

    @property
    def outputs(self):
        """Return all outputs of the study this output set belongs to."""
        return self.study.outputs
        # return Output.objects.filter(ex__in=self.output_exs.all())

    @property
    def outputs_normed(self):
        """Return the normalized outputs of the study this output set belongs to."""
        return self.outputs.filter(normed=True)

    @property
    def count_outputs(self):
        """Return the number of outputs, or zero if none exist."""
        if self.outputs.exists():
            return self.outputs.count()
        return 0


class AbstractOutput(models.Model):
    """Abstract base model providing the time and time unit fields of an output."""

    time = models.FloatField(null=True)
    time_unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    class Meta:
        abstract = True


class OutputEx(Externable):
    """External (as uploaded) form of an output.

    The form references its source and image files.
    """

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
    """Abstract mixin providing tissue and method info node and name accessors."""

    class Meta:
        abstract = True

    @property
    def i_tissue(self):
        """Return the info node linked to the tissue field, or None if unset."""
        return self._i("tissue")

    @property
    def tissue_name(self):
        """Return the name of the tissue info node, or None if unset."""
        if self.tissue:
            return self.tissue.info_node.name
        return None

    @property
    def i_method(self):
        """Return the info node linked to the method field, or None if unset."""
        return self._i("method")

    @property
    def method_name(self):
        """Return the name of the method info node, or None if unset."""
        if self.method:
            return self.method.info_node.name
        return None


class Output(AbstractOutput, Outputable, Accessible):
    """A single measured or calculated pharmacokinetic value.

    The value belongs to a group or an individual.
    """

    class OutputTypes(models.TextChoices):
        """The kinds of output: a single value, a timecourse point or an array."""

        Array = "array", _("array")
        Timecourse = "timecourse", _("timecourse")
        Output = "output", _("output")

    label = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    output_type = models.CharField(
        max_length=CHAR_MAX_LENGTH, choices=OutputTypes.choices
    )

    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.CASCADE)
    individual = models.ForeignKey(
        Individual, null=True, blank=True, on_delete=models.CASCADE
    )
    interventions = models.ManyToManyField(
        Intervention, through="OutputIntervention", related_name="outputs", blank=True
    )
    subset = models.ForeignKey(
        "data.Subset",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="pks",
    )

    tissue = models.ForeignKey(
        Tissue, related_name="outputs", null=True, blank=True, on_delete=models.CASCADE
    )
    method = models.ForeignKey(
        Method, related_name="outputs", null=True, blank=True, on_delete=models.CASCADE
    )

    ex = models.ForeignKey(
        OutputEx, related_name="outputs", on_delete=models.CASCADE, null=True
    )

    calculated = models.BooleanField(default=False)
    study = models.ForeignKey(
        "studies.Study", on_delete=models.CASCADE, related_name="outputs"
    )

    objects = OutputManager()

    # for elastic search. NaNs are not allowed in elastic search
    def null_attr(self, attr):
        """Return the named attribute.

        None is returned when the attribute is missing or NaN, because
        elasticsearch rejects NaN.
        """
        value = getattr(self, attr)
        if value not in ["nan", "NA", "NAN", "na", np.nan, None] and not math.isnan(
            value
        ):
            return value
        return None

    def is_timecourse(self):
        """Return True if this output belongs to a timecourse data set."""
        return bool(self.timecourse and self.timecourse.data.data_type == "timecourse")

    def null_value(self):
        """Return the value, or None if missing or NaN."""
        return self.null_attr("value")

    def null_mean(self):
        """Return the mean, or None if missing or NaN."""
        return self.null_attr("mean")

    def null_median(self):
        """Return the median, or None if missing or NaN."""
        return self.null_attr("median")

    def null_min(self):
        """Return the min, or None if missing or NaN."""
        return self.null_attr("min")

    def null_max(self):
        """Return the max, or None if missing or NaN."""
        return self.null_attr("max")

    def null_se(self):
        """Return the standard error, or None if missing or NaN."""
        return self.null_attr("se")

    def null_sd(self):
        """Return the standard deviation, or None if missing or NaN."""
        return self.null_attr("sd")

    def null_cv(self):
        """Return the coefficient of variation, or None if missing or NaN."""
        return self.null_attr("cv")

    def null_unit(self):
        """Return the unit, or None if missing or NaN."""
        return self.null_attr("unit")

    def null_time(self):
        """Return the time, or None if missing or NaN."""
        return self.null_attr("time")

    def add_error_measures(self):
        """Fill in the missing sd, se and cv of a group output.

        The missing measures are calculated from the ones which are set.
        """
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
    """Link between an output and one of the interventions it was measured under."""

    output = models.ForeignKey(Output, on_delete=models.CASCADE)
    intervention = models.ForeignKey(Intervention, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("output", "intervention")

    @property
    def study(self):
        """Return the study of the linked intervention."""
        return self.intervention.study

    @property
    def intervention_pk(self):
        """Return the primary key of the linked intervention."""
        return self.intervention.pk

    @property
    def intervention_name(self):
        """Return the name of the linked intervention."""
        return self.intervention.name

    @property
    def output_pk(self):
        """Return the primary key of the linked output."""
        return self.output.pk

    @property
    def output_label(self):
        """Return the label of the linked output."""
        return self.output.label

    @property
    def output_type(self):
        """Return the output type of the linked output."""
        return self.output.output_type

    @property
    def group_name(self):
        """Return the name of the output's group, or None if it has none."""
        if self.output.group:
            return self.output.group.name
        return None

    @property
    def group_pk(self):
        """Return the primary key of the output's group, or None if it has none."""
        if self.output.group:
            return self.output.group.pk
        return None

    @property
    def individual_pk(self):
        """Return the primary key of the output's individual, or None if it has none."""
        if self.output.individual:
            return self.output.individual.pk
        return None

    @property
    def individual_name(self):
        """Return the name of the output's individual, or None if it has none."""
        if self.output.individual:
            return self.output.individual.name
        return None

    @property
    def value(self):
        """Return the output's bound method null_value, not its value.

        The call of the method is missing.
        """
        return self.output.null_value

    @property
    def mean(self):
        """Return the output's bound method null_mean, not its value.

        The call of the method is missing.
        """
        return self.output.null_mean

    @property
    def median(self):
        """Return the output's bound method null_median, not its value.

        The call of the method is missing.
        """
        return self.output.null_median

    @property
    def min(self):
        """Return the output's bound method null_min, not its value.

        The call of the method is missing.
        """
        return self.output.null_min

    @property
    def max(self):
        """Return the output's bound method null_max, not its value.

        The call of the method is missing.
        """
        return self.output.null_max

    @property
    def sd(self):
        """Return the output's bound method null_sd, not its value.

        The call of the method is missing.
        """
        return self.output.null_sd

    @property
    def se(self):
        """Return the output's bound method null_se, not its value.

        The call of the method is missing.
        """
        return self.output.null_se

    @property
    def cv(self):
        """Return the output's bound method null_cv, not its value.

        The call of the method is missing.
        """
        return self.output.null_cv

    @property
    def unit(self):
        """Return the output's unit."""
        return self.output.unit

    @property
    def time(self):
        """Return the output's bound method null_time, not its value.

        The call of the method is missing.
        """
        return self.output.null_time

    @property
    def time_unit(self):
        """Return the output's time unit."""
        return self.output.time_unit

    @property
    def tissue(self):
        """Return the sid of the output's tissue info node, or None if it has none."""
        if self.output.tissue:
            return self.output.tissue.info_node.sid
        return None

    @property
    def tissue_label(self):
        """Return the label of the output's tissue info node, or None if it has none."""
        if self.output.tissue:
            return self.output.tissue.info_node.label
        return None

    @property
    def method(self):
        """Return the sid of the output's method info node, or None if it has none."""
        if self.output.method:
            return self.output.method.info_node.sid
        return None

    @property
    def method_label(self):
        """Return the label of the output's method info node, or None if it has none."""
        if self.output.method:
            return self.output.method.info_node.label
        return None

    @property
    def measurement_type(self):
        """Return the sid of the output's measurement type info node."""
        return self.output.measurement_type.info_node.sid

    @property
    def measurement_type_label(self):
        """Return the label of the output's measurement type info node."""
        return self.output.measurement_type.info_node.label

    @property
    def calculation_type(self):
        """Return the sid of the output's calculation type info node.

        None is returned when the output has no calculation type.
        """
        if self.output.calculation_type:
            return self.output.calculation_type.info_node.sid
        return None

    @property
    def calculation_type_label(self):
        """Return the label of the output's calculation type info node.

        None is returned when the output has no calculation type.
        """
        if self.output.calculation_type:
            return self.output.calculation_type.info_node.label
        return None

    @property
    def choice(self):
        """Return the sid of the output's choice info node, or None if it has none."""
        if self.output.choice:
            return self.output.choice.info_node.sid
        return None

    @property
    def choice_label(self):
        """Return the label of the output's choice info node, or None if it has none."""
        if self.output.choice:
            return self.output.choice.info_node.label
        return None

    @property
    def label(self):
        """Return the label of the linked output."""
        return self.output.label

    @property
    def substance(self):
        """Return the sid of the output's substance info node.

        None is returned when the output has no substance.
        """
        if self.output.substance:
            return self.output.substance.info_node.sid
        return None

    @property
    def substance_label(self):
        """Return the label of the output's substance info node.

        None is returned when the output has no substance.
        """
        if self.output.substance:
            return self.output.substance.info_node.label
        return None

    @property
    def normed(self):
        """Return whether the linked output is normalized."""
        return self.output.normed

    @property
    def calculated(self):
        """Return whether the linked output is calculated rather than measured."""
        return self.output.calculated

"""
Describe Interventions and Output (i.e. define the characteristics of the
group or individual).
"""

import numpy as np
import math
import pandas as pd

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import models
from django.contrib.postgres.fields import ArrayField

from ..utils import CHAR_MAX_LENGTH, CHAR_MAX_LENGTH_LONG
from ..subjects.models import Group, DataFile, Individual

from ..interventions.managers import (
    InterventionSetManager,
    OutputSetManager,
    OutputExManager,
    TimecourseExManager,
    InterventionExManager,
    OutputManager
)
from ..normalization import get_cv, get_se, get_sd
from ..behaviours import (
    Valueable,
    ValueableMap,
    Externable,
    ValueableNotBlank,
    ValueableMapNotBlank,
    Normalizable,
    Sidable
)
from ..categoricals import (
    INTERVENTION_CHOICES,
    INTERVENTION_ROUTE_CHOICES,
    INTERVENTION_FORM_CHOICES,
    INTERVENTION_APPLICATION_CHOICES,
    PK_DATA_CHOICES,
    OUTPUT_TISSUE_DATA_CHOICES, PK_DATA_DICT, INTERVENTION_DICT, TIME_NORM_UNIT, DOSING_RESTRICTED
)


from ..substances.substances import SUBSTANCES_DATA_CHOICES


# -------------------------------------------------
# Substance
# -------------------------------------------------


class Substance(Sidable, models.Model):
    """ Substances.

    There could be three main classes of `substances`:
    1. Substance with a chebi identifier
    - this is a basic substance and can have a mass (or not)
    2. Substance with no chebi identifier
    - this is a basic substance and can have a mass (or not)
    3. Derived substance (with no chebi identifier)
    - this is a combination of basic substances (from class 1 or 2).
    - this has no mass
    - if all partial substances have mass this could be used for unit transformations ?!

    Has to be extended via ontology (Ontologable)
    """
    # this cannot be null (for class 1 & 2), must be null for class 3
    name = models.CharField(max_length=CHAR_MAX_LENGTH, choices=SUBSTANCES_DATA_CHOICES, unique=True)
    chebi = models.CharField(null=True, max_length=CHAR_MAX_LENGTH, unique=True)
    url_slug = models.CharField(max_length=CHAR_MAX_LENGTH, unique=True)

    description = models.TextField(blank=True, null=True)
    mass = models.FloatField(null=True)
    charge = models.FloatField(null=True)
    formula = models.CharField(null=True, max_length=CHAR_MAX_LENGTH)  # chemical formula

    parents = models.ManyToManyField("Substance", related_name="children")

    # validation rule: check that all labels are in derived and not more(split on `+/()`)

    def __str__(self):
        return self.name

    @property
    def derived(self):
        return bool(self.parents)

    @property
    def outputs_normed(self):
        return self.outputs.filter(normed=True)

    @property
    def timecourses_normed(self):
        return self.timecourses.filter(normed=True)

    @property
    def interventions_normed(self):
        return self.interventions.filter(normed=True)


class Synonym(models.Model):
    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    substance = models.ForeignKey(Substance, on_delete=models.CASCADE, related_name="synonyms")


# -------------------------------------------------
# Intervention
# -------------------------------------------------
class InterventionSet(models.Model):
    objects = InterventionSetManager()

    @property
    def interventions(self):
        """ all interventions """
        interventions = Intervention.objects.filter(ex__in=self.intervention_exs.all())
        return interventions

    @property
    def interventions_normed(self):
        """ all interventions """
        interventions = self.interventions.filter(normed=True)
        return interventions

    @property
    def count(self):
        if self.interventions:
            return self.interventions.count()
        else:
            return 0


class AbstractIntervention(models.Model):
    category = models.CharField(
        choices=INTERVENTION_CHOICES, max_length=CHAR_MAX_LENGTH
    )
    choice = models.CharField(max_length=CHAR_MAX_LENGTH * 3, null=True)
    form = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, choices=INTERVENTION_FORM_CHOICES)
    application = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, choices=INTERVENTION_APPLICATION_CHOICES)
    time = models.FloatField(null=True)
    time_unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    substance = models.ForeignKey(Substance, null=True, on_delete=models.SET_NULL)
    route = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, choices=INTERVENTION_ROUTE_CHOICES)

    class Meta:
        abstract = True

    @property
    def category_class_data(self):
        """ Returns the full information about the characteristic.

        :return:
        """
        return INTERVENTION_DICT[self.category]

    @property
    def choices(self):
        return self.category_class_data.choices

    def __str__(self):
        return self.name


class AbstractInterventionMap(models.Model):
    choice_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    form_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    application_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    time_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    time_unit_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    substance_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    route_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    class Meta:
        abstract = True


class InterventionEx(
    Externable,
    ValueableNotBlank,
    ValueableMapNotBlank,
    AbstractIntervention,
    AbstractInterventionMap,
):
    """ Intervention (external curated layer)."""

    source = models.ForeignKey(
        DataFile,
        related_name="s_intervention_exs",
        null=True,
        on_delete=models.SET_NULL,
    )
    figure = models.ForeignKey(
        DataFile,
        related_name="f_intervention_exs",
        null=True,
        on_delete=models.SET_NULL,
    )

    interventionset = models.ForeignKey(
        InterventionSet, related_name="intervention_exs", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    name_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    objects = InterventionExManager()

    class Meta:
        unique_together = ("interventionset", "name", "name_map", "source")


class Intervention(Normalizable, ValueableNotBlank, AbstractIntervention):
    """ A concrete step/thing which is done to the group.

         In case of dosing/medication the actual dosing is stored in the Valueable.
         In case of a step without dosing, e.g., lifestyle intervention only the category is used.
      """

    ex = models.ForeignKey(
        InterventionEx,
        related_name="interventions",
        null=True,
        on_delete=models.CASCADE,
    )

    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    raw = models.ForeignKey("Intervention", related_name="norm", on_delete=models.CASCADE, null=True)
    normed = models.BooleanField(default=False)
    substance = models.ForeignKey(Substance, related_name="interventions", null=True, on_delete=models.PROTECT)

    @property
    def study(self):
        return self.ex.interventionset.study.name


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


class AbstractOutput(Normalizable):
    substance = models.ForeignKey(Substance, null=True, on_delete=models.SET_NULL)
    tissue = models.CharField(
        max_length=CHAR_MAX_LENGTH, choices=OUTPUT_TISSUE_DATA_CHOICES, null=True
    )
    pktype = models.CharField(max_length=CHAR_MAX_LENGTH, choices=PK_DATA_CHOICES)
    time = models.FloatField(null=True)
    time_unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)  # todo: validate in serializer

    class Meta:
        abstract = True


class AbstractOutputMap(models.Model):
    substance_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    tissue_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    pktype_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    time_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    time_unit_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    class Meta:
        abstract = True


class OutputEx(Externable, AbstractOutput, AbstractOutputMap, Valueable, ValueableMap):
    source = models.ForeignKey(
        DataFile, related_name="s_output_exs", null=True, on_delete=models.SET_NULL
    )
    figure = models.ForeignKey(
        DataFile, related_name="f_output_exs", null=True, on_delete=models.SET_NULL
    )
    outputset = models.ForeignKey(
        OutputSet, related_name="output_exs", on_delete=models.CASCADE, null=True
    )

    group = models.ForeignKey(Group, null=True, on_delete=models.SET_NULL)
    individual = models.ForeignKey(Individual, null=True, on_delete=models.SET_NULL)
    interventions = models.ManyToManyField(Intervention)

    group_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    individual_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    interventions_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    objects = OutputExManager()


class Output(ValueableNotBlank, AbstractOutput):
    """ Storage of data sets. """

    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.SET_NULL)
    individual = models.ForeignKey(
        Individual, null=True, blank=True, on_delete=models.SET_NULL
    )
    _interventions = models.ManyToManyField(Intervention)
    unit = models.CharField(max_length=CHAR_MAX_LENGTH)
    tissue = models.CharField(max_length=CHAR_MAX_LENGTH, choices=OUTPUT_TISSUE_DATA_CHOICES)
    substance = models.ForeignKey(Substance, related_name="outputs", on_delete=models.PROTECT)
    ex = models.ForeignKey(OutputEx, related_name="outputs", on_delete=models.CASCADE, null=True)

    # normalization into standertized units and added statistic
    raw = models.ForeignKey("Output", related_name="norm", on_delete=models.CASCADE, null=True)
    normed = models.BooleanField(default=False)

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

    def add_statistics(self):
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

    @property
    def study(self):

        try:
            return self.ex.outputset.study.name

        except AttributeError:
            return self.timecourse.ex.outputset.study.name

    @property
    def category_class_data(self):
        return PK_DATA_DICT[self.pktype]

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


class TimecourseEx(
    Externable,
    AbstractOutput,
    AbstractOutputMap,
    ValueableNotBlank,
    ValueableMapNotBlank,
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


class Timecourse(AbstractOutput):
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
    substance = models.ForeignKey(Substance, related_name="timecourses", on_delete=models.PROTECT)
    unit = models.CharField(max_length=CHAR_MAX_LENGTH)

    value = ArrayField(models.FloatField(null=True), null=True)
    mean = ArrayField(models.FloatField(null=True), null=True)
    median = ArrayField(models.FloatField(null=True), null=True)
    min = ArrayField(models.FloatField(null=True), null=True)
    max = ArrayField(models.FloatField(null=True), null=True)
    sd = ArrayField(models.FloatField(null=True), null=True)
    se = ArrayField(models.FloatField(null=True), null=True)
    cv = ArrayField(models.FloatField(null=True), null=True)
    time = ArrayField(models.FloatField(null=True), null=True)
    raw = models.ForeignKey("Timecourse", related_name="norm", on_delete=models.CASCADE, null=True)

    normed = models.BooleanField(default=False)
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

    @property
    def category_class_data(self):
        return PK_DATA_DICT[self.pktype]

    def normalize(self):
        """Normalizes timecourse."""
        if not self.is_norm:
            for key, value in self.norm_fields.items():
                if value is not None:
                    list_norm_values = list(self.category_class_data.normalize(value, self.unit).magnitude)
                    setattr(self, key, list_norm_values)
            self.unit = self.category_class_data.norm_unit(self.unit).__str__()

        # for time_unit
        if not self.time_unit == TIME_NORM_UNIT:
            p_time_unit = self.category_class_data.p_unit(self.time_unit)
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
        weight_categories = self.related_subject.characteristica_all_normed.filter(category="weight")
        return weight_categories

    def get_dosing(self):

        try:
            dosing_category = self.interventions.get(normed=True, category="dosing")
            return dosing_category

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
            if DOSING_RESTRICTED.is_valid_unit(dosing.unit):
                p_unit_dosing = self.category_class_data.p_unit(dosing.unit)
                p_unit_concentration = self.category_class_data.p_unit(pk_dict["c_unit"])
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

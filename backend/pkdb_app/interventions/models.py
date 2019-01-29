
"""
Describe Interventions and Output (i.e. define the characteristics of the
group or individual).
"""
import copy
import numpy as np
import math
import pandas as pd

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.apps import apps


from ..subjects.models import Group, DataFile, Individual

from pkdb_app.interventions.managers import (
    InterventionSetManager,
    OutputSetManager,
    OutputExManager,
    TimecourseExManager,
    InterventionExManager,
    OutputManager,
)
from pkdb_app.normalization import get_cv, get_se, get_sd
from ..behaviours import (
    Valueable,
    ValueableMap,
    Externable,
    CHAR_MAX_LENGTH_LONG,
    ValueableNotBlank,
    ValueableMapNotBlank,
)
from ..categoricals import (
    INTERVENTION_CHOICES,
    INTERVENTION_ROUTE_CHOICES,
    INTERVENTION_FORM_CHOICES,
    INTERVENTION_APPLICATION_CHOICES,
    PK_DATA_CHOICES,
    OUTPUT_TISSUE_DATA_CHOICES, PK_DATA_DICT, INTERVENTION_DICT, TIME_NORM_UNIT)
from ..units import UNITS_CHOICES, TIME_UNITS_CHOICES, UNIT_CONVERSIONS_DICT

from ..utils import CHAR_MAX_LENGTH
from pkdb_app.analysis.pharmacokinetic import _auc, _aucinf, _kel, _vd, f_pk
from ..substances import SUBSTANCES_DATA_CHOICES

# -------------------------------------------------
# Substance
# -------------------------------------------------
class Substance(models.Model):
    """ Substances have to be in a different table, so that
    than be uniquely defined.

    Has to be extended via ontology (Ontologable)
    """
    name = models.CharField(max_length=CHAR_MAX_LENGTH, choices=SUBSTANCES_DATA_CHOICES)

    def __str__(self):
        return self.name


    @property
    def outputs_final(self):
        return self.outputs.filter(final=True)

    @property
    def timecourses_final(self):
        return self.timecourses.filter(final=True)

    @property
    def interventions_final(self):
        return self.interventions.filter(final=True)

    #@property
    #def all_studies(self):
        #Study = apps.get_model('studies', 'Study')


        #studies = [study for study in Study.objects.all() if self in study.all_substances.all()]

        #Intervention.objects.
        #studies = studies | Study.objects.filter(interventionset__intervention_exs__interventions__in = self.interventions)
        #studies = studies | Study.objects.filter( reduce(lambda x, y: x | y, [Q(interventionset__interventions__contains=intervention) for intervention in #self.interventions.all()]))


        #return studies
        #return Study.objects.filter(all_substances__contains = self)



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
    def interventions_final(self):
        """ all interventions """
        interventions = self.interventions.filter(final=True)
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
    form = models.CharField(
        max_length=CHAR_MAX_LENGTH, null=True, choices=INTERVENTION_FORM_CHOICES
    )
    application = models.CharField(
        max_length=CHAR_MAX_LENGTH, null=True, choices=INTERVENTION_APPLICATION_CHOICES
    )
    time = models.FloatField(null=True)
    time_unit = models.CharField(
        max_length=CHAR_MAX_LENGTH, null=True, choices=TIME_UNITS_CHOICES
    )
    substance = models.ForeignKey(Substance, null=True, on_delete=models.SET_NULL)
    route = models.CharField(
        max_length=CHAR_MAX_LENGTH, null=True, choices=INTERVENTION_ROUTE_CHOICES
    )

    class Meta:
        abstract = True

    @property
    def intervention_data(self):
        """ Returns the full information about the characteristic.

        :return:
        """
        return INTERVENTION_DICT[self.category]

    @property
    def choices(self):
        return self.intervention_data.choices

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


class Intervention(ValueableNotBlank, AbstractIntervention):
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
    final = models.BooleanField(default=False)
    substance = models.ForeignKey(Substance, related_name="interventions",null=True, on_delete=models.PROTECT)


    @property
    def norm_unit(self):
        return self.intervention_data.units.get(self.unit)

    @property
    def study(self):
        return self.ex.interventionset.study.name

    @property
    def is_norm(self):
        norm_unit = self.norm_unit
        return norm_unit is None

    @property
    def is_convertible(self):
        conversion_key = f"[{self.unit}] -> [{self.norm_unit}]"
        conversion = UNIT_CONVERSIONS_DICT.get(conversion_key)
        return conversion is not None

    @property
    def norm_fields(self):
        return {"value": self.value, "mean": self.mean, "median": self.median, "min": self.min, "max": self.max,
                "sd": self.sd, "se": self.se}

    def normalize(self):
        if all([not self.is_norm, self.is_convertible]):
            conversion_key = f"[{self.unit}] -> [{self.norm_unit}]"
            self.unit = self.norm_unit

            conversion = UNIT_CONVERSIONS_DICT.get(conversion_key)
            for key, value in self.norm_fields.items():
                if not value is None:
                        setattr(self, key, conversion.apply_conversion(value))


# -------------------------------------------------
# OUTPUTS
# -------------------------------------------------
class OutputSet(models.Model):
    objects = OutputSetManager()

    @property
    def outputs(self):
        outputs = Output.objects.filter(ex__in=self.output_exs.all())
        return outputs

    @property
    def outputs_final(self):
        outputs = self.outputs.filter(final=True)
        return outputs


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
    def timecourses_final(self):
        timecourses = self.timecourses.filter(final=True)
        return timecourses

    @property
    def count_timecourses(self):
        if self.timecourses:
            return self.timecourses.count()
        else:
            return 0


class AbstractOutput(models.Model):

    substance = models.ForeignKey(Substance,null=True, on_delete=models.SET_NULL)
    tissue = models.CharField(
        max_length=CHAR_MAX_LENGTH, choices=OUTPUT_TISSUE_DATA_CHOICES, null=True
    )
    pktype = models.CharField(
        max_length=CHAR_MAX_LENGTH, choices=PK_DATA_CHOICES, null=True
    )
    time = models.FloatField(null=True)
    time_unit = models.CharField(
        max_length=CHAR_MAX_LENGTH, null=True, choices=TIME_UNITS_CHOICES
    )

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
    unit = models.CharField(choices=UNITS_CHOICES, max_length=CHAR_MAX_LENGTH)
    tissue = models.CharField(max_length=CHAR_MAX_LENGTH, choices=OUTPUT_TISSUE_DATA_CHOICES)
    substance = models.ForeignKey(Substance,related_name="outputs",on_delete=models.PROTECT)
    ex = models.ForeignKey(OutputEx, related_name="outputs", on_delete=models.CASCADE)
    raw = models.ForeignKey("Output",related_name="norm",on_delete=models.CASCADE,null=True)

    final = models.BooleanField(default=False)
    timecourse = models.ForeignKey("Timecourse",on_delete=models.CASCADE,related_name="pharmacokinetics", null=True)
    objects = OutputManager()

    @property
    def interventions(self):
        interventions = self._interventions
        if interventions.all():
            return interventions
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
        return self.ex.outputset.study.name

    @property
    def pk_data(self):
        return PK_DATA_DICT[self.pktype]

    @property
    def norm_unit(self):
        return self.pk_data.units.get(self.unit)

    @property
    def is_norm(self):
        norm_unit = self.norm_unit
        return norm_unit is None

    @property
    def norm_fields(self):
        return {"value": self.value, "mean": self.mean, "median": self.median, "min": self.min, "max": self.max,
                "sd": self.sd, "se": self.se}

    @property
    def is_convertible(self):
        conversion_key = f"[{self.unit}] -> [{self.norm_unit}]"
        conversion = UNIT_CONVERSIONS_DICT.get(conversion_key)
        return conversion is not None

    def normalize(self):

        if all([not self.is_norm, self.is_convertible]):
            conversion_key = f"[{self.unit}] -> [{self.norm_unit}]"
            self.unit = self.norm_unit
            conversion = UNIT_CONVERSIONS_DICT.get(conversion_key)

            for key,value in self.norm_fields.items():
                if not value is None:
                        setattr(self,key,conversion.apply_conversion(value))


    # for elastic search. NaNs are not allowed in elastic search

    def null_attr(self,attr):
        value = getattr(self,attr)
        if value not in ['nan','NA','NAN','na',np.NaN, None] and not math.isnan(value):
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
    substance = models.ForeignKey(Substance,related_name="timecourses", on_delete=models.PROTECT)
    unit = models.CharField(choices=UNITS_CHOICES, max_length=CHAR_MAX_LENGTH)

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

    final = models.BooleanField(default=False)
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
        except:
            return None

    def add_statistics(self):
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
    def pk_data(self):
        return PK_DATA_DICT[self.pktype]

    @property
    def norm_unit(self):
        return self.pk_data.units.get(self.unit)

    @property
    def norm_time_unit(self):
        return TIME_NORM_UNIT

    @property
    def is_norm(self):
        return self.norm_unit is None


    @staticmethod
    def is_convertible(unit,norm_unit):
        conversion_key = f"[{unit}] -> [{norm_unit}]"
        conversion = UNIT_CONVERSIONS_DICT.get(conversion_key)
        return conversion is not None



    @property
    def norm_fields(self):
        return {"value": self.value, "mean": self.mean, "median": self.median, "min": self.min, "max": self.max,
                      "sd": self.sd, "se": self.se}



    def normalize(self):
        if all([not self.is_norm, self.is_convertible(self.unit,self.norm_unit)]):
            conversion_key = f"[{self.unit}] -> [{self.norm_unit}]"
            self.unit = self.norm_unit
            conversion = UNIT_CONVERSIONS_DICT.get(conversion_key)
            for key, value in self.norm_fields.items():
                if not value is None:
                    setattr(self, key, list(conversion.apply_conversion(value)))

        #for time_unit
        if self.is_convertible(self.time_unit, self.norm_time_unit):
            conversion_key = f"[{self.time_unit}] -> [{self.norm_time_unit}]"
            self.time_unit = self.norm_time_unit
            conversion = UNIT_CONVERSIONS_DICT.get(conversion_key)
            self.time = list(conversion.apply_conversion(self.time))


        # for elastic search. NaNs are not allowed in elastic search

    @staticmethod
    def _any_not_json(value):
        return any([np.isnan(value), np.isinf(value), np.isneginf(value)])

    def null_attr(self, attr):
        value_list = getattr(self, attr)
        if value_list:
            value_list_none = [ None if self._any_not_json(value) else value for value in value_list ]
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
        self.related_subject.characteristica.filter(category="weight")

    def calculate_pharamcokinatics(self):
        pk_data = self.get_pharamcokinetic_data()
        #return f_pk(t=pk_data["t"],c=pk_data["c"],compound=self.substance.name,dose=)

    def get_pharamcokinetic_data(self):
        pk_data = {}

        if self.value:
            pk_data["c"] = self.value
            try:
                pk_data["weight"] = self.individual.characteristica.get(category="weight").value
            except ObjectDoesNotExist:
                pk_data["weight"] = np.NaN

        elif self.mean:
            pk_data["c"] = self.mean

            try:
                weight = self.group.characteristica_all.get(category="weight")
                pk_data["weight"] = weight.get("mean")
                pk_data["bodyweight_unit"] = weight.unit

            except ObjectDoesNotExist:
                pk_data["weight"] = np.NaN
        try:
            dosing = self.interventions.get(category="dosing")
            pk_data["dose"] = dosing.value
            pk_data["dosing_unit"] =  dosing.unit

        except ObjectDoesNotExist:
            pk_data["dose"] = np.NaN
            pk_data["dosing_unit"] = np.NaN

            pk_data["t"] = self.time

    @property
    def calculate_auc_end(self):
        output_data = {}
        output_data["substance"] = str(self.substance)
        output_data["tissue"] = str(self.tissue)
        output_data["pktype"] = "auc_end"
        output_data["time"] = self.time[-1]
        if self.value:
            output_data["value"] = self.try_type_error(self.time,self.value,_auc)
        if self.mean:
            output_data["mean"] = self.try_type_error(self.time,self.mean,_auc)

        if self.median:
            output_data["median"] = self.try_type_error(self.time,self.median,_auc)

        output_data["unit"] = f"({self.unit})*{self.time_unit}"



        array_fields = [
                "value",
                "mean",
                "median",
                "min",
                "max",
                "sd",
                "se",
                "cv",
                "time",
            ]
        for field in array_fields:
            value = output_data.get(field, None)
            if value:
                if self._any_not_json(value):
                    output_data[field] = None

        return output_data

    @property
    def auc_end(self):
        instance_calc_end = self.calculate_auc_end
        for value in ['value','mean','median']:
            if instance_calc_end.get(value):
                return instance_calc_end[value]



    @staticmethod
    def try_type_error(time, array, method):
        try:
            value = method(np.array(time),np.array(array))

        except TypeError:
            value = None

        return value

    @property
    def calculate_auc_inf(self):
        output_data = {}
        output_data["substance"] = str(self.substance)
        output_data["tissue"] = str(self.tissue)
        output_data["pktype"] = "auc_inf"
        if self.value:
            output_data["value"] = self.try_type_error(self.time, self.value, _aucinf)
        if self.mean:
            output_data["mean"] = self.try_type_error(self.time, self.mean, _aucinf)

        if self.median:
            output_data["median"] = self.try_type_error(self.time, self.median, _aucinf)

        output_data["unit"] = f"({self.unit})*{self.time_unit}"



        array_fields = [
            "value",
            "mean",
            "median",
            "min",
            "max",
            "sd",
            "se",
            "cv",
            "time",
        ]
        for field in array_fields:
            value = output_data.get(field, None)
            if value:
                if self._any_not_json(value):
                    output_data[field] = None
        return output_data


    def calculate_kel(self):
        output_data = {}
        output_data["substance"] = str(self.substance)
        output_data["tissue"] = str(self.tissue)
        output_data["pktype"] = "kel"
        if self.value:
            output_data["value"] = self.try_type_error(self.time, self.value, _kel)
        if self.mean:
            output_data["mean"] = self.try_type_error(self.time, self.mean, _kel)

        if self.median:
            output_data["median"] = self.try_type_error(self.time, self.median, _kel)

        output_data["unit"] = f"({self.unit})/{self.time_unit}"

        array_fields = [
            "value",
            "mean",
            "median",
            "min",
            "max",
            "sd",
            "se",
            "cv",
            "time",
        ]
        for field in array_fields:
            value = output_data.get(field, None)
            if value:
                if self._any_not_json(value):
                    output_data[field] = None

        return output_data

    @property
    def kel(self):
        instance_calc_kel = self.calculate_kel()
        for value in ['value', 'mean', 'median']:
            if instance_calc_kel.get(value):
                return instance_calc_kel[value]

    @property
    def calculate_vd(self):
            output_data = {}
            output_data["substance"] = str(self.substance)
            output_data["tissue"] = str(self.tissue)
            output_data["pktype"] = "vd"
            if self.value:
                output_data["value"] = self.try_type_error(self.time, self.value, _vd)
            if self.mean:
                output_data["mean"] = self.try_type_error(self.time, self.mean, _vd)
            if self.median:
                output_data["median"] = self.try_type_error(self.time, self.median, _vd)

            output_data["unit"] = f"({self.unit})/{self.time_unit}"

            array_fields = [
                "value",
                "mean",
                "median",
                "min",
                "max",
                "sd",
                "se",
                "cv",
                "time",
            ]
            for field in array_fields:
                value = output_data.get(field, None)
                if value:
                    if self._any_not_json(value):
                        output_data[field] = None

            return output_data
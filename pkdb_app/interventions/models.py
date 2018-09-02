
"""
Describe Interventions and Output (i.e. define the characteristics of the
group or individual).
"""

from django.db import models
from django.contrib.postgres.fields import ArrayField
from pkdb_app.interventions.managers import InterventionSetManager, OutputSetManager, OutputExManager, \
    TimecourseExManager, InterventionExManager,  OutputManager
from pkdb_app.normalization import get_cv, get_se, get_sd
from ..behaviours import Valueable, ValueableMap, Externable, CHAR_MAX_LENGTH_LONG
from ..categoricals import INTERVENTION_CHOICES, TIME_UNITS_CHOICES, \
    INTERVENTION_ROUTE_CHOICES, INTERVENTION_FORM_CHOICES, INTERVENTION_APPLICATION_CHOICES, PK_DATA_CHOICES, \
    SUBSTANCES_DATA_CHOICES, OUTPUT_TISSUE_DATA_CHOICES, UNITS_CHOICES
from ..subjects.models import Group, IndividualEx, DataFile, GroupEx, Individual
from ..utils import CHAR_MAX_LENGTH
import numpy as np

# -------------------------------------------------
# Substance
# -------------------------------------------------
class Substance(models.Model):
    """ Substances have to be in a different table, so that
    than be uniquely defined.

    Has to be extended via ontology (Ontologable)
    """
    name = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True, choices=SUBSTANCES_DATA_CHOICES)

    # ontologies: has set of defined values: is, CHEBI:27732

    def __str__(self):
        return self.name


# -------------------------------------------------
# Intervention
# -------------------------------------------------
class InterventionSet(models.Model):
    objects = InterventionSetManager()

    @property
    def interventions(self):
        interventions = Intervention.objects.filter(ex__in=self.intervention_exs.all())
        return interventions


class AbstractIntervention(models.Model):
    category = models.CharField(choices=INTERVENTION_CHOICES, max_length=CHAR_MAX_LENGTH)
    choice = models.CharField(max_length=CHAR_MAX_LENGTH * 3, null=True, blank=True)
    form = models.CharField(max_length=CHAR_MAX_LENGTH, blank=True, null=True, choices=INTERVENTION_FORM_CHOICES)
    application = models.CharField(max_length=CHAR_MAX_LENGTH, blank=True, null=True, choices=INTERVENTION_APPLICATION_CHOICES)
    time = models.FloatField(null=True, blank=False)
    time_unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True, choices=TIME_UNITS_CHOICES)
    substance = models.ForeignKey(Substance, null=True, blank=False, on_delete=models.SET_NULL)
    route = models.CharField(max_length=CHAR_MAX_LENGTH, blank=True, null=True, choices=INTERVENTION_ROUTE_CHOICES)

    class Meta:
        abstract = True

    @property
    def intervention_data(self):
        """ Returns the full information about the characteristic.

        :return:
        """
        return INTERVENTION_CHOICES[self.category]

    @property
    def choices(self):
        return self.intervention_data.choices

    def __str__(self):
        return self.name


class AbstractInterventionMap(models.Model):
    choice_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    form_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    application_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    time_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    time_unit_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    substance_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    route_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)

    class Meta:
        abstract = True


class InterventionEx(Externable, Valueable, ValueableMap, AbstractIntervention, AbstractInterventionMap):
    """ Intervention (external curated layer)."""
    source = models.ForeignKey(DataFile, related_name="s_intervention_exs", null=True, blank=True,
                               on_delete=models.SET_NULL)
    figure = models.ForeignKey(DataFile, related_name="f_intervention_exs", null=True, blank=True,
                               on_delete=models.SET_NULL)

    interventionset = models.ForeignKey(InterventionSet, related_name="intervention_exs", on_delete=models.CASCADE)
    name = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    name_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)

    objects = InterventionExManager()

    class Meta:
        unique_together = ('interventionset', 'name', 'name_map', 'source')


class Intervention(Valueable, AbstractIntervention):
    """ A concrete step/thing which is done to the group.

         In case of dosing/medication the actual dosing is stored in the Valueable.
         In case of a step without dosing, e.g., lifestyle intervention only the category is used.
      """
    ex = models.ForeignKey(InterventionEx, related_name="interventions", null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=CHAR_MAX_LENGTH)

    # TODO: unique together  unique_together = ('ex__interventionset', 'name')


# -------------------------------------------------
# RESULTS
# -------------------------------------------------
class OutputSet(models.Model):
    objects = OutputSetManager()

    @property
    def outputs(self):
        outputs = Output.objects.filter(ex__in=self.output_exs.all())
        return outputs

    @property
    def timecourses(self):
        timecourses = Timecourse.objects.filter(ex__in=self.timecourse_exs.all())
        return timecourses


class AbstractOutput(models.Model):

    substance = models.ForeignKey(Substance, null=True, blank=True,on_delete=models.SET_NULL)
    tissue = models.CharField(max_length=CHAR_MAX_LENGTH,choices=OUTPUT_TISSUE_DATA_CHOICES ,null=True, blank=True)
    pktype = models.CharField(max_length=CHAR_MAX_LENGTH, choices=PK_DATA_CHOICES, null=True, blank=True)
    time = models.FloatField(null=True, blank=True)
    time_unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True, choices=TIME_UNITS_CHOICES)

    class Meta:
        abstract = True


class AbstractOutputMap(models.Model):

    substance_map = models.CharField(max_length=CHAR_MAX_LENGTH_LONG,null=True, blank=True)
    tissue_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    pktype_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    time_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    time_unit_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)

    class Meta:
        abstract = True


class OutputEx(Externable, AbstractOutput, AbstractOutputMap, Valueable, ValueableMap):

    source = models.ForeignKey(DataFile, related_name="s_output_exs", null=True, blank=True,on_delete=models.SET_NULL)
    figure = models.ForeignKey(DataFile, related_name="f_output_exs", null=True, blank=True,on_delete=models.SET_NULL)
    outputset = models.ForeignKey(OutputSet, related_name="output_exs", on_delete=models.CASCADE, null=True, blank=True)

    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.SET_NULL)
    individual = models.ForeignKey(Individual, null=True, blank=True, on_delete=models.SET_NULL)
    interventions = models.ManyToManyField(Intervention)

    group_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    individual_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    interventions_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)

    objects = OutputExManager()




class Output(Valueable, AbstractOutput):

    """ Storage of data sets. """
    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.SET_NULL)
    individual = models.ForeignKey(Individual, null=True, blank=True, on_delete=models.SET_NULL)
    interventions = models.ManyToManyField(Intervention)
    unit = models.CharField(choices=UNITS_CHOICES, max_length=CHAR_MAX_LENGTH)


    ex = models.ForeignKey(OutputEx, related_name="outputs", on_delete=models.CASCADE)

    objects = OutputManager()

    def save(self, *args, **kwargs):
        if self.group:
            if not self.sd:
                self.sd = get_sd(se=self.se, count = self.group.count, mean=self.mean, cv=self.cv)
            if not self.se:
                self.se = get_se(sd=self.sd, count = self.group.count, mean=self.mean, cv=self.cv)
            if not self.cv:
                self.cv = get_cv(se=self.se, count = self.group.count, mean=self.mean, sd=self.sd)
        super().save(*args, **kwargs)


class TimecourseEx(Externable, AbstractOutput, AbstractOutputMap, Valueable, ValueableMap):
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

    source = models.ForeignKey(DataFile, related_name="s_timecourse_exs", null=True, blank=True, on_delete=models.SET_NULL)
    figure = models.ForeignKey(DataFile, related_name="f_timecourse_exs", null=True, blank=True, on_delete=models.SET_NULL)
    outputset = models.ForeignKey(OutputSet, related_name="timecourse_exs", on_delete=models.CASCADE, null=True, blank=True)

    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.SET_NULL)
    individual = models.ForeignKey(Individual, null=True, blank=True, on_delete=models.SET_NULL)
    interventions = models.ManyToManyField(Intervention)

    group_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    individual_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    interventions_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)

    objects = TimecourseExManager()

# django-numpy

class Timecourse(AbstractOutput):
    """ Storing of time course data.

    Store a binary blop of the data (json, pandas dataframe or similar, backwards compatible).
    """
    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.CASCADE)
    individual = models.ForeignKey(Individual, null=True, blank=True, on_delete=models.CASCADE)
    interventions = models.ManyToManyField(Intervention)
    ex = models.ForeignKey(TimecourseEx, related_name="timecourses", on_delete=models.CASCADE)
    unit = models.CharField(choices=UNITS_CHOICES, max_length=CHAR_MAX_LENGTH)

    value = ArrayField(models.FloatField(null=True, blank=True),null=True,blank=True)
    mean = ArrayField(models.FloatField(null=True, blank=True), null=True,blank=True)
    median = ArrayField(models.FloatField(null=True, blank=True), null=True,blank=True)
    min = ArrayField(models.FloatField(null=True, blank=True), null=True,blank=True)
    max = ArrayField(models.FloatField(null=True, blank=True), null=True,blank=True)
    sd = ArrayField(models.FloatField(null=True, blank=True), null=True,blank=True)
    se = ArrayField(models.FloatField(null=True, blank=True), null=True,blank=True)
    cv = ArrayField(models.FloatField(null=True, blank=True), null=True,blank=True)
    time = ArrayField(models.FloatField(null=True, blank=True), null=True,blank=True)

    objects = OutputManager()

    def save(self, *args, **kwargs):

        if self.group:
            if not self.sd:
                sd = get_sd(se=self.se, count=self.group.count, mean=self.mean, cv=self.cv)
                if isinstance(sd,np.ndarray):
                    self.sd = list(sd)
            if not self.se:
                se = get_se(sd=self.sd, count=self.group.count, mean=self.mean, cv=self.cv)
                if isinstance(se,np.ndarray):
                    self.se = list(se)
            if not self.cv:
                cv = get_cv(se=self.se, count=self.group.count, mean=self.mean, sd=self.sd)
                if isinstance(cv,np.ndarray):
                    self.cv = list(cv)
            super().save(*args, **kwargs)

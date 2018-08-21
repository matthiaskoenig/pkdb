
"""
Describe Interventions and Output (i.e. define the characteristics of the
group or individual).
"""

from django.db import models

from pkdb_app.interventions.managers import InterventionSetManager, OutputSetManager, OutputManager
from ..behaviours import Valueable, ValueableMap
from ..categoricals import INTERVENTION_CHOICES, TIME_UNITS_CHOICES, \
    INTERVENTION_ROUTE_CHOICES, INTERVENTION_FORM_CHOICES, INTERVENTION_APPLICATION_CHOICES, PK_DATA_CHOICES, \
    SUBSTANCES_DATA_CHOICES, OUTPUT_TISSUE_DATA_CHOICES
from ..subjects.models import Group, IndividualEx, DataFile
from ..utils import CHAR_MAX_LENGTH


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


class AbstractIntervention(models.Model):
    form = models.CharField(max_length=CHAR_MAX_LENGTH, blank=True, null=True, choices=INTERVENTION_FORM_CHOICES)
    application = models.CharField(max_length=CHAR_MAX_LENGTH, blank=True, null=True,
                                   choices=INTERVENTION_APPLICATION_CHOICES)  # application: # how timing ['single dose', 'multiple doses', 'continuous injection']

    time = models.FloatField(null=True,
                             blank=False)  # application_time: # when exactly [h] (for multiple times create multiple MedicationSteps)
    time_unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True, choices=TIME_UNITS_CHOICES)

    substance = models.ForeignKey(Substance, null=True, blank=False,
                                  on_delete=models.SET_NULL)  # substance: # what was given ['
    route = models.CharField(max_length=CHAR_MAX_LENGTH, blank=True, null=True,
                             choices=INTERVENTION_ROUTE_CHOICES)  # route: # where ['oral', 'iv']

    category = models.CharField(choices=INTERVENTION_CHOICES, max_length=CHAR_MAX_LENGTH)
    choice = models.CharField(max_length=CHAR_MAX_LENGTH * 3, null=True,blank=True)

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


class InterventionEx(Valueable,ValueableMap,AbstractIntervention):
    """ Intervention (external curated layer).

       """
    source = models.ForeignKey(DataFile, related_name="intervention_exs", null=True, blank=True,
                               on_delete=models.SET_NULL)
    format = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    figure = models.ForeignKey(DataFile, related_name="intervention_exs", null=True, blank=True,
                               on_delete=models.SET_NULL)

    interventionset = models.ForeignKey(InterventionSet, related_name="interventions_exs", on_delete=models.CASCADE)
    name = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    name_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)

    class Meta:
        unique_together = ('interventionset', 'name', 'name_map', 'source')


class Intervention(Valueable, AbstractIntervention):
    """ A concrete step/thing which is done to the group.

         In case of dosing/medication the actual dosing is stored in the Valueable.
         In case of a step without dosing, e.g., lifestyle intervention only the category is used.
      """
    ex = models.ForeignKey(IndividualEx, related_name="interventions", null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=CHAR_MAX_LENGTH)

    class Meta:
        unique_together = ('ex__interventionset', 'name')


# -------------------------------------------------
# RESULTS
# -------------------------------------------------


class OutputSet(models.Model):
    objects = OutputSetManager()


class AbstractOutput(models.Model):

    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.CASCADE)
    individual = models.ForeignKey(IndividualEx, null=True, blank=True, on_delete=models.CASCADE)
    interventions = models.ManyToManyField(Intervention)
    substance = models.ForeignKey(Substance, null=True, blank=True,on_delete=models.SET_NULL)
    tissue = models.CharField(max_length=CHAR_MAX_LENGTH,choices=OUTPUT_TISSUE_DATA_CHOICES ,null=True, blank=True)
    pktype = models.CharField(max_length=CHAR_MAX_LENGTH, choices=PK_DATA_CHOICES, null=True, blank=True)
    time = models.FloatField(null=True, blank=True)
    time_unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True, choices=TIME_UNITS_CHOICES)

    class Meta:
        abstract = True


class AbstractOutputMap(models.Model):

    group_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    individual_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    interventions_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    substance_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    tissue_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    subset_map = models.CharField(max_length=CHAR_MAX_LENGTH,null=True, blank=True)
    pktype_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    time_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)
    time_unit_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True)

    class Meta:
        abstract = True


class OutputEx(AbstractOutput,AbstractOutputMap,ValueableMap,Valueable):
    source = models.ForeignKey(DataFile, related_name="output_exs", null=True, blank=True,on_delete=models.SET_NULL)
    figure = models.ForeignKey(DataFile, related_name="output_exs", null=True, blank=True,on_delete=models.SET_NULL)
    outputset = models.ForeignKey(OutputSet, related_name="output_exs", on_delete=models.CASCADE, null=True, blank=True)


class Output(Valueable, AbstractOutput):

    """ Storage of data sets. """

    ex = models.ForeignKey(OutputEx, related_name="outputs", on_delete=models.CASCADE)
    objects = OutputManager()


class TimecourseEx(AbstractOutput,AbstractOutputMap,ValueableMap,Valueable):

    source = models.ForeignKey(DataFile, related_name="timecourse_exs", null=True, blank=True, on_delete=models.SET_NULL)
    figure = models.ForeignKey(DataFile, related_name="timecourse_exs", null=True, blank=True, on_delete=models.SET_NULL)
    outputset = models.ForeignKey(OutputSet, related_name="timecourse_exs", on_delete=models.CASCADE, null=True, blank=True)



class Timecourse(Valueable, AbstractOutput):
    """ Storing of time course data.

    Store a binary blop of the data (json, pandas dataframe or similar, backwards compatible).
    """
    ex = models.ForeignKey(TimecourseEx, related_name="outputs", on_delete=models.CASCADE)
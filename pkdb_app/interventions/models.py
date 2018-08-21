
"""
Describe Interventions and Output (i.e. define the characteristics of the
group or individual).
"""

from django.db import models

from pkdb_app.interventions.managers import InterventionSetManager, OutputSetManager, OutputManager
from ..behaviours import Valueable, ValueableMap, Sourceable
from ..categoricals import INTERVENTION_CHOICES, TIME_UNITS_CHOICES, \
    INTERVENTION_ROUTE_CHOICES, INTERVENTION_FORM_CHOICES, INTERVENTION_APPLICATION_CHOICES, PK_DATA_CHOICES, \
    SUBSTANCES_DATA_CHOICES, OUTPUT_TISSUE_DATA_CHOICES
from ..subjects.models import Group, Individual, Set, DataFile
from ..utils import CHAR_MAX_LENGTH

# -------------------------------------------------
# Intervention
# -------------------------------------------------

# Important to store raw DataSets & Corresponding Figures/Tables
#

# How can data sets look
# - CharacteristicValues (value +- SE in n subjects) -> e.g. pharmacokinetics data
# - mean timecourse +- SE/SD
# - individual time courses

# Simple pharmacokinetics


# How to represent the dosing?
# Add separate class? extension of model?

#####################################
#new


class Substance(models.Model):
    """ Substances have to be in a different table, so that
    than be uniquely defined.

    Has to be extended via ontology (Ontologable)

    """
    name = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True, choices=SUBSTANCES_DATA_CHOICES)

    #name # example caffeine
    # ontologies: has set of defined values: is, CHEBI:27732

    def __str__(self):
        return self.name


class InterventionSet(Set):
    objects = InterventionSetManager()

class Intervention(Valueable, models.Model):
    """ A concrete step/thing which is done to the group.

         In case of dosing/medication the actual dosing is stored in the Valueable.
         In case of a step without dosing, e.g., lifestyle intervention only the category is used.
      """
    name = models.CharField(max_length=CHAR_MAX_LENGTH)

    interventionset = models.ForeignKey(InterventionSet, related_name="interventions", on_delete=models.CASCADE)
    substance = models.ForeignKey(Substance, null=True, blank=False,
                                  on_delete=models.SET_NULL)  # substance: # what was given ['
    route = models.CharField(max_length=CHAR_MAX_LENGTH, blank=True, null=True,
                             choices=INTERVENTION_ROUTE_CHOICES)  # route: # where ['oral', 'iv']
    form = models.CharField(max_length=CHAR_MAX_LENGTH, blank=True, null=True, choices=INTERVENTION_FORM_CHOICES)
    application = models.CharField(max_length=CHAR_MAX_LENGTH, blank=True, null=True,
                                   choices=INTERVENTION_APPLICATION_CHOICES)  # application: # how timing ['single dose', 'multiple doses', 'continuous injection']
    time = models.FloatField(null=True,
                             blank=False)  # application_time: # when exactly [h] (for multiple times create multiple MedicationSteps)
    time_unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True, choices=TIME_UNITS_CHOICES)

    ######
    # probably should be deleted
    category = models.CharField(max_length=CHAR_MAX_LENGTH, choices=INTERVENTION_CHOICES, null=True, blank=True)

    # choice = models.CharField(max_length=CHAR_MAX_LENGTH, null=True,blank=True)

    @property
    def intervention_data(self):
        """ Returns the full information about the characteristic.

        :return:
        """
        return INTERVENTION_CHOICES[self.category]

    @property
    def choices(self):
        return self.intervention_data.choices

    class Meta:
        unique_together = ('interventionset', 'name')

    def __str__(self):
        return self.name



# -----------------
# RESULTS
# -----------------
#

class OutputSet(Set):
    objects = OutputSetManager()

class BaseOutput(models.Model):
    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.CASCADE)
    individual = models.ForeignKey(Individual, null=True, blank=True, on_delete=models.CASCADE)
    #intervention = models.ForeignKey(Intervention,null=True, blank=True, on_delete=False)
    interventions = models.ManyToManyField(Intervention)
    substance = models.ForeignKey(Substance, null=True, blank=True,on_delete=models.SET_NULL)
    tissue = models.CharField(max_length=CHAR_MAX_LENGTH,choices=OUTPUT_TISSUE_DATA_CHOICES ,null=True, blank=True)
    pktype = models.CharField(max_length=CHAR_MAX_LENGTH, choices=PK_DATA_CHOICES, null=True, blank=True)
    time = models.FloatField(null=True, blank=True)
    time_unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, blank=True, choices=TIME_UNITS_CHOICES)

    class Meta:
        abstract = True

class BaseOutputMap(models.Model):
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


class CleanOutput(Sourceable,Valueable,BaseOutput,models.Model):

    """ Storage of data sets. """

    source = models.ForeignKey(DataFile, related_name="c_output_sources", null=True, blank=True,on_delete=models.SET_NULL)
    figure = models.ForeignKey(DataFile, related_name="c_output_figures", null=True, blank=True,on_delete=models.SET_NULL)
    outputset = models.ForeignKey(OutputSet, related_name="c_outputs", on_delete=models.CASCADE, null=True, blank=True)

    raw = models.ForeignKey("Output", related_name="cleaned", on_delete=models.CASCADE)


class Output(Sourceable,ValueableMap,Valueable,BaseOutputMap,BaseOutput,models.Model):

    """ Storage of data sets. """

    source = models.ForeignKey(DataFile, related_name="output_sources",null=True,blank=True, on_delete=models.SET_NULL)
    figure = models.ForeignKey(DataFile, related_name="output_figures",null=True,blank=True, on_delete=models.SET_NULL)
    outputset = models.ForeignKey(OutputSet, related_name="outputs", on_delete=models.CASCADE,null=True, blank=True)
    objects = OutputManager()

class CleanTimecourse(Sourceable,Valueable,BaseOutput,models.Model):

    source = models.ForeignKey(DataFile, related_name="c_timecourse_sources", null=True, blank=True,
                               on_delete=models.SET_NULL)
    figure = models.ForeignKey(DataFile, related_name="c_timecourse_figures", null=True, blank=True,
                               on_delete=models.SET_NULL)
    outputset = models.ForeignKey(OutputSet, related_name="c_timecourses", on_delete=models.CASCADE, null=True,
                                  blank=True)

    raw = models.ForeignKey("Timecourse", related_name="cleaned", null=True, on_delete=models.CASCADE)



class Timecourse(Sourceable,ValueableMap,Valueable,BaseOutputMap,BaseOutput,models.Model):
    """ Storing of time course data.

    Store a binary blop of the data (json, pandas dataframe or similar, backwards compatible).
    """
    source = models.ForeignKey(DataFile, related_name="timecourse_sources",null=True,blank=True,on_delete=models.SET_NULL)
    figure = models.ForeignKey(DataFile, related_name="timecourse_figures",null=True,blank=True, on_delete=models.SET_NULL)
    outputset = models.ForeignKey(OutputSet, related_name="timecourses", on_delete=models.CASCADE,null=True, blank=True)
    objects = OutputManager()









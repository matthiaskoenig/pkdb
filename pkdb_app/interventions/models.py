
"""
Describe Interventions and Output (i.e. define the characteristics of the
group or individual).
"""

from django.db import models
from ..behaviours import Sidable, Describable, Valueable
from ..categoricals import PROTOCOL_CHOICES, UNITS_CHOICES
from ..subjects.models import Group
from ..studies.models import DataFile
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


class ProtocolStep(Sidable, Describable, models.Model):
    """ What is done to the group, single step.

     - dosing of certain substance, e.g. caffeine oral
     - smoking cessation
     - sports / lifestyle change
     - medication
     - ...

     Examples:
         Two groups (parallel group design), one group control, other group gets medication, e.g., oral contraceptives, than pharmacokinetics of caffeine measured.
         -> 2 protocol
            - protocol 1 (linked to control group): MedicationStep (caffeine)
            - protocol 2 (linked to intervention group): MedicationStep (oral contraceptives), MedicationStep (caffeine)

     """
    # TODO: MedicationStep & LifestyleStep

    # FIXME: Important to find the subset of dosing protocols
    category = models.IntegerField(choices=PROTOCOL_CHOICES)

    @property
    def Intervention_data(self):
        """ Returns the full information about the characteristic.

        :return:
        """
        return PROTOCOL_CHOICES[self.category]

    @property
    def choices(self):
        return self.Intervention_data.choices

    class Meta:
        abstract = True


class ValueProtocolStep(Valueable, ProtocolStep):  # choices, dose, unit (per_bodyweitght is not important)
    """ A concrete step/thing which is done to the group.

    In case of dosing/medication the actual dosing is stored in the Valueable.
    In case of a step without dosing, e.g., lifestyle intervention only the category is used.
    """
    substance = models.CharField(null=True, blank=True, max_length=CHAR_MAX_LENGTH) #substance: # what was given ['
    route = models.CharField(null=True, blank=True, max_length=CHAR_MAX_LENGTH) # route: # where ['oral', 'iv']
    application = models.CharField(null=True, blank=True, max_length=CHAR_MAX_LENGTH) # application: # how timing ['single dose', 'multiple doses', 'continuous injection']
    application_time = models.CharField(null=True, blank=True, max_length=CHAR_MAX_LENGTH) # application_time: # when exactly [h] (for multiple times create multiple MedicationSteps)
    form = models.CharField(null=True, blank=True, max_length=CHAR_MAX_LENGTH) # form: # how medication [capsule, tablete]

class ProcessedValueProtocolStep(Valueable, ProtocolStep):
    """ Calculated from medicationstep
    """
    raw = models.ForeignKey(ValueProtocolStep, null=True, on_delete=True)


class Protocol(models.Model):
    """ List of things/steps which were done to the group or changed within the group or
    distinguishing the group (for instance different time in montly cycle).
    - distinguishing operation on the group (! but does not change group characteristics !)
    - giving medication
    - FIXME: better naming of class

    """
    group = models.ForeignKey(Group, related_name='interventions', on_delete=True)
    protocol_steps = models.ManyToManyField(ValueProtocolStep)
    name = models.CharField(null=True, blank=True, max_length=CHAR_MAX_LENGTH)
    # set of protocols
    # name (control, fluvoxamine, control-fluvo, fluvo-control)

class Substance(models.Model):
    """ Substances have to be in a different table, so that
    than be uniquely defined.

    Has to be extended via ontology (Ontologable)

    """
    name = models.CharField(null=True, blank=True, max_length=CHAR_MAX_LENGTH)
    #name # example caffeine
    # ontologies: has set of defined values: is, CHEBI:27732


# -----------------
# RESULTS
# -----------------

# Create your models here.
class Output(Sidable, Describable, models.Model):
    """ Storage of data sets. """
    protocol = models.ForeignKey(Protocol,on_delete=True)
    # files from which the data was extracted, these have to be linked to the study already should be PNG or NONE
    files = models.ForeignKey(DataFile, on_delete=True)

class Pharmacokinetics(Output, Valueable):
    """ Measured value (calculated value via ProcessedPharmacokinetics)

    category: [clearance, vd, thalf, cmax, ...]
    """
    substance = models.ForeignKey(Substance, on_delete=True)
    #tissue # where was it measured


class Timecourse(Output):
    """ Storing of time course data.

    Store a binary blop of the data (json, pandas dataframe or similar, backwards compatible).
    """
    #substance
    #tissue
    data = models.ForeignKey(DataFile, on_delete=True) # link to the CSV


class ProcessedPharmacokinetics(Valueable):
    """ Calculated from pharmacokinetics or timecourse data.
    """
    raw = models.ForeignKey(Pharmacokinetics, null=True, on_delete=True)
    type = models.CharField(null=True, blank=True, max_length=CHAR_MAX_LENGTH)  # ['normalized', 'timecourse-derived']






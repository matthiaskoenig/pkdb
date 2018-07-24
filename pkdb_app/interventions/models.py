
"""
Describe Interventions and Output (i.e. define the characteristics of the
group or individual).
"""

from django.db import models
from ..behaviours import Sidable, Describable, Valueable
from ..categoricals import PROTOCOL_CHOICES, UNITS_CHOICES
from ..subjects.models import Group
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


class Protocol(models.Model):
    """ List of things/steps which were done to the group.

    """
    group = models.ForeignKey(Group, related_name='intervention', on_delete=True)
    # set of protocols
    # name (control, fluvoxamine, control-fluvo, fluvo-control)


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


class MedicationStep(Valueable, ProtocolStep):  # choices, dose, unit (per_bodyweitght is not important)
    """ Dosing.

    The actual dosing is stored in the Valueable.
    """

    substance: # what was given ['
    route: # where ['oral', 'iv']
    application: # how timing ['single dose', 'multiple doses', 'continuous injection']
    application_time: # when exactly [h] (for multiple times create multiple MedicationSteps)
    form: # how medication [capusle, tablete]
    form_details: # h details


class Substance(models.Model):
    """ Substances have to be in a different table, so that
    than be uniquely defined.

    Has to be extended via ontology (Ontologable)

    """
    name # example caffeine
    # ontologies: has set of defined values: is, CHEBI:27732


# -----------------
# RESULTS
# -----------------

# Create your models here.
class Output(Sidable, Describable, models.Model):
    """ Storage of data sets. """
    protocol = models.ForeignKey(Protocol)
    # files from which the data was extracted, these have to be linked to the study already should be PNG or NONE
    files = models.ForeignKey(DataFile)

class Pharmacokinetics(Output, Valueable):
    """ Measured value (calculated value via ProcessedPharmacokinetics)

    category: [clearance, vd, thalf, cmax, ...]
    """
    substance = models.ForeignKey(Substance)
    tissue # where was it measured


class Timecourse(Output):
    """ Storing of time course data.

    Store a binary blop of the data (json, pandas dataframe or similar, backwards compatible).
    """
    substance
    tissue
    data = models.ForeignKey(DataFile) # link to the CSV


'''
class ProcessedPharmacokinetics():
    """ Calculated from pharmacokinetics or timecourse data.

    """
    rawid = models.ForeignKey(Pharmacokinetics)
    type # ['normalized', 'timecourse-derived']
'''





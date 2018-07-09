
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


class Protocol:
    """ Selection of things which were done to the group.

    """
    group = models.ForeignKey(Group, related_name='intervention', on_delete=True)
    # set of protocols
    # name (control, fluvoxamine, control-fluvo, fluvo-control)


class ProtocolStep(Sidable, Describable, models.Model):
    """ What is done to the group, single step.

     - dosing of certain substance, e.g. caffeine oral

     - smoking cessation
     - sports, ...
     -
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



class MedicationStep(Valuable, ProtocolStep):  # choices, dose, unit (per_bodyweitght is not important)

    substance: # what was given ['
    route: # where ['oral', 'iv']
    application: # how timing ['single dose', 'multiple doses', 'continuous injection']
    application_time: # when exactly [h] (for multiple times create multiple MedicationSteps)
    form: # how medication [capusle, tablete]
    form_details: # h details


class Substance(Ontologable):
    """
    """
    name # example caffeine
    # ontologies: has set of defined values: is, CHEBI:27732


class ProtocolValue(Valueable, Protocol):
    pass

    #def validate(self):
        #    """ Check that choices are valid. I.e. that choice is allowed choice from choices for
        #    Interventions.

        #    Add checks for individuals and groups. For instance if count==1 than value must be filled,
        #    but not entries in mean, median, ...

        #    :return:
        #    """
        #    raise NotImplemented

class DatasetFile():
    """ Table or figure from where the data comes from.

    """
    file = models.FileField(upload_to="output", null=True, blank=True)  # table or figure


# Create your models here.
class Output(Sidable, Describable, models.Model):
    """ Storage of data sets. """
    protocol = models.ForeignKey(Protocol)
    file = models.ForeignKey(DatasetFile)


class Timecourse(Output):
    """ Storing of time course data.

    Store a binary blop of the data (json, pandas dataframe or similar, backwards compatible).
    """
    data = models.BinaryField()



class Pharmacokinetics(Output, Valueable):
    """ Measured value (calculated value via ProcessedPharmacokinetics)

    category: [clearance, vd, thalf, cmax, ...]
    """
    substance = models.ForeignKey(Substance)
    tissue # where was it measured


class ProcessedPharmacokinetics():
    """ Calculated from pharmacokinetics or timecourse data.

    """
    rawid = models.ForeignKey(Pharmacokinetics)
    type # ['normalized', 'timecourse-derived']




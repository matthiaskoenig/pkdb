
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


# Create your models here.
class Output(Sidable, Describable, models.Model):
    """ Storage of data sets. """
    file = models.FileField(upload_to="output", null=True, blank=True)
    groups = models.ManyToManyField(Group, through="InterventionValue")


# How to represent the dosing?
# Add separate class? extension of model?

class Protocol(Sidable, Describable, models.Model):
    """ What is done to the group. """


    # FIXME: Important to find the subset of dosing protocols

    category = models.IntegerField(choices=PROTOCOL_CHOICES)
    group = models.ForeignKey(Group, related_name='intervention', on_delete=True)
    output = models.ForeignKey(Output, related_name='intervention', on_delete=True)

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
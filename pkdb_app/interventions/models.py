
'''
Describe Interventions and Output (i.e. define the characteristics of the
group or individual).
'''

from django.db import models
from ..behaviours import Sidable, Describable, Values
from ..categoricals import INTERVENTION_CHOICES, UNITS_CHOICES
from ..subjects.models import Group
from ..utils import CHAR_MAX_LENGTH
# -------------------------------------------------
# Intervention
# -------------------------------------------------



# Create your models here.
class Output(Sidable,Describable,models.Model):
    file = models.FileField(upload_to="output", null=True, blank=True)
    groups = models.ManyToManyField(Group,through="InterventionValue")


class Intervention(Sidable,Describable, models.Model):
    category = models.IntegerField(choices=INTERVENTION_CHOICES)
    group = models.ForeignKey(Group, related_name='intervention', on_delete=True)
    output = models.ForeignKey(Output, related_name='intervention',on_delete=True)

    @property
    def Intervention_data(self):
        """ Returns the full information about the characteristic.

        :return:
        """
        return INTERVENTION_CHOICES[self.category]

    @property
    def choices(self):
        return self.Intervention_data.choices

    class Meta:
        abstract = True


class InterventionValue(Values ,Intervention):
    pass
    #def validate(self):
        #    """ Check that choices are valid. I.e. that choice is allowed choice from choices for
        #    Interventions.

        #    Add checks for individuals and groups. For instance if count==1 than value must be filled,
        #    but not entries in mean, median, ...

        #    :return:
        #    """
        #    raise NotImplemented
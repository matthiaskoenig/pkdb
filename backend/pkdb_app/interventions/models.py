"""
Describe Interventions and Output (i.e. define the characteristics of the
group or individual).
"""
from django.db import models

from ..utils import CHAR_MAX_LENGTH, create_choices
from ..subjects.models import DataFile

from ..interventions.managers import InterventionSetManager,InterventionExManager
from ..behaviours import Externable, Accessible

from pkdb_app.users.models import User
from pkdb_app.categorials.behaviours import Normalizable, ExMeasurementTypeable

# -------------------------------------------------
# Intervention
# -------------------------------------------------


#
# Choices for intervention routes, application and form.
#

# FIXME: some duplication with pkdb_data
INTERVENTION_ROUTE = [
    "iv",  # intravenous
    "intramuscular",
    "oral",
    "rectal",
    "inhalation"
]
INTERVENTION_APPLICATION = [
    "constant infusion",
    "multiple dose",
    "single dose",
    "variable infusion",
]
INTERVENTION_FORM = [
    "capsule",
    "tablet",
    "solution",
    "no info",
]

INTERVENTION_APPLICATION_CHOICES = create_choices(INTERVENTION_APPLICATION)
INTERVENTION_ROUTE_CHOICES = create_choices(INTERVENTION_ROUTE)
INTERVENTION_FORM_CHOICES = create_choices(INTERVENTION_FORM)


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


    form = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, choices=INTERVENTION_FORM_CHOICES)
    application = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, choices=INTERVENTION_APPLICATION_CHOICES)
    time = models.FloatField(null=True)
    time_unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    route = models.CharField(max_length=CHAR_MAX_LENGTH, null=True, choices=INTERVENTION_ROUTE_CHOICES)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class AbstractInterventionMap(models.Model):
    form_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    application_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    time_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    time_unit_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    route_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    class Meta:
        abstract = True


class InterventionEx(
    Externable,
    AbstractIntervention,
    AbstractInterventionMap,
    ExMeasurementTypeable

):
    """ Intervention (external curated layer)."""

    source = models.ForeignKey(
        DataFile,
        related_name="s_intervention_exs",
        null=True,
        on_delete=models.CASCADE,
    )
    figure = models.ForeignKey(
        DataFile,
        related_name="f_intervention_exs",
        null=True,
        on_delete=models.CASCADE,
    )

    interventionset = models.ForeignKey(
        InterventionSet, related_name="intervention_exs", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    name_map = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)
    objects = InterventionExManager()

    class Meta:
        unique_together = ("interventionset", "name", "name_map", "source")


class Intervention(Accessible, Normalizable, AbstractIntervention):
    """ A concrete step/thing which is done to the group.

         In case of dosing/medication the actual dosing is stored in the Valueable.
         In case of a step without dosing, e.g., lifestyle intervention only the measurement_type is used.
      """
    ex = models.ForeignKey(
        InterventionEx,
        related_name="interventions",
        null=True,
        on_delete=models.CASCADE,
    )

    name = models.CharField(max_length=CHAR_MAX_LENGTH)


    @property
    def study_name(self):
        return self.study.name

    @property
    def study(self):
        return self.ex.interventionset.study



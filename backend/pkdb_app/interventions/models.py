"""
Describe Interventions and Output (i.e. define the characteristics of the
group or individual).
"""
from django.db import models

from pkdb_app.behaviours import Normalizable
from pkdb_app.info_nodes.models import Application, Form, Route
from ..behaviours import Externable, Accessible
from ..subjects.models import DataFile
from ..utils import CHAR_MAX_LENGTH


# -------------------------------------------------
# Intervention
# -------------------------------------------------

class InterventionSet(models.Model):

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
    time = models.FloatField(null=True)
    time_end = models.FloatField(null=True)
    time_unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name





class InterventionEx(Externable):
    """ Intervention (external curated layer)."""

    source = models.ForeignKey(
        DataFile,
        related_name="s_intervention_exs",
        null=True,
        on_delete=models.CASCADE,
    )
    image = models.ForeignKey(
        DataFile,
        related_name="i_intervention_exs",
        null=True,
        on_delete=models.CASCADE,
    )

    interventionset = models.ForeignKey(
        InterventionSet, related_name="intervention_exs", on_delete=models.CASCADE
    )



class Intervention(Accessible, Normalizable, AbstractIntervention):
    """ A concrete step/thing which is done to the group.

    In case of dosing/medication the actual dosing is stored in the Valueable.
    In case of a step without dosing, e.g., lifestyle intervention only the
    measurement_type is used.
    """
    ex = models.ForeignKey(
        InterventionEx,
        related_name="interventions",
        null=True,
        on_delete=models.CASCADE,
    )

    name = models.CharField(max_length=CHAR_MAX_LENGTH)
    route = models.ForeignKey(Route, on_delete=models.CASCADE, null=True)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, null=True)
    form = models.ForeignKey(Form, on_delete=models.CASCADE, null=True)
    study = models.ForeignKey('studies.Study', on_delete=models.CASCADE, related_name="interventions")

    @property
    def raw_pk(self):
        if self.raw:
            return self.raw.pk
        return None

    @property
    def i_application(self):
        return self._i("application")

    @property
    def i_route(self):
        return self._i("route")

    @property
    def i_form(self):
        return self._i("form")

    @property
    def route_name(self):
        if self.route:
            return self.route.info_node.name
        return None

    @property
    def application_name(self):
        if self.application:
            return self.application.info_node.name
        return None

    @property
    def form_name(self):
        if self.form:
            return self.form.info_node.name
        return None



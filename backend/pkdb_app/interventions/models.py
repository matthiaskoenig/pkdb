"""Models describing the interventions applied to a group or individual."""

from typing import TYPE_CHECKING

from django.db import models

from pkdb_app.behaviours import Normalizable
from pkdb_app.info_nodes.models import Application, Form, Route

from ..behaviours import Accessible, Externable
from ..subjects.models import DataFile
from ..utils import CHAR_MAX_LENGTH, CHAR_MAX_LENGTH_LONG

if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager

# -------------------------------------------------
# Intervention
# -------------------------------------------------


class InterventionSet(models.Model):
    """Collection of interventions belonging to the intervention_exs of a study."""

    if TYPE_CHECKING:
        # reverse relation of InterventionEx.interventionset
        intervention_exs: "RelatedManager[InterventionEx]"

    @property
    def interventions(self):
        """Return all interventions created from this set's intervention_exs."""
        return Intervention.objects.filter(ex__in=self.intervention_exs.all())

    @property
    def interventions_normed(self):
        """Return the normed interventions of this set."""
        return self.interventions.filter(normed=True)

    @property
    def count(self):
        """Return the number of interventions in this set, 0 if there are none."""
        if self.interventions:
            return self.interventions.count()
        return 0


class AbstractIntervention(models.Model):
    """Abstract base holding the timing fields shared by interventions."""

    time = models.CharField(max_length=CHAR_MAX_LENGTH_LONG, null=True)
    time_end = models.FloatField(null=True)
    time_unit = models.CharField(max_length=CHAR_MAX_LENGTH, null=True)

    if TYPE_CHECKING:
        # every concrete subclass declares the name field
        name: str

    class Meta:
        abstract = True

    def __str__(self):
        """Return the intervention's name."""
        return self.name


class InterventionEx(Externable):
    """Intervention (external curated layer)."""

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
    """A concrete step/thing which is done to the group.

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
    study = models.ForeignKey(
        "studies.Study", on_delete=models.CASCADE, related_name="interventions"
    )

    def __str__(self):
        """Return the intervention's name."""
        return self.name

    @property
    def raw_pk(self):
        """Return the primary key of the raw (non-normed) intervention, or None."""
        if self.raw:
            return self.raw.pk
        return None

    @property
    def i_application(self):
        """Return the info node of the application, or None if not set."""
        return self._i("application")

    @property
    def i_route(self):
        """Return the info node of the route, or None if not set."""
        return self._i("route")

    @property
    def i_form(self):
        """Return the info node of the form, or None if not set."""
        return self._i("form")

    @property
    def route_name(self):
        """Return the name of the route's info node, or None if not set."""
        if self.route:
            return self.route.info_node.name
        return None

    @property
    def application_name(self):
        """Return the name of the application's info node, or None if not set."""
        if self.application:
            return self.application.info_node.name
        return None

    @property
    def form_name(self):
        """Return the name of the form's info node, or None if not set."""
        if self.form:
            return self.form.info_node.name
        return None

"""Comments and descriptions that curators attach to studies and their data."""

from django.db import models

# Create your models here.
from pkdb_app.data.models import Data, DataSet, Dimension, SubSet
from pkdb_app.interventions.models import (
    InterventionEx,
    InterventionSet,
)
from pkdb_app.outputs.models import OutputEx, OutputSet
from pkdb_app.studies.models import Study
from pkdb_app.subjects.models import (
    CharacteristicaEx,
    GroupEx,
    GroupSet,
    IndividualEx,
    IndividualSet,
)
from pkdb_app.users.models import User


class Comment(models.Model):
    """A curator's remark attached to a study or to one of its uploaded entities.

    Exactly one of the foreign keys is expected to be set, linking the comment
    to the study, group, individual, intervention, output, data set or one of
    their ``Ex`` (external, as uploaded) counterparts it was written about.
    """

    text = models.TextField(null=True)
    user = models.ForeignKey(
        User, related_name="comments", null=True, on_delete=models.CASCADE
    )
    date_time = models.DateTimeField(auto_now_add=True, blank=True)

    individual_ex = models.ForeignKey(
        IndividualEx, related_name="comments", null=True, on_delete=models.CASCADE
    )

    individualset = models.ForeignKey(
        IndividualSet, related_name="comments", null=True, on_delete=models.CASCADE
    )
    group_ex = models.ForeignKey(
        GroupEx, related_name="comments", null=True, on_delete=models.CASCADE
    )

    groupset = models.ForeignKey(
        GroupSet, related_name="comments", null=True, on_delete=models.CASCADE
    )

    characteristica_ex = models.ForeignKey(
        CharacteristicaEx, related_name="comments", null=True, on_delete=models.CASCADE
    )

    output_ex = models.ForeignKey(
        OutputEx, related_name="comments", null=True, on_delete=models.CASCADE
    )

    outputset = models.ForeignKey(
        OutputSet, related_name="comments", null=True, on_delete=models.CASCADE
    )

    datasets = models.ForeignKey(
        DataSet, related_name="comments", null=True, on_delete=models.CASCADE
    )

    data = models.ForeignKey(
        Data, related_name="comments", null=True, on_delete=models.CASCADE
    )

    subsets = models.ForeignKey(
        SubSet, related_name="comments", null=True, on_delete=models.CASCADE
    )

    dimensions = models.ForeignKey(
        Dimension, related_name="comments", null=True, on_delete=models.CASCADE
    )

    intervention_ex = models.ForeignKey(
        InterventionEx, related_name="comments", null=True, on_delete=models.CASCADE
    )
    interventionset = models.ForeignKey(
        InterventionSet, related_name="comments", null=True, on_delete=models.CASCADE
    )

    study = models.ForeignKey(
        Study, related_name="comments", null=True, on_delete=models.CASCADE
    )

    class Meta:
        ordering = ["pk"]

    @property
    def username(self):
        """Return the username of the comment's author."""
        return self.user.username


class Description(models.Model):
    """A free text description attached to a study or one of its uploaded entities.

    Exactly one of the foreign keys is expected to be set, linking the
    description to the study, group, individual, intervention, output, data
    set or one of their ``Ex`` (external, as uploaded) counterparts, or to a
    study as a warning.
    """

    text = models.TextField(blank=True, null=True)
    groupset = models.ForeignKey(
        GroupSet, related_name="descriptions", null=True, on_delete=models.CASCADE
    )
    interventionset = models.ForeignKey(
        InterventionSet,
        related_name="descriptions",
        null=True,
        on_delete=models.CASCADE,
    )
    outputset = models.ForeignKey(
        OutputSet, related_name="descriptions", null=True, on_delete=models.CASCADE
    )

    datasets = models.ForeignKey(
        DataSet, related_name="descriptions", null=True, on_delete=models.CASCADE
    )

    data = models.ForeignKey(
        Data, related_name="descriptions", null=True, on_delete=models.CASCADE
    )

    subsets = models.ForeignKey(
        SubSet, related_name="descriptions", null=True, on_delete=models.CASCADE
    )

    dimensions = models.ForeignKey(
        Dimension, related_name="descriptions", null=True, on_delete=models.CASCADE
    )
    individualset = models.ForeignKey(
        IndividualSet, related_name="descriptions", null=True, on_delete=models.CASCADE
    )
    study = models.ForeignKey(
        Study, related_name="descriptions", null=True, on_delete=models.CASCADE
    )
    study_as_warning = models.ForeignKey(
        Study, related_name="warnings", null=True, on_delete=models.CASCADE
    )

    individual_ex = models.ForeignKey(
        IndividualEx, related_name="descriptions", null=True, on_delete=models.CASCADE
    )

    group_ex = models.ForeignKey(
        GroupEx, related_name="descriptions", null=True, on_delete=models.CASCADE
    )

    characteristica_ex = models.ForeignKey(
        CharacteristicaEx,
        related_name="descriptions",
        null=True,
        on_delete=models.CASCADE,
    )

    output_ex = models.ForeignKey(
        OutputEx, related_name="descriptions", null=True, on_delete=models.CASCADE
    )

    intervention_ex = models.ForeignKey(
        InterventionEx, related_name="descriptions", null=True, on_delete=models.CASCADE
    )

    class Meta:
        ordering = ["pk"]

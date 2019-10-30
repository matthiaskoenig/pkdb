from django.db import models

# Create your models here.
from pkdb_app.interventions.models import (
    InterventionEx,
    InterventionSet,
)
from pkdb_app.outputs.models import OutputEx, OutputSet, TimecourseEx
from pkdb_app.studies.models import Reference, Study
from pkdb_app.subjects.models import (
    IndividualEx,
    IndividualSet,
    CharacteristicaEx,
    GroupSet,
    GroupEx,
)
from pkdb_app.users.models import User


class Comment(models.Model):

    text = models.TextField(null=True)
    user = models.ForeignKey(
        User, related_name="comments", null=True, on_delete=models.CASCADE
    )
    date_time = models.DateTimeField(auto_now_add=True, blank=True)
    ####

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
    timecourse_ex = models.ForeignKey(
        TimecourseEx, related_name="comments", null=True, on_delete=models.CASCADE
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
        ordering = ['pk']


class Description(models.Model):
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
    individualset = models.ForeignKey(
        IndividualSet, related_name="descriptions", null=True, on_delete=models.CASCADE
    )
    study = models.ForeignKey(
        Study, related_name="descriptions", null=True, on_delete=models.CASCADE
    )

    individual_ex = models.ForeignKey(
        IndividualEx, related_name="descriptions", null=True, on_delete=models.CASCADE
    )

    group_ex = models.ForeignKey(
        GroupEx, related_name="descriptions", null=True, on_delete=models.CASCADE
    )

    characteristica_ex = models.ForeignKey(
        CharacteristicaEx, related_name="descriptions", null=True, on_delete=models.CASCADE
    )

    output_ex = models.ForeignKey(
        OutputEx, related_name="descriptions", null=True, on_delete=models.CASCADE
    )

    timecourse_ex = models.ForeignKey(
        TimecourseEx, related_name="descriptions", null=True, on_delete=models.CASCADE
    )

    intervention_ex = models.ForeignKey(
        InterventionEx, related_name="descriptions", null=True, on_delete=models.CASCADE
    )

    class Meta:
        ordering = ['pk']


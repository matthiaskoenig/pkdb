from django.db import models

# Create your models here.
from pkdb_app.interventions.models import InterventionEx, InterventionSet, TimecourseEx, OutputSet, OutputEx
from pkdb_app.studies.models import Reference, Study
from pkdb_app.subjects.models import IndividualEx, IndividualSet, CharacteristicaEx, GroupSet, GroupEx
from pkdb_app.users.models import User



class Comment(models.Model):

    text = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, related_name="comments", blank=True, null=True, on_delete = models.SET_NULL)
    date_time = models.DateTimeField(auto_now_add=True, blank=True)
    ####

    individual_ex = models.ForeignKey(IndividualEx, related_name="comments", blank=True, null=True, on_delete=models.SET_NULL)
    individualset = models.ForeignKey(IndividualSet,related_name="comments",blank=True, null=True, on_delete=models.SET_NULL)
    group_ex = models.ForeignKey(GroupEx,related_name="comments", blank=True, null=True,on_delete=models.SET_NULL)
    groupset = models.ForeignKey(GroupSet,related_name="comments",blank=True, null=True, on_delete=models.SET_NULL)
    characteristica_ex = models.ForeignKey(CharacteristicaEx,related_name="comments",blank=True, null=True, on_delete=models.SET_NULL)


    output_ex = models.ForeignKey(OutputEx,related_name="comments",blank=True, null=True, on_delete=models.SET_NULL)
    outputset = models.ForeignKey(OutputSet,related_name="comments",blank=True, null=True, on_delete=models.SET_NULL)
    timecourse_ex = models.ForeignKey(TimecourseEx,related_name="comments", blank=True, null=True,on_delete=models.SET_NULL)

    intervention_ex = models.ForeignKey(InterventionEx,related_name="comments",blank=True, null=True, on_delete=models.SET_NULL)
    interventionset = models.ForeignKey(InterventionSet,related_name="comments", blank=True, null=True,on_delete=models.SET_NULL)


    reference = models.ForeignKey(Reference,related_name="comments",blank=True, null=True, on_delete=models.SET_NULL)
    study = models.ForeignKey(Study, related_name="comments",blank=True, null=True,on_delete=models.SET_NULL)


class Description(models.Model):
    text = models.TextField(blank=True, null=True)

    groupset = models.ForeignKey(GroupSet,related_name="descriptions",blank=True, null=True, on_delete=models.SET_NULL)
    interventionset = models.ForeignKey(InterventionSet,related_name="descriptions", blank=True, null=True,on_delete=models.SET_NULL)
    outputset = models.ForeignKey(OutputSet,related_name="descriptions",blank=True, null=True, on_delete=models.SET_NULL)
    individualset = models.ForeignKey(IndividualSet,related_name="descriptions",blank=True, null=True, on_delete=models.SET_NULL)

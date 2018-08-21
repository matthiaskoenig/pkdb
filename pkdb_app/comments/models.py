from django.db import models

# Create your models here.
from pkdb_app.interventions.models import Intervention, InterventionSet, Timecourse, OutputSet, Output
from pkdb_app.studies.models import Reference, Study
from pkdb_app.subjects.models import IndividualEx, IndividualSet, Characteristica, GroupSet, Group
from pkdb_app.users.models import User


class Comment(models.Model):

    text = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, related_name="comments", blank=True, null=True, on_delete = models.SET_NULL)
    time = models.DateTimeField(auto_created=True)
    ####

    individual = models.ForeignKey(IndividualEx, related_name="comments", blank=True, null=True, on_delete=models.SET_NULL)
    individualset = models.ForeignKey(IndividualSet,related_name="comments",blank=True, null=True, on_delete=models.SET_NULL)
    group = models.ForeignKey(Group,related_name="comments", blank=True, null=True,on_delete=models.SET_NULL)
    groupset = models.ForeignKey(GroupSet,related_name="comments",blank=True, null=True, on_delete=models.SET_NULL)
    characteristica = models.ForeignKey(Characteristica,related_name="comments",blank=True, null=True, on_delete=models.SET_NULL)


    output = models.ForeignKey(Output,related_name="comments",blank=True, null=True, on_delete=models.SET_NULL)
    outputset = models.ForeignKey(OutputSet,related_name="comments",blank=True, null=True, on_delete=models.SET_NULL)
    timecourse = models.ForeignKey(Timecourse,related_name="comments", blank=True, null=True,on_delete=models.SET_NULL)

    intervention = models.ForeignKey(Intervention,related_name="comments",blank=True, null=True, on_delete=models.SET_NULL)
    interventionset = models.ForeignKey(InterventionSet,related_name="comments", blank=True, null=True,on_delete=models.SET_NULL)


    reference = models.ForeignKey(Reference,related_name="comments",blank=True, null=True, on_delete=models.SET_NULL)
    study = models.ForeignKey(Study, related_name="comments",blank=True, null=True,on_delete=models.SET_NULL)


class Description(models.Model):
    text = models.TextField(blank=True, null=True)

    groupset = models.ForeignKey(GroupSet,related_name="descriptions",blank=True, null=True, on_delete=models.SET_NULL)
    interventionset = models.ForeignKey(InterventionSet,related_name="descriptions", blank=True, null=True,on_delete=models.SET_NULL)
    outputset = models.ForeignKey(OutputSet,related_name="descriptions",blank=True, null=True, on_delete=models.SET_NULL)
    individualset = models.ForeignKey(IndividualSet,related_name="descriptions",blank=True, null=True, on_delete=models.SET_NULL)

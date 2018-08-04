from django.db import models

# Create your models here.
from pkdb_app.interventions.models import Intervention, InterventionSet, Timecourse, OutputSet, Output
from pkdb_app.studies.models import Reference, Study
from pkdb_app.subjects.models import Individual, IndividualSet, Characteristica, GroupSet, Group
from pkdb_app.users.models import User


class Comment(models.Model):

    text = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, related_name="comments", on_delete=False)
    time = models.DateTimeField(auto_created=True)
    ####

    individual =  models.ForeignKey(Individual,related_name="comments",blank=True, null=True, on_delete=False)
    individualset = models.ForeignKey(IndividualSet,related_name="comments",blank=True, null=True, on_delete=False)
    group   =  models.ForeignKey(Group,related_name="comments", blank=True, null=True,on_delete=False)
    groupset =  models.ForeignKey(GroupSet,related_name="comments",blank=True, null=True, on_delete=False)
    characteristica =  models.ForeignKey(Characteristica,related_name="comments",blank=True, null=True, on_delete=False)


    output =  models.ForeignKey(Output,related_name="comments",blank=True, null=True, on_delete=False)
    outputset =  models.ForeignKey(OutputSet,related_name="comments",blank=True, null=True, on_delete=False)
    timecourse =  models.ForeignKey(Timecourse,related_name="comments", blank=True, null=True,on_delete=False)

    intervention =  models.ForeignKey(Intervention,related_name="comments",blank=True, null=True, on_delete=False)
    interventionset =  models.ForeignKey(InterventionSet,related_name="comments", blank=True, null=True,on_delete=False)


    reference =  models.ForeignKey(Reference,related_name="comments",blank=True, null=True, on_delete=False)
    study =  models.ForeignKey(Study, related_name="comments",blank=True, null=True,on_delete=False)



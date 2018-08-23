import django_filters
from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets

from pkdb_app.interventions.models import Substance
from pkdb_app.interventions.serializers import SubstanceSerializer

class SubstancesViewSet(viewsets.ModelViewSet):

    queryset = Substance.objects.all()
    serializer_class = SubstanceSerializer



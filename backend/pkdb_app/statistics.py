"""
Basic information and statistics about data base content.
"""
import pandas as pd
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework import viewsets
from rest_framework.response import Response

from pkdb_app._version import __version__
from pkdb_app.studies.models import Study, Reference
from pkdb_app.subjects.models import Group, Individual
from pkdb_app.interventions.models import Intervention, Output, Timecourse


class Statistics(object):
    """ Basic database statistics. """

    def __init__(self):
        self.version = __version__
        self.study_count = Study.objects.count()
        self.reference_count = Reference.objects.count()
        self.group_count = Group.objects.count()
        self.individual_count = Individual.objects.count()
        self.intervention_count = Intervention.objects.filter(final=True).count()
        self.output_count = Output.objects.filter(final=True).count()
        self.timecourse_count = Timecourse.objects.filter(final=True).count()

@api_view(['GET'])
def study_pks_view(request):
    if request.method == 'GET':
        return Response(list(Study.objects.values_list("pk", flat=True)))


class StatisticsViewSet(viewsets.ViewSet):
    """
    Get database statistics including version.
    """
    def list(self, request):
        instance = Statistics()
        serializer = StatisticsSerializer(instance)
        return Response(serializer.data)


class StatisticsSerializer(serializers.BaseSerializer):
    """ Serializer for database statistics. """

    def to_representation(self, instance):
        from django.db.models import Count
        return {
            key: getattr(instance, key)
            for key in [
                "version",
                "study_count",
                "reference_count",
                "group_count",
                "individual_count",
                "intervention_count",
                "output_count",
                "timecourse_count",
            ]
        }


class StatisticsData(object):
    """ More complex statistics data for plots and overviews. """

    def __init__(self, substance):
        self.version = __version__
        self.studies = Study.objects.filter(substances__name__contains=substance)
        self.study_count = self.studies.count()
        self.reference_count = self.studies.values_list("reference").count()
        self.interventions = Intervention.objects.filter(substance__name=substance).filter(final=True)
        self.intervention_count = self.interventions.count()
        self.outputs = Output.objects.filter(substance__name=substance).filter(final=True)
        self.output_count = self.outputs.count()
        self.timecourses = Timecourse.objects.filter(substance__name=substance).filter(final=True)
        self.timecourse_count = self.timecourses.count()

        outputs_with_substance = Output.objects.filter(raw___interventions__in=self.interventions)
        self.individual_count = Individual.objects.filter(output__in=outputs_with_substance).count()
        self.group_count = Group.objects.filter(output__in=outputs_with_substance).count()


class StatisticsDataViewSet(viewsets.ViewSet):
    """
    Get database statistics including version.
    """
    def list(self, request):
        # substances = ["caffeine", "codeine"]
        data = {}
        substances = Intervention.objects.values_list("substance__name", flat=True).distinct()
        substances = [x for x in substances if x is not None]

        for substance in substances:

            instance = StatisticsData(substance=substance)
            serializer = StatisticsSerializer(instance)

            data[substance] = serializer.data
        data = pd.DataFrame(data).T.to_dict("list")
        data["labels"] = substances
        return Response(data)

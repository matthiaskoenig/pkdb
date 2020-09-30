"""
Basic information and statistics about data base content.
"""
from pkdb_app.data.models import SubSet, Data
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.response import Response

from pkdb_app._version import __version__
from pkdb_app.interventions.models import Intervention
from pkdb_app.outputs.models import Output
from pkdb_app.studies.models import Study, Reference
from pkdb_app.subjects.models import Group, Individual


'''
Substance statistics: /statistics/substances/
{
    version: 0.9.2,
    substances: {
        caffeine: {
            studies: {
                count: 20, 
            },
            interventions: {
                count: 20,
            },
            outputs: {
                count: 20
            },
            timecourses: {
                count: 40
            },
            scatters: {
                count: 30
            }
        },
        ...
    }

}


'''



class Statistics(object):
    """ Basic database statistics. """

    def __init__(self):
        self.version = __version__
        self.study_count = Study.objects.count()
        self.reference_count = Reference.objects.count()
        self.group_count = Group.objects.count()
        self.individual_count = Individual.objects.count()
        self.intervention_count = Intervention.objects.filter(normed=True).count()
        self.output_count = Output.objects.filter(normed=True).count()
        self.output_calculated_count = Output.objects.filter(normed=True, calculated=True).count()
        self.timecourse_count = SubSet.objects.filter(data__data_type=Data.DataTypes.Timecourse).count()
        self.scatter_count = SubSet.objects.filter(data__data_type=Data.DataTypes.Scatter).count()


class StatisticsViewSet(viewsets.ViewSet):
    """ Endpoint to query PK-DB statistics

    Get database statistics consisting of count and version information.
    """
    def list(self, request):
        instance = Statistics()
        serializer = StatisticsSerializer(instance)
        return Response(serializer.data)


class StatisticsSerializer(serializers.BaseSerializer):
    """ Serializer for database statistics. """

    def to_representation(self, instance):
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
                "output_calculated_count",
                'timecourse_count',
                'scatter_count',
            ]
        }

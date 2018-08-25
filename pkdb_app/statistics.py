"""
Basic information and statistics about data base content.
"""
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
        self.intervention_count = Intervention.objects.count()
        self.output_count = Output.objects.count()
        self.timecourse_count = Timecourse.objects.count()


class StatisticsSerializer(serializers.BaseSerializer):
    """ Serializer for database statistics. """
    def to_representation(self, instance):

        return {key: getattr(instance, key) for key in ["version", "study_count",
                                                        "reference_count", "group_count",
                                                        "individual_count", "intervention_count", "output_count",
                                                        "timecourse_count"]}


class StatisticsViewSet(viewsets.ViewSet):
    """
    Get database statistics including version.
    """
    '''
    def list(self, request):
        queryset = User.objects.all()
        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data)
    '''

    def list(self, request):
        instance = Statistics()
        serializer = StatisticsSerializer(instance)
        return Response(serializer.data)




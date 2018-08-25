"""
Basic information and statistics about data base content.
"""
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework import viewsets
from rest_framework.response import Response

from pkdb_app._version import __version__
from pkdb_app.studies.models import Study, Reference


class Statistics(object):
    """ Basic database statistics. """
    def __init__(self):
        self.version = __version__
        self.studies_count = Study.objects.count()


class StatisticsSerializer(serializers.BaseSerializer):
    """ Serializer for database statistics. """
    def to_representation(self, instance):
        return{
            'version': instance.version,
            "studies_count": instance.studies_count
        }


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




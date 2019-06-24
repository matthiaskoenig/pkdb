from django.urls import reverse
from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, CompoundSearchFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from pkdb_app.categorials.models import  MeasurementType
from pkdb_app.outputs.models import OUTPUT_TISSUE_DATA
from rest_framework import viewsets
from rest_framework.response import Response

from pkdb_app.documents import AccessView
from .documents import OutputDocument, TimecourseDocument
from .serializers import (OutputElasticSerializer, TimecourseElasticSerializer)
from ..pagination import CustomPagination

###############################################################################################
# Option Views
###############################################################################################


class OutputOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
        options = {}
        options["measurememnt_types"] = {k.name: k._asdict() for k in MeasurementType.objects.all()}
        options["substances"] = reverse('substances_elastic-list')
        options["tissue"] = OUTPUT_TISSUE_DATA
        return options

    def list(self, request):
        return Response(self.get_options())

class TimecourseOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
            options = {}
            options["measurememnt_types"] = {k.name: k._asdict() for k in MeasurementType.objects.all()}
            options["substances"] = reverse('substances_elastic-list')
            options["tissue"] = OUTPUT_TISSUE_DATA
            return options

    def list(self, request):
        return Response(self.get_options())



###############################################################################################
# Elastic Views
###############################################################################################

class ElasticOutputViewSet(AccessView):
    document = OutputDocument
    serializer_class = OutputElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,MultiMatchSearchFilterBackend]
    search_fields = ('study','measurement_type','substance','group.name', 'individual.name', "tissue",'time_unit','interventions.name')
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {'pk':'pk',
                     'study':'study.raw',
                     'normed':'normed',
                     'calculated':'calculated',
                     'unit':'unit',
                     'substance':'substance',
                     'measurement_type':'measurement_type.raw',
                     'group_pk': {'field': 'group.pk',
                                    'lookups': [
                                        LOOKUP_QUERY_IN,
                                    ],
                                },
                     'individual_pk': {'field': 'individual.pk',
                                  'lookups': [
                                      LOOKUP_QUERY_IN,
                                  ],
                                  }}
    ordering_fields = {'measurement_type':'measurement_type.raw',
                       'tissue':'tissue.raw',
                       'substance':'substance',
                       'group': 'group.name',
                       'individual': 'individual.name',
                       'value':'value',
                       }

class ElasticTimecourseViewSet(AccessView):
    document = TimecourseDocument
    serializer_class = TimecourseElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,MultiMatchSearchFilterBackend]
    search_fields = ('study','measurement_type','substance',"tissue",'time_unit','group.name', 'individual.name','interventions.name')
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {'pk': 'pk',
                     'normed': 'normed',
                     'study': 'study.raw',
                     'substance': 'substance',
                     'measurement_type': 'measurement_type.raw',
                     'group_pk': {'field': 'group.pk',
                                  'lookups': [
                                      LOOKUP_QUERY_IN,
                                  ],
                                  },
                     'individual_pk': {'field': 'individual.pk',
                                       'lookups': [
                                           LOOKUP_QUERY_IN,
                                       ],
                                       }}
    ordering_fields = {'measurement_type':'measurement_type.raw',
                       'tissue':'tissue.raw',
                       'group':'group.name',
                       'individual': 'individual.name',
                       'substance':'substance',

                       }

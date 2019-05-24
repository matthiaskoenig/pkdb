from django.urls import reverse
from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, CompoundSearchFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from pkdb_app.categorials.models import  MeasurementType
from pkdb_app.outputs.models import OUTPUT_TISSUE_DATA
from rest_framework import viewsets
from rest_framework.response import Response

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
        options["measurememnt_types"] = {k.key: k._asdict() for k in MeasurementType.objects.all()}
        options["substances"] = reverse('substances_elastic-list')
        options["tissue"] = OUTPUT_TISSUE_DATA
        return options

    def list(self, request):
        return Response(self.get_options())

class TimecourseOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
            options = {}
            options["measurememnt_types"] = {k.key: k._asdict() for k in MeasurementType.objects.all()}
            options["substances"] = reverse('substances_elastic-list')
            options["tissue"] = OUTPUT_TISSUE_DATA
            return options

    def list(self, request):
        return Response(self.get_options())



###############################################################################################
# Elastic Views
###############################################################################################

class ElasticOutputViewSet(DocumentViewSet):
    document = OutputDocument
    serializer_class = OutputElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,CompoundSearchFilterBackend]
    search_fields = ('measurement_type','substance.name','group.name', 'individual.name', "tissue",'time_unit','interventions.name')
    filter_fields = {'pk':'pk',
                     'study':'study.raw',
                     'normed':'normed',
                     'calculated':'calculated',
                     'unit':'unit',
                     'substance':'substance.name.raw',
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
                       'substance':'substance.name',
                       'group': 'group.name',
                       'individual': 'individual.name',
                       'value':'value',
                       }

class ElasticTimecourseViewSet(DocumentViewSet):
    document = TimecourseDocument
    serializer_class = TimecourseElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,CompoundSearchFilterBackend]
    search_fields = ('measurement_type','substance.name',"tissue",'time_unit','group.name', 'individual.name','name','interventions.name')
    filter_fields = {'pk': 'pk',
                     'normed': 'normed',
                     'substance': 'substance.name.raw',
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
                       'substance':'substance.name',
                       'auc_end':'auc_end'

                       }

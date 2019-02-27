from django.urls import reverse
from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, CompoundSearchFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from rest_framework import viewsets
from rest_framework.response import Response

from ..categoricals import INTERVENTION_DICT, INTERVENTION_ROUTE, INTERVENTION_FORM, INTERVENTION_APPLICATION, \
    OUTPUT_TISSUE_DATA, PK_DATA_DICT
from ..interventions.documents import SubstanceDocument, InterventionDocument, OutputDocument, TimecourseDocument
from ..interventions.models import (
    Substance)
from ..interventions.serializers import (
    SubstanceSerializer, SubstanceStatisticsSerializer, InterventionElasticSerializer,
    OutputElasticSerializer, TimecourseElasticSerializer)
from rest_framework.permissions import IsAdminUser

from ..pagination import CustomPagination
from ..views import CreateListModelMixin


###############################################################################################
# Upload/External Views
###############################################################################################


class SubstanceViewSet(CreateListModelMixin,viewsets.ModelViewSet):
    queryset = Substance.objects.all()
    serializer_class = SubstanceSerializer
    permission_classes = (IsAdminUser,)

class SubstanceStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Substance.objects.all()
    serializer_class = SubstanceStatisticsSerializer



###############################################################################################
# Option Views
###############################################################################################


class InterventionOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
        options = {}
        options["categories"] = {k: item._asdict() for k, item in sorted(INTERVENTION_DICT.items())}
        options["substances"] = reverse('substances_elastic-list')
        options["route"] = INTERVENTION_ROUTE
        options["form"] = INTERVENTION_FORM
        options["application"] = INTERVENTION_APPLICATION
        return options

    def list(self, request):
        return Response(self.get_options())

class OutputOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
        options = {}
        options["pktypes"] = {k:item._asdict() for k, item in sorted(PK_DATA_DICT.items())}
        options["substances"] = reverse('substances_elastic-list')
        options["tissue"] = OUTPUT_TISSUE_DATA
        return options

    def list(self, request):
        return Response(self.get_options())

class TimecourseOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
            options = {}
            options["pktypes"] = {k: item._asdict() for k, item in sorted(PK_DATA_DICT.items())}
            options["substances"] = reverse('substances_elastic-list')
            options["tissue"] = OUTPUT_TISSUE_DATA
            return options

    def list(self, request):
        return Response(self.get_options())



###############################################################################################
# Elastic Views
###############################################################################################


class ElasticSubstanceViewSet(DocumentViewSet):
    document = SubstanceDocument
    serializer_class = SubstanceSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,CompoundSearchFilterBackend]
    search_fields = ('name',)
    filter_fields = {'name': 'name.raw',}
    ordering_fields = {'name': 'name.raw',}

class ElasticInterventionViewSet(DocumentViewSet):
    document = InterventionDocument
    serializer_class = InterventionElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,CompoundSearchFilterBackend]
    search_fields = ('name','category','substance.name',"form","application",'route','time_unit')
    filter_fields = {'name': 'name.raw','pk':'pk'}
    ordering_fields = {'name': 'name.raw',
                       'category':'category.raw',
                       'choice':'choice.raw',
                       'application':'application.raw',
                       'substance':'substance.name',
                       'value':'value'}



class ElasticOutputViewSet(DocumentViewSet):
    document = OutputDocument
    serializer_class = OutputElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,CompoundSearchFilterBackend]
    search_fields = ('pktype','substance.name','group.name', 'individual.name', "tissue",'time_unit','interventions.name')
    filter_fields = {'pk':'pk',
                     'study':'study.raw',
                     'final':'final',
                     'calculated':'calculated',
                     'unit':'unit',
                     'substance':'substance.name.raw',
                     'pktype':'pktype.raw',
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
    ordering_fields = {'pktype':'pktype.raw',
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
    search_fields = ('pktype','substance.name',"tissue",'time_unit','group.name', 'individual.name','name','interventions.name')
    filter_fields = {'pk': 'pk',
                     'final': 'final',
                     'substance': 'substance.name.raw',
                     'pktype': 'pktype.raw',
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
    ordering_fields = {'pktype':'pktype.raw',
                       'tissue':'tissue.raw',
                       'group':'group.name',
                       'individual': 'individual.name',
                       'substance':'substance.name',
                       'auc_end':'auc_end'

                       }

import django_filters.rest_framework
from django_elasticsearch_dsl_drf.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework import viewsets
from rest_framework.response import Response

from pkdb_app.categoricals import CHARACTERISTIC_DICT, CHARACTERISTICA_TYPES
from pkdb_app.pagination import CustomPagination
from pkdb_app.subjects.models import (
    DataFile,
)
from pkdb_app.subjects.serializers import (
    DataFileSerializer,
    DataFileElasticSerializer,
    IndividualElasticSerializer, GroupElasticSerializer, CharacteristicaReadSerializer)

from pkdb_app.subjects.documents import IndividualDocument, CharacteristicaDocument, GroupDocument

############################################################
#Elastic Search Views
###########################################################
from django_elasticsearch_dsl_drf.constants import (
    LOOKUP_FILTER_RANGE,
    LOOKUP_QUERY_IN,
    LOOKUP_QUERY_GT,
    LOOKUP_QUERY_GTE,
    LOOKUP_QUERY_LT,
    LOOKUP_QUERY_LTE,
    LOOKUP_FILTER_TERMS, LOOKUP_FILTER_PREFIX, LOOKUP_FILTER_WILDCARD, LOOKUP_QUERY_EXCLUDE)
from django_elasticsearch_dsl_drf.filter_backends import (
    FilteringFilterBackend,
    OrderingFilterBackend,
    SearchFilterBackend,
    IdsFilterBackend, )

from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet



class GroupViewSet(DocumentViewSet):
    document = GroupDocument
    serializer_class = GroupElasticSerializer
    lookup_field = 'id'
    filter_backends = [FilteringFilterBackend,OrderingFilterBackend,SearchFilterBackend]
    pagination_class = CustomPagination


    # Define search fields
    search_fields = (
        'name',
        'study.name',
        'parent.name',
        'characteristica_all_final.category',
        'characteristica_all_final.choice',
        'characteristica_all_final.ctype',

    )

    # Filter fields
    filter_fields = {
        'id': 'id',
        'name': 'name.raw',
        'parent': 'group.name.raw',
        'study': 'study.name.raw',
        'ctype':'ctype.raw'

    }

    # Define ordering fields
    ordering_fields = {
        'id':'id',
        'study': 'study.raw',
        #'group': 'group.raw',
        'name': 'name.raw',
    }


class IndividualViewSet(DocumentViewSet):
    document = IndividualDocument
    serializer_class = IndividualElasticSerializer
    lookup_field = 'id'
    filter_backends = [FilteringFilterBackend,OrderingFilterBackend,SearchFilterBackend]
    pagination_class = CustomPagination


    # Define search fields
    search_fields = (
        'name',
        'study.name',
        'group.name',
        'characteristica_all_final.category',
        'characteristica_all_final.choice',
        'characteristica_all_final.ctype',

    )

    # Filter fields
    filter_fields = {
        'id': {
            'field': 'id',
            'lookups': [
                LOOKUP_FILTER_RANGE,
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_GT,
                LOOKUP_QUERY_GTE,
                LOOKUP_QUERY_LT,
                LOOKUP_QUERY_LTE,
            ],
        },
        'name': 'name.raw',
        'group': 'group.name.raw',
        'study': 'study.name.raw',
        'ctype':'ctype.raw'

    }

    # Define ordering fields
    ordering_fields = {
        'id':'id',
        'study': 'study.raw',
        #'group': 'group.raw',
        'name': 'name.raw',
    }





class DataFileViewSet(viewsets.ModelViewSet):

    queryset = DataFile.objects.all()
    serializer_class = DataFileSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)




############################################################
#Read Views
###########################################################

class CharacteristicaOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
        options = {}
        options["categories"] = {k: item._asdict() for k, item in sorted(CHARACTERISTIC_DICT.items())}
        options["ctypes"] = CHARACTERISTICA_TYPES
        return options

    def list(self, request):
        return Response(self.get_options())


###########################################################
#Elastic Search Views
###########################################################




class CharacteristicaViewSet(DocumentViewSet):
    pagination_class = PageNumberPagination
    document = CharacteristicaDocument
    serializer_class = CharacteristicaReadSerializer
    lookup_field = 'id'
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,SearchFilterBackend]

    search_fields = (
        'choice',
        'group_name',
    )
    ordering_fields = {
        'choice': 'choice.raw',
        "count": 'count',
    }

    filter_fields = {
        'all_group_pks': {
            'field': 'all_group_pks',
            'lookups': [
                LOOKUP_FILTER_TERMS,
                LOOKUP_FILTER_PREFIX,
                LOOKUP_FILTER_WILDCARD,
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_EXCLUDE,
            ],
        },
        'id': {
            'field': 'id',
            'lookups': [
                LOOKUP_FILTER_RANGE,
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_GT,
                LOOKUP_QUERY_GTE,
                LOOKUP_QUERY_LT,
                LOOKUP_QUERY_LTE,
            ],
        },
        'value': {
            'field': 'value',
            'lookups': [
                LOOKUP_FILTER_RANGE,
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_GT,
                LOOKUP_QUERY_GTE,
                LOOKUP_QUERY_LT,
                LOOKUP_QUERY_LTE,
            ],
        },
        'mean': {
            'field': 'mean',
            'lookups': [
                LOOKUP_FILTER_RANGE,
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_GT,
                LOOKUP_QUERY_GTE,
                LOOKUP_QUERY_LT,
                LOOKUP_QUERY_LTE,
            ],
        },
        'median': {
            'field': 'median',
            'lookups': [
                LOOKUP_FILTER_RANGE,
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_GT,
                LOOKUP_QUERY_GTE,
                LOOKUP_QUERY_LT,
                LOOKUP_QUERY_LTE,
            ],
        },
        'min': {
            'field': 'id',
            'lookups': [
                LOOKUP_FILTER_RANGE,
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_GT,
                LOOKUP_QUERY_GTE,
                LOOKUP_QUERY_LT,
                LOOKUP_QUERY_LTE,
            ],
        },
        'max': {
            'field': 'id',
            'lookups': [
                LOOKUP_FILTER_RANGE,
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_GT,
                LOOKUP_QUERY_GTE,
                LOOKUP_QUERY_LT,
                LOOKUP_QUERY_LTE,
            ],
        },
        'se': {
            'field': 'id',
            'lookups': [
                LOOKUP_FILTER_RANGE,
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_GT,
                LOOKUP_QUERY_GTE,
                LOOKUP_QUERY_LT,
                LOOKUP_QUERY_LTE,
            ],
        },
        'sd': {
            'field': 'id',
            'lookups': [
                LOOKUP_FILTER_RANGE,
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_GT,
                LOOKUP_QUERY_GTE,
                LOOKUP_QUERY_LT,
                LOOKUP_QUERY_LTE,
            ],
        },
        'cv': {
            'field': 'id',
            'lookups': [
                LOOKUP_FILTER_RANGE,
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_GT,
                LOOKUP_QUERY_GTE,
                LOOKUP_QUERY_LT,
                LOOKUP_QUERY_LTE,
            ],
        },
        'final':'final',
        'group_name': 'group_name.raw',
        'group_pk': 'group_pk',
        'individual_name': 'individual_name.raw',
        'individual_pk': 'individual_pk',
    }





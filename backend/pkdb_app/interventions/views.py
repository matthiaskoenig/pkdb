from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend

from pkdb_app.documents import AccessView
from ..interventions.documents import InterventionDocument
from ..interventions.serializers import InterventionElasticSerializer, InterventionElasticSerializerAnalysis
from ..pagination import CustomPagination


###############################################################################################
# Elastic Views
###############################################################################################

class ElasticInterventionViewSet(AccessView):
    document = InterventionDocument
    serializer_class = InterventionElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = (
        'name', 'study', 'access', 'measurement_type', 'substance', "form", "tissue", "application", 'route',
        'time_unit')
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    filter_fields = {

        'pk': {'field': 'pk',
               'lookups': [
                   LOOKUP_QUERY_IN,
                   LOOKUP_QUERY_EXCLUDE,

               ],
               },
        'normed': 'normed',
        'name': 'name.raw',
        'measurement_type': 'measurement_type.raw',
        'choice': 'choice.raw',
        'route': 'route.raw',
        'form': 'form.raw',
        'application': 'application.raw',
        'time_unit': 'time_unit.raw',
        'time': 'time',
        'value': 'value',
        'mean': 'mean',
        'median': 'median',
        'min': 'min',
        'max': 'max',
        'se': 'se',
        'sd': 'sd',
        'cv': 'cv',
        'unit': 'unit.raw',
        'substance': 'substance.raw',

    }
    ordering_fields = {'name': 'name.raw',
                       'measurement_type': 'measurement_type.raw',
                       'choice': 'choice.raw',
                       'normed': 'normed',
                       'application': 'application.raw',
                       'substance': 'substance.raw',
                       'value': 'value'}


class ElasticInterventionAnalysisViewSet(AccessView):
    document = InterventionDocument
    serializer_class = InterventionElasticSerializerAnalysis
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = (
        'name', 'study_sid', 'access', 'measurement_type', 'substance', "form", "tissue", "application", 'route',
        'time_unit')
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {

        'study_sid': {'field': 'study_sid.raw',
                      'lookups': [
                          LOOKUP_QUERY_IN,
                          LOOKUP_QUERY_EXCLUDE,

                      ],
                      },
        'study_name': {'field': 'study_name.raw',
                       'lookups': [
                           LOOKUP_QUERY_IN,
                           LOOKUP_QUERY_EXCLUDE,

                       ],
                       },
        'pk': {'field': 'pk',
               'lookups': [
                   LOOKUP_QUERY_IN,
                   LOOKUP_QUERY_EXCLUDE,

               ],
               },
        'normed': 'normed',
        'raw_pk': 'raw_pk',
        'name': 'name.raw',
        'measurement_type': 'measurement_type.raw',
        'choice': 'choice.raw',
        'substance': 'substance.raw',
        'route': 'route.raw',
        'form': 'form.raw',
        'application': 'application.raw',
        'time_unit': 'time_unit.raw',
        'unit': 'unit.raw',
        'time': 'time',
        'value': 'value',
        'mean': 'mean',
        'median': 'median',
        'min': 'min',
        'max': 'max',
        'se': 'se',
        'sd': 'sd',
        'cv': 'cv',
    }
    ordering_fields = {'name': 'name.raw',
                       'measurement_type': 'measurement_type.raw',
                       'choice': 'choice.raw',
                       'normed': 'normed',
                       'application': 'application.raw',
                       'substance': 'substance.raw',
                       'value': 'value'}

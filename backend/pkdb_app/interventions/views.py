from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend

from pkdb_app.documents import AccessView
from ..interventions.documents import InterventionDocument
from ..interventions.serializers import InterventionElasticSerializer, InterventionElasticSerializerAnalysis
from ..pagination import CustomPagination


class ElasticInterventionViewSet(AccessView):
    """Endpoint to query interventions.

    Intervention encode what was performed on the subjects. E.g. which dose of a
    substance was applied.
    """
    document = InterventionDocument
    serializer_class = InterventionElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = (
        'name',
        'study.sid',
        'study.name',
        'measurement_type.label',
        'substance.label',
        "form.label",
        "tissue.label",
        "application.label",
        'route.label',
        'time_unit'
    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    filter_fields = {
        'pk': {
            'field': 'pk',
            'lookups': [
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_EXCLUDE,
            ],
        },
        'normed': 'normed',
        'name': 'name.raw',
        'choice': 'choice.raw',
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
        'substance': 'substance.name.raw',
        'form': 'form.name.raw',
        'route': 'route.name.raw',
        'application': 'application.name.raw',
        'measurement_type': 'measurement_type.name.raw',
        'substance_sid': {
            'field': 'substance.sid.raw',
            'lookups': [LOOKUP_QUERY_IN],
        },
        'form_sid': {
            'field': 'form.sid.raw',
            'lookups': [LOOKUP_QUERY_IN],
        },
        'route_sid': {
            'field': 'route.sid.raw',
            'lookups': [LOOKUP_QUERY_IN],
        },
        'application_sid': {
            'field': 'application.sid.raw',
            'lookups': [LOOKUP_QUERY_IN],
        },
        'measurement_type_sid': {
            'field': 'measurement_type.sid.raw',
            'lookups': [LOOKUP_QUERY_IN]
        },
    }
    ordering_fields = {
        'name': 'name.raw',
        'measurement_type': 'measurement_type.raw',
        'choice': 'choice.raw',
        'normed': 'normed',
        'application': 'application.raw',
        'substance': 'substance.raw',
        'value': 'value'
    }


class ElasticInterventionAnalysisViewSet(AccessView):
    """

    The intervention endpoint gives access to the intervention data. This is mostly a dosing of a substance to the body
    of the subject but can also be more vague interventions like a meal uptake or exercise.
    """
    swagger_schema = None
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

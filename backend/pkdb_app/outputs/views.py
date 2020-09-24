from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend
from drf_yasg.utils import swagger_auto_schema

from pkdb_app.documents import AccessView
from .documents import OutputDocument, OutputInterventionDocument
from .serializers import OutputElasticSerializer, OutputInterventionSerializer
from ..pagination import CustomPagination


class OutputInterventionViewSet(AccessView):
    """Elastic view for OutputIntervention."""
    swagger_schema = None
    document = OutputInterventionDocument
    serializer_class = OutputInterventionSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = (
        'study',
        'measurement_type',
        'substance',
        'group_name',
        'individual_name',
        'tissue',
        'time_unit',
        'intervention'
    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {
        'study_sid': {
            'field': 'study_sid.raw',
            'lookups': [LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE],
        },
        'study_name': {
            'field': 'study_name.raw',
            'lookups': [LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE],
        },
        'output_pk': {
            'field': 'output_pk',
            'lookups': [LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE],
        },
        'intervention_pk': {
            'field': 'intervention_pk',
            'lookups': [LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE],
        },
        'group_pk': {
            'field': 'group_pk',
            'lookups': [LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE],
        },
        'individual_pk': {
            'field': 'individual_pk',
            'lookups': [LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE],
        },
        'normed': 'normed',
        'calculated': 'calculated',
        'tissue': "tissue.raw",
        'time': 'time.raw',
        'time_unit': 'time_unit.raw',
        'measurement_type': 'measurement_type.raw',
        'substance': 'substance.raw',
        'choice': 'choice.raw',
        'unit': 'unit.raw',
    }
    ordering_fields = {
        'measurement_type': 'measurement_type.raw',
        'tissue': 'tissue.raw',
        'substance': 'substance.raw',
        'group_name': 'group_name.raw',
        'individual_name': 'individual_name.raw',
        'value': 'value',
    }


class ElasticOutputViewSet(AccessView):
    """ Endpoint to query outputs

    The outputs endpoint gives access to the output data. Outputs generally describe what has been measured.
    This includes more complex results which cannot be directly measured but are calculated from the measured data.
    In the outputs related subjects and interventions are referenced.
    """
    document = OutputDocument
    serializer_class = OutputElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = (
        'study.sid',
        'study.name',
        'measurement_type.label',
        'substance.label',
        "tissue.label",
        "choice.label",
        'time_unit',
        'group.name',
        'individual.name',
        'interventions.name',
    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {'operator': 'and'}
    filter_fields = {
        'study_name': 'study.name.raw',
        'study_sid': 'study.sid.raw',
        'group_pk': {
            'field': 'group.pk',
            'lookups': [LOOKUP_QUERY_IN],
        },
        'individual_pk': {
            'field': 'individual.pk',
            'lookups': [LOOKUP_QUERY_IN],
        },
        'interventions_pk': {
            'field': 'interventions.pk',
            'lookups': [LOOKUP_QUERY_IN],
        },
        'tissue': "tissue.name.raw",
        'time': 'time.raw',
        'choice': 'choice.name.raw',
        'normed': 'normed',
        'calculated': 'calculated',
        'unit': 'unit.raw',
        'substance': 'substance.name.raw',
        'output_type': {
            'field': 'output_type.raw',
            'lookups': [LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE],
        },
        'substance_sid': {
            'field': 'substance.sid.raw',
            'lookups': [LOOKUP_QUERY_IN],
        },
        'measurement_type': 'measurement_type.sid.raw',
        'measurement_type_sid': {
            'field': 'measurement_type.sid.raw',
            'lookups': [LOOKUP_QUERY_IN],
        },
        'method_sid': {
            'field': 'method.sid.raw',
            'lookups': [LOOKUP_QUERY_IN],
        },
        'tissue_sid': {
            'field': 'tissue.sid.raw',
            'lookups': [LOOKUP_QUERY_IN],
        },
    }
    ordering_fields = {
        'measurement_type': 'measurement_type.name.raw',
        'tissue': 'tissue.name.raw',
        'group': 'group.name',
        'individual': 'individual.name',
        'substance': 'substance.name',
    }

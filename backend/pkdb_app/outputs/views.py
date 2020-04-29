from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend

from pkdb_app.documents import AccessView
from .documents import OutputDocument, TimecourseDocument, OutputInterventionDocument, TimecourseInterventionDocument
from .serializers import (OutputElasticSerializer, TimecourseElasticSerializer, OutputInterventionSerializer,
                          TimecourseInterventionSerializer)
from ..pagination import CustomPagination


###############################################################################################
# Elastic Views
###############################################################################################



class OutputInterventionViewSet(AccessView):
    document = OutputInterventionDocument
    serializer_class = OutputInterventionSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = ('study', 'measurement_type', 'substance', 'group_name', 'individual_name', "tissue", 'time_unit',
                     'intervention')
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
        'output_pk': {'field': 'output_pk',
                      'lookups': [
                          LOOKUP_QUERY_IN,
                          LOOKUP_QUERY_EXCLUDE,
                      ],
                      },
        'intervention_pk': {'field': 'intervention_pk',
                            'lookups': [
                                LOOKUP_QUERY_IN,
                                LOOKUP_QUERY_EXCLUDE,
                            ],
                            },
        'group_pk': {'field': 'group_pk',
                     'lookups': [
                         LOOKUP_QUERY_IN,
                         LOOKUP_QUERY_EXCLUDE,
                     ],
                     },

        'individual_pk': {'field': 'individual_pk',
                          'lookups': [
                              LOOKUP_QUERY_IN,
                              LOOKUP_QUERY_EXCLUDE,
                          ]},
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

    ordering_fields = {'measurement_type': 'measurement_type.raw',
                       'tissue': 'tissue.raw',
                       'substance': 'substance.raw',
                       'group_name': 'group_name.raw',
                       'individual_name': 'individual_name.raw',
                       'value': 'value',
                       }


class TimecourseInterventionViewSet(AccessView):
    document = TimecourseInterventionDocument
    serializer_class = TimecourseInterventionSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = ('study', 'measurement_type', 'substance', 'group_name', 'individual_name', "tissue", 'time_unit',
                     'intervention')
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
        'tissue': "tissue.raw",
        'time': 'time.raw',
        'time_unit': 'time_unit.raw',
        'choice': 'choice.raw',
        'normed': 'normed',
        'unit': 'unit.raw',
        'substance': 'substance.raw',
        'measurement_type': 'measurement_type.raw',
        'group_pk': {'field': 'group_pk',
                     'lookups': [
                         LOOKUP_QUERY_IN,
                         LOOKUP_QUERY_EXCLUDE,
                     ],
                     },
        'timecourse_pk': {'field': 'timecourse_pk',
                          'lookups': [
                              LOOKUP_QUERY_IN,
                              LOOKUP_QUERY_EXCLUDE,

                          ],
                          },
        'individual_pk': {'field': 'individual_pk',
                          'lookups': [
                              LOOKUP_QUERY_IN,
                              LOOKUP_QUERY_EXCLUDE,

                          ]},
        'intervention_pk': {'field': 'intervention_pk',
                            'lookups': [
                                LOOKUP_QUERY_IN,
                                LOOKUP_QUERY_EXCLUDE,
                            ],
                            }}
    ordering_fields = {'measurement_type': 'measurement_type.raw',
                       'tissue': 'tissue.raw',
                       'substance': 'substance.raw',
                       'group_name': 'group_name.raw',
                       'individual_name': 'individual_name.raw',
                       }


# Elastic

common_search_fields = (
    'study.sid',
    'study.name',
    'measurement_type.name',
    'substance.name',
    "tissue.name",
    "choice.name",
    'time_unit',
    'group.name',
    'individual.name',
    'interventions.name')

common_filter_fields = {
        'study_name': 'study.name.raw',
        'study_sid': 'study.sid.raw',
        'group_pk': {'field': 'group.pk',
                     'lookups': [
                         LOOKUP_QUERY_IN,
                     ],
                     },
        'timecourse_pk': {'field': 'timecourse.pk',
                          'lookups': [
                              LOOKUP_QUERY_IN,
                          ],
                          },
        'individual_pk': {'field': 'individual.pk',
                          'lookups': [
                              LOOKUP_QUERY_IN,
                          ]},
        'interventions_pk': {'field': 'interventions.pk',
                             'lookups': [
                                 LOOKUP_QUERY_IN,
                             ],
                             },
        'tissue': "tissue.name.raw",
        'time': 'time.raw',
        'choice': 'choice.name.raw',
        'normed': 'normed',
        'calculated': 'calculated',
        'unit': 'unit.raw',
        'substance': 'substance.name.raw',
        'measurement_type': 'measurement_type.name.raw',
    }

common_ordering_fields = {
        'measurement_type': 'measurement_type.name.raw',
        'tissue': 'tissue.name.raw',
        'group': 'group.name',
        'individual': 'individual.name',
        'substance': 'substance.name',
    }


class ElasticOutputViewSet(AccessView):
    document = OutputDocument
    serializer_class = OutputElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = common_search_fields
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {'operator': 'and'}
    filter_fields = common_filter_fields
    ordering_fields = common_ordering_fields


class ElasticTimecourseViewSet(AccessView):
    document = TimecourseDocument
    serializer_class = TimecourseElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = common_search_fields
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = common_filter_fields
    ordering_fields = common_ordering_fields

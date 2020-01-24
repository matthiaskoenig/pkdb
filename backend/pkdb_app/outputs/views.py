from django.urls import reverse
from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend
from pkdb_app.categorials.models import MeasurementType, Tissue
from rest_framework import viewsets
from rest_framework.response import Response

from pkdb_app.documents import AccessView
from pkdb_app.outputs.models import Output, OutputIntervention, TimecourseIntervention
from .documents import OutputDocument, TimecourseDocument, OutputInterventionDocument, TimecourseInterventionDocument
from .serializers import (OutputElasticSerializer, TimecourseElasticSerializer, OutputInterventionSerializer, TimecourseInterventionSerializer)
from ..pagination import CustomPagination
import pandas as pd
import numpy as np
import math


###############################################################################################
# Option Views
###############################################################################################


class OutputOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
        options = {}
        options["measurememnt_types"] = {k.name: k._asdict() for k in MeasurementType.objects.all()}
        options["substances"] = reverse('substances_elastic-list')
        options["tissue"] = [k.name for k in Tissue.objects.all()]

        return options

    def list(self, request):
        return Response(self.get_options())


class TimecourseOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
        options = {}
        options["measurememnt_types"] = {k.name: k._asdict() for k in MeasurementType.objects.all()}
        options["substances"] = reverse('substances_elastic-list')
        options["tissue"] = [k.name for k in Tissue.objects.all()]
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
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = ('study', 'measurement_type', 'substance', 'group.name', 'individual.name', "tissue", 'time_unit',
                     'interventions.name')
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {

        'study_name': 'study_name.raw',
        'study_sid': 'study_sid.raw',

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
        'tissue': "tissue.raw",
        'time': 'time.raw',
        'choice': 'choice.raw',
        'normed': 'normed',
        'calculated': 'calculated',
        'unit': 'unit.raw',
        'substance': 'substance.raw',
        'measurement_type': 'measurement_type.raw',
    }

    ordering_fields = {'measurement_type': 'measurement_type.raw',
                       'tissue': 'tissue.raw',
                       'substance': 'substance',
                       'group': 'group.name',
                       'individual': 'individual.name',
                       'value': 'value',
                       }


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


class ElasticTimecourseViewSet(AccessView):
    document = TimecourseDocument
    serializer_class = TimecourseElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = ('study', 'measurement_type', 'substance', "tissue", 'time_unit', 'group.name', 'individual.name',
                     'interventions.name')
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
    ordering_fields = {'measurement_type': 'measurement_type.raw',
                       'tissue': 'tissue.raw',
                       'group': 'group.name',
                       'individual': 'individual.name',
                       'substance': 'substance',
                       }

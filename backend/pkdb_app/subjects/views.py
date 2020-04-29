from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE
############################################################
# Elastic Search Views
###########################################################
from django_elasticsearch_dsl_drf.filter_backends import (
    FilteringFilterBackend,
    OrderingFilterBackend,
    IdsFilterBackend,
    MultiMatchSearchFilterBackend)
from rest_framework import viewsets

from pkdb_app.documents import AccessView
from pkdb_app.pagination import CustomPagination
from pkdb_app.subjects.documents import IndividualDocument, GroupDocument, \
    GroupCharacteristicaDocument, IndividualCharacteristicaDocument
from pkdb_app.subjects.models import DataFile
from pkdb_app.subjects.serializers import (
    DataFileSerializer,
    IndividualElasticSerializer,
    GroupElasticSerializer,
    GroupCharacteristicaSerializer,
    IndividualCharacteristicaSerializer
)
from pkdb_app.users.permissions import StudyPermission


class GroupViewSet(AccessView):
    document = GroupDocument
    serializer_class = GroupElasticSerializer
    lookup_field = 'id'
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    pagination_class = CustomPagination

    # Define search fields
    search_fields = (
        'name',
        'study',
        'parent.name',
        'characteristica_all_normed.measurement_type.',
        'characteristica_all_normed.substance',
        'characteristica_all_normed.choice',
        'characteristica_all_normed.ctype',

    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }

    # Filter fields
    filter_fields = {
        'id': 'id',
        'pk': 'pk',
        'name': 'name.raw',
        'parent': 'group.name.raw',
        'study': 'study.raw',
        'ctype': 'ctype.raw'

    }

    # Define ordering fields
    ordering_fields = {
        'id': 'id',
        'study': 'study.raw',
        # 'group': 'group.raw',
        'name': 'name.raw',
    }


class IndividualViewSet(AccessView):
    document = IndividualDocument
    serializer_class = IndividualElasticSerializer
    lookup_field = 'id'
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    pagination_class = CustomPagination

    # Define search fields
    search_fields = (
        'name',
        'study.name',
        'group.name',
        'characteristica_all_normed.measurement_type.name',
        'characteristica_all_normed.choice',

    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }

    # Filter fields
    filter_fields = {
        'pk': 'pk',
        'id': 'id',
        'name': 'name.raw',
        'group_name': 'group.name.raw',
        'study': 'study.raw',

    }

    # Define ordering fields
    ordering_fields = {
        'id': 'id',
        'study': 'study.raw',
        'group': 'group.raw',
        'name': 'name.raw',
    }


class GroupCharacteristicaViewSet(AccessView):
    document = GroupCharacteristicaDocument
    serializer_class = GroupCharacteristicaSerializer
    pagination_class = CustomPagination
    lookup_field = 'id'
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]

    search_fields = (
        'choice',
    )
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
        'group_name': {'field': 'group_name',
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
        'group_parent_pk': {'field': 'group_parent_pk',
                            'lookups': [
                                LOOKUP_QUERY_IN,
                                LOOKUP_QUERY_EXCLUDE,

                            ],
                            },
        'characteristica_pk': {'field': 'characteristica_pk',
                               'lookups': [
                                   LOOKUP_QUERY_IN,
                                   LOOKUP_QUERY_EXCLUDE,

                               ],
                               },

        'group_count': 'group_count',
        'count': 'count',
        'measurement_type': 'measurement_type.raw',
        'choice': 'choice.raw',
        'substance': 'substance.raw',
        'value': 'value',
        'mean': 'mean',
        'median': 'median',
        'min': 'min',
        'max': 'max',
        'se': 'se',
        'sd': 'sd',
        'cv': 'cv',
        'unit': 'unit.raw',
    }
    ordering_fields = {
        'choice': 'choice.raw',
        "count": 'count',
    }


class IndividualCharacteristicaViewSet(AccessView):
    document = IndividualCharacteristicaDocument
    serializer_class = IndividualCharacteristicaSerializer
    pagination_class = CustomPagination
    lookup_field = 'id'
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]

    search_fields = (
        'choice',
    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }

    filter_fields = {
        'study_sid': {
            'field': 'study_sid.raw',
            'lookups': [
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_EXCLUDE,
            ],
        },
        'study_name': {
            'field': 'study_name.raw',
            'lookups': [
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_EXCLUDE,

            ],
        },
        'individual_name': {
            'field': 'individual_name',
            'lookups': [
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_EXCLUDE,
            ],
        },
        'individual_pk': {
            'field': 'individual_pk',
            'lookups': [
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_EXCLUDE,
            ],
        },
        'individual_group_pk': {
            'field': 'individual_group_pk',
            'lookups': [
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_EXCLUDE,
            ],
        },
        'characteristica_pk': {
            'field': 'characteristica_pk',
            'lookups': [
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_EXCLUDE,
            ],
        },
        'count': 'count',
        'measurement_type': 'measurement_type.raw',
        'choice': 'choice.raw',
        'substance': 'substance.raw',
        'value': 'value',
        'mean': 'mean',
        'median': 'median',
        'min': 'min',
        'max': 'max',
        'se': 'se',
        'sd': 'sd',
        'cv': 'cv',
        'unit': 'unit.raw',
    }
    ordering_fields = {
        'choice': 'choice.raw',
        "count": 'count',
    }


############################################################
# Views queried not from elastic search
###########################################################
class DataFileViewSet(viewsets.ModelViewSet):
    queryset = DataFile.objects.all()
    serializer_class = DataFileSerializer
    permission_classes = (StudyPermission,)

    def create(self, request, *args, **kwargs):
        try:
            DataFile.objects.filter(file=f"data/{request.data['file'].name}").delete()

        # same_files = DataFile.objects.filter(file = request.data["file"].name)
        except DataFile.DoesNotExist:
            pass

        return super().create(request, *args, **kwargs)

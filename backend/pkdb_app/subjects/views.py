from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE
from django_elasticsearch_dsl_drf.filter_backends import (
    FilteringFilterBackend,
    OrderingFilterBackend,
    IdsFilterBackend,
    MultiMatchSearchFilterBackend, CompoundSearchFilterBackend)
from rest_framework import viewsets

from pkdb_app.documents import AccessView
from pkdb_app.pagination import CustomPagination
from pkdb_app.subjects.documents import (
    IndividualDocument,
    GroupDocument,
    GroupCharacteristicaDocument,
    IndividualCharacteristicaDocument
)
from pkdb_app.subjects.models import DataFile
from pkdb_app.subjects.serializers import (
    DataFileSerializer,
    IndividualElasticSerializer,
    GroupElasticSerializer,
    GroupCharacteristicaSerializer,
    IndividualCharacteristicaSerializer
)
from pkdb_app.users.permissions import StudyPermission

subject_filter_fields = {
    'study': 'study.raw',
    'name': 'name.raw',
    'choice_sid': {
        'field': 'characteristica_all_normed.choice.sid.raw',
        'lookups': [
            LOOKUP_QUERY_IN,
            LOOKUP_QUERY_EXCLUDE,
        ],
    },
    'measurement_type_sid': {
        'field': 'characteristica_all_normed.measurement_type.sid.raw',
        'lookups': [
            LOOKUP_QUERY_IN,
            LOOKUP_QUERY_EXCLUDE,
        ],
    },
}


class GroupViewSet(AccessView):
    """ Endpoint to query groups

    The groups endpoint gives access to the groups data. A group is a collection of individuals for which data was
    reported collectively.
    """
    document = GroupDocument
    serializer_class = GroupElasticSerializer
    ignore = [404]
    lookup_field = 'id'
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    pagination_class = CustomPagination
    search_fields = (
        'characteristica_all_normed.measurement_type.label',
        'characteristica_all_normed.choice.label',
        'characteristica_all_normed.substance.label',
        'name',
        'study.name',
        'study.sid',
    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {
        'id': 'id',
        'pk': 'pk',
        'parent': 'group.name.raw',
        **subject_filter_fields
    }
    ordering_fields = {
        'id': 'id',
        'study': 'study.raw',
        # 'group': 'group.raw',
        'name': 'name.raw',
    }


class IndividualViewSet(AccessView):
    """ Endpoint to query individuals

    The individual endpoint gives access to the individual subjects data.
    """
    document = IndividualDocument
    serializer_class = IndividualElasticSerializer
    lookup_field = 'id'
    ignore = [404]
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    pagination_class = CustomPagination
    search_fields = (
        'characteristica_all_normed.measurement_type.label',
        'characteristica_all_normed.choice.label',
        'characteristica_all_normed.substance.label',
        'name',
        'study.name',
        'study.sid',
        'group.name',
    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {
        'pk': 'pk',
        'id': 'id',
        'name': 'name.raw',
        'group_name': 'group.name.raw',
        **subject_filter_fields

    }
    ordering_fields = {
        'id': 'id',
        'group': 'group.raw',
    }


characteristica_filter_fields = {
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
    'characteristica_pk': {
        'field': 'characteristica_pk',
        'lookups': [
            LOOKUP_QUERY_IN,
            LOOKUP_QUERY_EXCLUDE,
        ],
    },
    'count': 'count',
    'measurement_type': 'measurement_type.raw',
    'measurement_type_sid': {
        'field': 'measurement_type.sid.raw',
        'lookups': [
         LOOKUP_QUERY_IN,
         LOOKUP_QUERY_EXCLUDE,
        ],
    },
    'choice': 'choice.raw',
    'choice_sid': {
        'field': 'choice.sid.raw',
        'lookups': [
             LOOKUP_QUERY_IN,
             LOOKUP_QUERY_EXCLUDE,
        ],
    },
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


class GroupCharacteristicaViewSet(AccessView):
    """ Endpoint to query group characteristica

    The endpoint gives access to characteristica information for groups.
    """
    swagger_schema = None
    document = GroupCharacteristicaDocument
    serializer_class = GroupCharacteristicaSerializer
    pagination_class = CustomPagination
    lookup_field = 'id'
    filter_backends = [
        FilteringFilterBackend,
        IdsFilterBackend,
        OrderingFilterBackend,
        CompoundSearchFilterBackend,
        MultiMatchSearchFilterBackend
    ]
    search_fields = ()
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {
        'group_name': {
            'field': 'group_name',
            'lookups': [
               LOOKUP_QUERY_IN,
               LOOKUP_QUERY_EXCLUDE,
            ],
        },
        'group_pk': {
            'field': 'group_pk',
            'lookups': [
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_EXCLUDE,
            ],
        },
        'group_parent_pk': {
            'field': 'group_parent_pk',
            'lookups': [
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_EXCLUDE,
            ],
        },
        'group_count': 'group_count',
        **characteristica_filter_fields
    }
    ordering_fields = {
        'choice': 'choice.raw',
        "count": 'count',
    }


class IndividualCharacteristicaViewSet(AccessView):
    """ Endpoint to query individual characteristica

    The endpoint gives access to characteristica information for individuals.
    """
    swagger_schema = None
    document = IndividualCharacteristicaDocument
    serializer_class = IndividualCharacteristicaSerializer
    pagination_class = CustomPagination
    lookup_field = 'id'
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]

    search_fields = (
        'characteristica_all_normed.measurement_type.label',
        'characteristica_all_normed.choice.label',
        'characteristica_all_normed.substance.label',
        'name',
        'group.name',
        'study.name',
        'study.sid',
    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {
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
        **characteristica_filter_fields

    }
    ordering_fields = {
        'choice': 'choice.raw',
        "count": 'count',
    }


############################################################
# Views queried not from elastic search
###########################################################
class DataFileViewSet(viewsets.ModelViewSet):
    swagger_schema = None
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

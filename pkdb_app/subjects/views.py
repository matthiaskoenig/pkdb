import django_filters.rest_framework
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework import viewsets
from pkdb_app.subjects.models import (
    DataFile,
    Characteristica,
    Individual,
    Group,
    GroupSet,
    IndividualSet,
    GroupEx, CharacteristicaEx, IndividualEx)
from pkdb_app.subjects.serializers import (
    DataFileSerializer,
    DataFileReadSerializer,
    CharacteristicaReadSerializer,
    IndividualReadSerializer,
    GroupReadSerializer,
    GroupSetReadSerializer,
    IndividualSetReadSerializer,
    GroupExReadSerializer, CharacteristicaExReadSerializer, IndividualExReadSerializer, IndividualDocumentSerializer)

from pkdb_app.subjects.documents import IndividualDocument

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
)
from django_elasticsearch_dsl_drf.filter_backends import (
    FilteringFilterBackend,
    OrderingFilterBackend,
    DefaultOrderingFilterBackend,
    SearchFilterBackend,
    IdsFilterBackend, SuggesterFilterBackend)
from django_elasticsearch_dsl_drf.constants import SUGGESTER_COMPLETION

from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet


class DataFileViewSet(viewsets.ModelViewSet):

    queryset = DataFile.objects.all()
    serializer_class = DataFileSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
############################################################
#Read Views
###########################################################

class DataFileReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = DataFile.objects.all()
    serializer_class = DataFileReadSerializer
    permission_classes = (AllowAny,)


class CharacteristicaReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Characteristica.objects.all()
    serializer_class = CharacteristicaReadSerializer
    permission_classes = (AllowAny,)
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
    )
    filter_fields = ("final",)

class CharacteristicaExReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = CharacteristicaEx.objects.all()
    serializer_class = CharacteristicaExReadSerializer
    permission_classes = (AllowAny,)

class IndividualReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Individual.objects.all()
    serializer_class = IndividualReadSerializer
    permission_classes = (AllowAny,)

class IndividualExReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = IndividualEx.objects.all()
    serializer_class = IndividualExReadSerializer
    permission_classes = (AllowAny,)

class GroupReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Group.objects.all()
    serializer_class = GroupReadSerializer
    permission_classes = (AllowAny,)

class GroupExReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = GroupEx.objects.all()
    serializer_class = GroupExReadSerializer
    permission_classes = (AllowAny,)

class GroupSetReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = GroupSet.objects.all()
    serializer_class = GroupSetReadSerializer
    permission_classes = (AllowAny,)


class IndividualSetReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = IndividualSet.objects.all()
    serializer_class = IndividualSetReadSerializer
    permission_classes = (AllowAny,)

###########################################################
#Elastic Search Views
###########################################################


class IndividualViewSet(DocumentViewSet):
    document = IndividualDocument
    serializer_class = IndividualDocumentSerializer
    lookup_field = 'id'
    filter_backends = [
        FilteringFilterBackend,
        IdsFilterBackend,
        OrderingFilterBackend,
        DefaultOrderingFilterBackend,
        SearchFilterBackend,
        SuggesterFilterBackend,

    ]

    # Define search fields
    search_fields = (
        'name',
        'study',
        'group',


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

        #'group': 'group.raw',
        #'study': 'study.raw',

    }

    # Define ordering fields
    ordering_fields = {
        'id':'id',
        #'study': 'study.raw',
        #'group': 'group.raw',
        'name': 'name.raw',
    }

    # Specify default ordering
    ordering = ('id',)
    suggester_fields = {
        'study_suggest':
            {'field':'study.suggest',
             'suggesters': [
                SUGGESTER_COMPLETION,
            ],},
        'name_suggest': 'name.suggest',
        'group_suggest': 'group.suggest',
    }
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from pkdb_app.categorials.documents import KeywordDocument
from pkdb_app.categorials.models import InterventionType, CharacteristicType, PharmacokineticType, Keyword
from pkdb_app.categorials.serializers import InterventionTypeSerializer, CharacteristicTypeSerializer, \
    PharmacokineticTypeSerializer, KeywordSerializer, KeywordElasticSerializer
from pkdb_app.pagination import CustomPagination
from pkdb_app.users.permissions import IsAdminOrCreator
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser


class InterventionTypeViewSet(viewsets.ModelViewSet):
    queryset = InterventionType.objects.all()
    serializer_class = InterventionTypeSerializer
    permission_classes = (IsAdminOrCreator,)
    lookup_field = "url_slug"


class CharacteristicTypeViewSet(viewsets.ModelViewSet):
    queryset = CharacteristicType.objects.all()
    serializer_class = CharacteristicTypeSerializer
    permission_classes = (IsAdminOrCreator,)
    lookup_field = "url_slug"


class PharmacokineticTypeViewSet(viewsets.ModelViewSet):
    queryset = PharmacokineticType.objects.all()
    serializer_class = PharmacokineticTypeSerializer
    permission_classes = (IsAdminOrCreator,)
    lookup_field = "url_slug"


class KeywordViewSet(viewsets.ModelViewSet):
    queryset = Keyword.objects.all()
    serializer_class = KeywordSerializer
    permission_classes = (IsAdminOrCreator,)


# Elastic Views
class ElasticKeywordViewSet(DocumentViewSet):
    document = KeywordDocument
    pagination_class = CustomPagination
    serializer_class = KeywordElasticSerializer
    lookup_field = 'id'
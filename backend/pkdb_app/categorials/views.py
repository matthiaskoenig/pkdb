from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from pkdb_app.categorials.documents import KeywordDocument
from pkdb_app.categorials.models import Keyword,MeasurementType
from pkdb_app.categorials.serializers import KeywordSerializer, KeywordElasticSerializer, MeasurementTypeSerializer
from pkdb_app.pagination import CustomPagination
from pkdb_app.users.permissions import IsAdminOrCreator
from rest_framework import viewsets


class MeasurementTypeViewSet(viewsets.ModelViewSet):
    queryset = MeasurementType.objects.all()
    serializer_class = MeasurementTypeSerializer
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
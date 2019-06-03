from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, IdsFilterBackend, \
    OrderingFilterBackend, CompoundSearchFilterBackend
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from pkdb_app.categorials.documents import MeasurementTypeDocument
from pkdb_app.categorials.models import MeasurementType
from pkdb_app.categorials.serializers import MeasurementTypeSerializer, MeasurementTypeElasticSerializer
from pkdb_app.pagination import CustomPagination
from pkdb_app.users.permissions import IsAdminOrCreator
from rest_framework import viewsets


class MeasurementTypeViewSet(viewsets.ModelViewSet):
    queryset = MeasurementType.objects.all()
    serializer_class = MeasurementTypeSerializer
    permission_classes = (IsAdminOrCreator,)
    lookup_field = "url_slug"

class MeasurementTypeElasticViewSet(DocumentViewSet):
    pagination_class = CustomPagination
    document = MeasurementTypeDocument
    serializer_class = MeasurementTypeElasticSerializer
    lookup_field = 'url_slug'
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,CompoundSearchFilterBackend]
    search_fields = ("name", "url_slug", "dtype", "description", "units", "annotations.name", "choices.name", "choices.annotations.name")
    filter_fields = {'name': 'name.raw'}
    ordering_fields ={'name': 'name.raw',"dtype":"dtype.raw"}

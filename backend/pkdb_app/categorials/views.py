from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, IdsFilterBackend, \
    OrderingFilterBackend, CompoundSearchFilterBackend, MultiMatchSearchFilterBackend
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from pkdb_app.categorials.documents import MeasurementTypeDocument
from pkdb_app.categorials.models import MeasurementType, Tissue, Application, Route, Form
from pkdb_app.categorials.serializers import MeasurementTypeSerializer, MeasurementTypeElasticSerializer, \
    TissueSerializer, ApplicationSerializer, RouteSerializer, FormSerializer
from pkdb_app.pagination import CustomPagination
from pkdb_app.users.permissions import IsAdminOrCreator
from rest_framework import viewsets


class MeasurementTypeViewSet(viewsets.ModelViewSet):
    queryset = MeasurementType.objects.all()
    serializer_class = MeasurementTypeSerializer
    permission_classes = (IsAdminOrCreator,)
    lookup_field = "url_slug"


class TissueViewSet(viewsets.ModelViewSet):
    queryset = Tissue.objects.all()
    serializer_class = TissueSerializer
    permission_classes = (IsAdminOrCreator,)
    lookup_field = "url_slug"


class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = (IsAdminOrCreator,)
    lookup_field = "url_slug"


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    permission_classes = (IsAdminOrCreator,)
    lookup_field = "url_slug"


class FormViewSet(viewsets.ModelViewSet):
    queryset = Form.objects.all()
    serializer_class = FormSerializer
    permission_classes = (IsAdminOrCreator,)
    lookup_field = "url_slug"


class MeasurementTypeElasticViewSet(DocumentViewSet):
    pagination_class = CustomPagination
    document = MeasurementTypeDocument
    serializer_class = MeasurementTypeElasticSerializer
    lookup_field = 'url_slug'
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = ("name",
                     "url_slug",
                     "dtype",
                     "description",
                     "units",
                     "annotations.name",
                     "annotations.description",
                     "annotations.label",
                     "choices.name",
                     "choices.description",
                     "choices.annotations.name",
                     "choices.annotations.description",
                     "choices.annotations.label"
                     )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {'name': 'name'}
    ordering_fields = {'name': 'name', "dtype": "dtype"}

from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, IdsFilterBackend, \
    OrderingFilterBackend, CompoundSearchFilterBackend, MultiMatchSearchFilterBackend
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from pkdb_app.info_nodes.documents import MeasurementTypeDocument
from pkdb_app.info_nodes.models import MeasurementType, Substance, Route, Form, Application, Tissue, Choice
from pkdb_app.info_nodes.serializers import InfoNodeSerializer
from pkdb_app.pagination import CustomPagination
from pkdb_app.users.permissions import IsAdminOrCreator
from rest_framework import viewsets


class Chocie(object):
    pass

namedTuple =  ViewSet


class InfoNodeViewSet(viewsets.ModelViewSet):
    queryset = MeasurementType.objects.all()
    serializer_class = InfoNodeSerializer
    permission_classes = (IsAdminOrCreator,)
    lookup_field = "url_slug"
    node_types = {
        "measurement_type":MeasurementType,
        "substance": Substance,
        "measurement_type": Route,
        "measurement_type": Form,
        "measurement_type": Application,
        "measurement_type": Tissue,
        "measurement_type": Choice,

     }


class NoteTypes(models.TextChoices):
    """ Note Types. """

    Substance = 'substance', _('substance')
    MeasurementType = 'measurement_type', _('measurement_type')
    Route = 'route', _('route')
    Form = 'form', _('form')
    Application = 'application', _('application')
    Tissue = 'tissue', _('tissue')
    Chocie = 'choice', _('choice')



class InfoNodeElasticViewSet(DocumentViewSet):
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

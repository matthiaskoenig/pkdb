from collections import namedtuple

from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, IdsFilterBackend, \
    OrderingFilterBackend, MultiMatchSearchFilterBackend
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from rest_framework import viewsets

from pkdb_app.info_nodes.documents import InfoNodeDocument
from pkdb_app.info_nodes.models import  InfoNode
from pkdb_app.info_nodes.serializers import InfoNodeElasticSerializer, InfoNodeSerializer
from pkdb_app.pagination import CustomPagination
from pkdb_app.users.permissions import IsAdminOrCreator

NT = namedtuple("NodeType", ["model", "serializer", "fields"])

INFO_NODE_FIELDS = ["sid", "url_slug", "name", "parents", "description", "synonyms",
                    "creator", "annotations"]
SUBSTANCE_EXTRA = ["chebi", "formula", "charge", "mass"]
MEASUREMENT_TYPE_EXTRA = ["units"]


class InfoNodeViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminOrCreator,)
    lookup_field = "url_slug"
    serializer_class = InfoNodeSerializer
    queryset = InfoNode.objects.all()


class InfoNodeElasticViewSet(DocumentViewSet):
    pagination_class = CustomPagination
    document = InfoNodeDocument
    serializer_class = InfoNodeElasticSerializer
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

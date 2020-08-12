from collections import namedtuple

from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, IdsFilterBackend, \
    OrderingFilterBackend, MultiMatchSearchFilterBackend, SearchFilterBackend
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from rest_framework import viewsets

from pkdb_app.info_nodes.documents import InfoNodeDocument
from pkdb_app.info_nodes.models import InfoNode
from pkdb_app.info_nodes.serializers import InfoNodeElasticSerializer, InfoNodeSerializer
from pkdb_app.pagination import CustomPagination
from rest_framework.permissions import IsAdminUser

NT = namedtuple("NodeType", ["model", "serializer", "fields"])

INFO_NODE_FIELDS = ["sid", "url_slug", "name", "parents", "description", "synonyms",
                    "creator", "annotations"]
SUBSTANCE_EXTRA = ["chebi", "formula", "charge", "mass"]
MEASUREMENT_TYPE_EXTRA = ["units"]




class InfoNodeViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAdminUser,)
    lookup_field = "url_slug"
    serializer_class = InfoNodeSerializer
    queryset = InfoNode.objects.all()

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True
            return super().get_serializer(*args, **kwargs)

        return super().get_serializer(*args, **kwargs)


class InfoNodeElasticViewSet(DocumentViewSet):
    pagination_class = CustomPagination
    document = InfoNodeDocument
    serializer_class = InfoNodeElasticSerializer
    document_uid_field = "sid__raw"
    lookup_field = 'sid'
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, SearchFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = (
        "sid",
        "name",
        "description",
        "url_slug",
        "dtype",
        "ntype",
        "units",

        "annotations.name",
        "annotations.description",
        "annotations.label",

        "xrefs.name",
        "xrefs.accession",
        "xrefs.url",

        "measurement_type.choices.name",
        "measurement_type.choices.description",
        "measurement_type.choices.annotations.name",
        "measurement_type.choices.annotations.description",
        "measurement_type.choices.annotations.label",

        "synonyms.name",
        "substance.mass",
        "substance.formula",
        "substance.charge",
        )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {'name': 'name.raw', "ntype": "ntype.raw"}
    ordering_fields = {'name': 'name', "dtype": "dtype"}

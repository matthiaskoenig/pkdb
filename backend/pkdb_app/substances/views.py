from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, CompoundSearchFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from pkdb_app.users.permissions import IsAdminOrCreator
from rest_framework import viewsets
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from .documents import SubstanceDocument
from .models import Substance
from .serializers import SubstanceSerializer, SubstanceStatisticsSerializer,  SubstanceElasticSerializer
from rest_framework.permissions import IsAdminUser

from ..pagination import CustomPagination

###############################################################################################
# Upload/External Views
###############################################################################################

class SubstanceViewSet(viewsets.ModelViewSet):
    queryset = Substance.objects.all()
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    serializer_class = SubstanceSerializer
    permission_classes = (IsAdminOrCreator,)
    lookup_field = "url_slug"

class SubstanceStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Substance.objects.all()
    serializer_class = SubstanceStatisticsSerializer

###############################################################################################
# Elastic Views
###############################################################################################

class ElasticSubstanceViewSet(DocumentViewSet):
    document = SubstanceDocument
    serializer_class = SubstanceElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "url_slug"
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,CompoundSearchFilterBackend]
    search_fields = ('name',
                     'description',
                     'formula',
                     'parents.sid',
                     "annotations.name",
                     "annotations.description",
                     "annotations.label",)
    filter_fields = {'name': 'name.raw',}
    ordering_fields = {'name': 'name.raw','formula':'formula.raw','derived':"derived.raw"}

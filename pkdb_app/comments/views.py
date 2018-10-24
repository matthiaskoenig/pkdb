
# Create your views here.
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, CompoundSearchFilterBackend, IdsFilterBackend
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from pkdb_app.comments.documents import CommentDocument, DescriptionDocument
from pkdb_app.comments.serializers import DescriptionElasticSerializer, CommentElasticSerializer


class ElasticCommentViewSet(DocumentViewSet):
    document = CommentDocument
    serializer_class = CommentElasticSerializer
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,CompoundSearchFilterBackend]
    search_fields = ('text','user.username','user.first_name','user.last_name')
    filter_fields = {'text': 'text','user_lastname':'user.last_name.raw',}


class ElasticDescriptionViewSet(DocumentViewSet):
    document = DescriptionDocument
    serializer_class = DescriptionElasticSerializer
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,CompoundSearchFilterBackend]
    search_fields = ('text',)
    filter_fields = {'text': 'text.raw',}



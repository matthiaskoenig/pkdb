
# Create your views here.
from django_elasticsearch_dsl_drf.constants import SUGGESTER_TERM, SUGGESTER_PHRASE, SUGGESTER_COMPLETION
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, SearchFilterBackend, \
    SuggesterFilterBackend
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny

from pkdb_app.comments.documents import CommentDocument, DescriptionDocument
from pkdb_app.comments.models import Description, Comment
from pkdb_app.comments.serializers import DescriptionReadSerializer, CommentReadSerializer


class DescriptionReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Description.objects.all()
    serializer_class = DescriptionReadSerializer
    filter_backends = (filters.SearchFilter,)
    filter_fields = ("text",)
    search_fields = filter_fields
    permission_classes = (AllowAny,)

class CommentReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Comment.objects.all()
    serializer_class = CommentReadSerializer
    filter_backends = (filters.SearchFilter,)
    filter_fields = ("text",)
    search_fields = filter_fields
    permission_classes = (AllowAny,)

class ElasticCommentViewSet(DocumentViewSet):
    document = CommentDocument
    serializer_class = CommentReadSerializer
    lookup_field = "pk"
    filter_backends = [FilteringFilterBackend,SearchFilterBackend,SuggesterFilterBackend]
    search_fields = ('text',)
    filter_fields = {'text': 'name.raw',}
    suggester_fields = {
        'text_suggest': {'field':'text.suggest',
                         'suggesters': [SUGGESTER_TERM,SUGGESTER_PHRASE,SUGGESTER_COMPLETION],
                         'default_suggester': SUGGESTER_COMPLETION,
                         }
    }

class ElasticDescriptionViewSet(DocumentViewSet):
    document = DescriptionDocument
    serializer_class = DescriptionReadSerializer
    lookup_field = "pk"
    filter_backends = [FilteringFilterBackend,SearchFilterBackend,SuggesterFilterBackend]
    search_fields = ('text',)
    filter_fields = {'text': 'text.raw',}
    suggester_fields = {
        'text_suggest': {'field':'text.suggest',
                         'suggesters': [SUGGESTER_TERM,SUGGESTER_PHRASE,SUGGESTER_COMPLETION],
                         'default_suggester': SUGGESTER_COMPLETION,
                         }
    }


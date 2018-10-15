from django_elasticsearch_dsl_drf.constants import SUGGESTER_TERM, SUGGESTER_PHRASE, SUGGESTER_COMPLETION
from django_elasticsearch_dsl_drf.filter_backends import SearchFilterBackend, FilteringFilterBackend, \
    SuggesterFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend, HighlightBackend
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny,IsAuthenticatedOrReadOnly

from pkdb_app.pagination import CustomPagination
from pkdb_app.studies.documents import ReferenceDocument, StudyDocument
from .models import Author, Reference, Study, Keyword
from .serializers import (
    AuthorSerializer,
    ReferenceSerializer,
    StudySerializer,
    StudyReadSerializer,
    ReferenceReadSerializer,
    AuthorReadSerializer,
    KeywordSerializer,
    KeywordReadSerializer,
    StudyElasticSerializer)
from rest_framework import viewsets
import django_filters.rest_framework
from rest_framework import filters
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser


class KeywordViewSet(viewsets.ModelViewSet):
    queryset = Keyword.objects.all()
    serializer_class = KeywordSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


class AuthorsViewSet(viewsets.ModelViewSet):

    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
    )
    filter_fields = ("first_name", "last_name")
    search_fields = filter_fields
    permission_classes = (IsAuthenticatedOrReadOnly,)


class ReferencesViewSet(viewsets.ModelViewSet):

    queryset = Reference.objects.all()
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    serializer_class = ReferenceSerializer
    lookup_field = "sid"
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
    )
    filter_fields = ("sid",)

    # filter_fields = ( 'pmid', 'doi','title', 'abstract', 'journal','date', 'authors')
    search_fields = filter_fields
    permission_classes = (IsAuthenticatedOrReadOnly,)


class StudyViewSet(viewsets.ModelViewSet):
    queryset = Study.objects.all()
    serializer_class = StudySerializer
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
    )
    filter_fields = ("sid",)
    search_fields = filter_fields
    permission_classes = (IsAuthenticatedOrReadOnly,)

    @staticmethod
    def group_validation(request):
        if "groupset" in request.data:
            if request.data["groupset"]:
                groupset = request.data["groupset"]
                if "groups" in groupset:
                    groups = groupset.get("groups", [])
                    parents = set(
                        [group.get("parent") for group in groups if group.get("parent")]
                    )
                    groups = set(
                        [group.get("name") for group in groups if group.get("name")]
                    )

                    # validate if groups are missing
                    missing_groups = parents - groups
                    if missing_groups:
                        if missing_groups is not None:
                            msg = {
                                "groups": f"<{missing_groups}> have been used but not defined"
                            }
                            raise ValidationError(msg)

    def partial_update(self, request, *args, **kwargs):
        self.group_validation(request)
        return super().partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self.group_validation(request)
        return super().update(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        self.group_validation(request)
        return super().create(request, *args, **kwargs)


###############################################################################################
# Read ViewSets
###############################################################################################
class StudyReadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Study.objects.all()
    serializer_class = StudyReadSerializer
    lookup_field = "sid"
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
    )
    filter_fields = ("sid",)
    search_fields = filter_fields
    permission_classes = (AllowAny,)


class ReferencesReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Reference.objects.all()
    serializer_class = ReferenceReadSerializer
    lookup_field = "sid"
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filter_fields = ("pmid", "doi", "title", "abstract", "journal", "date", "authors")
    paginate_by_param = 'page_size'
    search_fields = filter_fields
    ordering_fields = filter_fields
    permission_classes = (AllowAny,)


class AuthorsReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Author.objects.all()
    serializer_class = AuthorReadSerializer
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
    )
    filter_fields = ("first_name", "last_name")
    search_fields = filter_fields
    permission_classes = (AllowAny,)


class KeywordReadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Keyword.objects.all()
    serializer_class = KeywordReadSerializer
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
    )
    filter_fields = ("name",)
    search_fields = filter_fields
    permission_classes = (AllowAny,)



class ElasticReferenceViewSet(DocumentViewSet):
    document = ReferenceDocument
    pagination_class = CustomPagination
    serializer_class = ReferenceReadSerializer
    lookup_field = "pk"
    filter_backends = [FilteringFilterBackend,OrderingFilterBackend, SearchFilterBackend]
    search_fields = ('sid','study_name','study_pk','pmid','title','abstract','name','journal')
    filter_fields = {'name': 'name.raw',}
    ordering_fields = {
        'sid': 'sid',
        "pk":'pk',
        "study_name":"study_name",
        "study_pk":"study_pk",
        "pmid":"pmid",
        "name":"name.raw",
        "doi":"doi",
        "title":"title.raw",
        "abstract":"abstract.raw",
        "journal":"journal.raw",
        "date":"date",
        "pdf":"pdf",
        "authors":"authors.last_name",
    }

class ElasticStudyViewSet(DocumentViewSet):
    document = StudyDocument
    pagination_class = CustomPagination
    serializer_class = StudyElasticSerializer
    lookup_field = "pk"
    filter_backends = [FilteringFilterBackend,OrderingFilterBackend,SearchFilterBackend]
    search_fields = ('sid',
                     'pk_version',

                     'creator.first_name',
                     'creator.last_name',
                     'creator.user',

                     'curators.first_name',
                     'curators.last_name',
                     'curators.user',

                     'name',
                     'design',
                     'reference',
                     'substances',
                     'keywords',
                     'files'
                     )

    filter_fields = {'name': 'name.raw',}
    ordering_fields = {
        'sid': 'sid',
        "pk_version":'pk_version',
        #"name":"name.raw",
        #"design": "design.raw",
        #"refernce": "refernce",
        #"substance": "substance.raw",
        #"keywords": "keywords.raw",

        #"files":"files",

        #"creator":"creator.last_name",
        #"curators": "curators.last_name",

    }





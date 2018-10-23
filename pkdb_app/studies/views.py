from django.http import Http404
from django_elasticsearch_dsl_drf.filter_backends import SearchFilterBackend, FilteringFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend
from django_elasticsearch_dsl_drf.utils import DictionaryProxy
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from pkdb_app.pagination import CustomPagination
from pkdb_app.studies.documents import ReferenceDocument, StudyDocument
from .models import Reference, Study
from .serializers import (
    ReferenceSerializer,
    StudySerializer,
    ReferenceElasticSerializer,
    StudyElasticSerializer)
from rest_framework import viewsets
import django_filters.rest_framework
from rest_framework import filters
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

###################
# References
###################
class ReferencesViewSet(viewsets.ModelViewSet):
    """Post/Update references"""
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


class ElasticReferenceViewSet(DocumentViewSet):
    """Read/query/search references. """
    document = ReferenceDocument
    pagination_class = CustomPagination
    serializer_class = ReferenceElasticSerializer
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend, SearchFilterBackend]
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
# Elastic ViewSets
###############################################################################################

class ElasticStudyViewSet(DocumentViewSet):
    document = StudyDocument
    pagination_class = CustomPagination
    serializer_class = StudyElasticSerializer
    lookup_field = 'id'
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,SearchFilterBackend]
    search_fields = (
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

    filter_fields = {'name': 'name.raw'}
    ordering_fields = {
        'sid': 'sid',
        "pk": 'pk',
        "pk_version":'pk_version',
        "name":"name.raw",
        "design": "design.raw",
        "refernce": "refernce",
        "substance": "substance.raw",
        #"keywords": "keywords.raw",
        #"files":"files",
        "creator":"creator.last_name",
        #"curators": "curators.last_name",

    }

    def get_object(self):
        """Get object."""
        queryset = self.get_queryset()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        if lookup_url_kwarg not in self.kwargs:
            raise AttributeError(
                "Expected view %s to be called with a URL keyword argument "
                "named '%s'. Fix your URL conf, or set the `.lookup_field` "
                "attribute on the view correctly." % (
                    self.__class__.__name__,
                    lookup_url_kwarg
                )
            )

        if lookup_url_kwarg == 'id':
            obj = self.document.get(id=self.kwargs[lookup_url_kwarg])
            return DictionaryProxy(obj.to_dict())
        else:
            queryset = queryset.filter(
                'term',
                **{self.document_uid_field: self.kwargs[lookup_url_kwarg]}
            )

            count = queryset.count()
            if count == 1:
                obj = queryset.execute().hits.hits[0]['_source']
                return DictionaryProxy(obj)

            elif count > 1:
                raise Http404(
                    "Multiple results matches the given query. "
                    "Expected a single result."
                )

            raise Http404("No result matches the given query.")






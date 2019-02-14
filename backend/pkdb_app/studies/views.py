from django.http import Http404
from django_elasticsearch_dsl_drf.filter_backends import CompoundSearchFilterBackend, \
    FilteringFilterBackend, OrderingFilterBackend, IdsFilterBackend
from django_elasticsearch_dsl_drf.utils import DictionaryProxy
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAdminUser
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from elasticsearch import helpers
from pkdb_app.interventions.documents import InterventionDocument, TimecourseDocument, OutputDocument
from pkdb_app.pagination import CustomPagination
from pkdb_app.studies.documents import ReferenceDocument, StudyDocument, KeywordDocument
from pkdb_app.subjects.documents import GroupDocument, IndividualDocument


from .models import Reference, Study, Keyword
from .serializers import (
    ReferenceSerializer,
    StudySerializer,
    ReferenceElasticSerializer,
    StudyElasticSerializer, KeywordSerializer)
from rest_framework import viewsets
import django_filters.rest_framework
from rest_framework import filters
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from django.core.exceptions import ObjectDoesNotExist


class KeywordViewSet(viewsets.ModelViewSet):
    queryset = Keyword.objects.all()
    serializer_class = KeywordSerializer
    permission_classes = (IsAdminUser,)


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
    permission_classes = (IsAdminUser,)


class StudyViewSet(viewsets.ModelViewSet):
    queryset = Study.objects.all()
    serializer_class = StudySerializer
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
    )
    filter_fields = ("sid",)
    search_fields = filter_fields
    permission_classes = (IsAdminUser,)

    @staticmethod
    def group_validation(request):
        if "groupset" in request.data:
            if request.data["groupset"]:
                groupset = request.data["groupset"]
                if "groups" in groupset:

                    groups = groupset.get("groups", [])
                    parents_name = set()
                    groups_name = set()
                    for group in groups:
                        parent_name  = group.get("parent")
                        if parent_name:
                            parents_name.add(parent_name)
                        group_name = group.get("name")
                        if group_name:
                            groups_name.add(group_name)
                        if group_name == "all" and parent_name is not None:
                            raise ValidationError({"groups": "parent is not allowed for group all"})

                        elif group_name != "all" and parent_name is None:
                            raise ValidationError({"groups":"parent is required for keyword in groups besides for the the <all> group"})





                    if "all" not in groups_name:
                        raise ValidationError({"group":"a group with the name all is required. This is the group "
                                              "with common characteristica for all groups and individuals"})


                    # validate if groups are missing
                    missing_groups = parents_name - groups_name
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
class ElasticKeywordViewSet(DocumentViewSet):
    document = KeywordDocument
    pagination_class = CustomPagination
    serializer_class = KeywordSerializer
    lookup_field = 'id'


@csrf_exempt
def update_index(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        update_instances = {}
        try:
            study = Study.objects.get(sid=data["sid"])
        except ObjectDoesNotExist:
            return JsonResponse({"success": "False", "reason": "Instance not in database"})

        action = data.get("action",'index')
        update_instances[StudyDocument] = study
        update_instances[ReferenceDocument] = study.reference
        update_instances[GroupDocument] = study.groups
        update_instances[IndividualDocument] = study.individuals
        update_instances[InterventionDocument] = study.interventions
        update_instances[OutputDocument] = study.outputs
        update_instances[TimecourseDocument] = study.timecourses


        for doc, instances in update_instances.items():
            try:
                doc().update(thing=instances,action=action)
            except helpers.BulkIndexError:
                pass

        return JsonResponse({"success":"True"})


class ElasticStudyViewSet(DocumentViewSet):
    document = StudyDocument
    pagination_class = CustomPagination
    serializer_class = StudyElasticSerializer
    lookup_field = 'id'
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,CompoundSearchFilterBackend]
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
        "name":"name",
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

class ElasticReferenceViewSet(DocumentViewSet):
    """Read/query/search references. """
    document = ReferenceDocument
    pagination_class = CustomPagination
    serializer_class = ReferenceElasticSerializer
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,CompoundSearchFilterBackend]
    search_fields = ('sid','study_name','study_pk','pmid','title','abstract','name','journal')
    #multi_match_search_fields = {f:f for f in search_fields}
    #multi_match_options = {
    #    'type': 'filter'
    #}
    filter_fields = {'name': 'name.raw',}
    #filter_fields = {f:f for f in search_fields}
    ordering_fields = {
        'sid': 'sid',
        "pk":'pk',
        "study_name":"study_name",
        "study_pk":"study_pk",
        "pmid":"pmid",
        "name":"name",
        "doi":"doi",
        "title":"title.raw",
        "abstract":"abstract.raw",
        "journal":"journal.raw",
        "date":"date",
        "pdf":"pdf",
        "authors":"authors.last_name",
    }

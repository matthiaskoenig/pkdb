from django.http import Http404
from django_elasticsearch_dsl_drf.filter_backends import CompoundSearchFilterBackend, \
    FilteringFilterBackend, OrderingFilterBackend, IdsFilterBackend
from django_elasticsearch_dsl_drf.utils import DictionaryProxy
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from pkdb_app.outputs.documents import OutputDocument, TimecourseDocument
from pkdb_app.users.models import PUBLIC
from pkdb_app.users.permissions import IsAdminOrCreatorOrCurator, StudyPermission, user_group
from rest_framework.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from elasticsearch import helpers
from pkdb_app.interventions.documents import InterventionDocument
from pkdb_app.pagination import CustomPagination
from pkdb_app.studies.documents import ReferenceDocument, StudyDocument
from pkdb_app.subjects.documents import GroupDocument, IndividualDocument, CharacteristicaDocument

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

from django.core.exceptions import ObjectDoesNotExist

from elasticsearch_dsl.query import Q


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
    permission_classes = (IsAdminOrCreatorOrCurator,)


class StudyViewSet(viewsets.ModelViewSet):
    queryset = Study.objects.all()
    serializer_class = StudySerializer
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
    )
    filter_fields = ("sid",)
    search_fields = filter_fields
    lookup_field = "sid"
    permission_classes = (StudyPermission,)

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
                        raise ValidationError(
                            {"group": "A group with the name `all` is missing (studies without such a group cannot be uploaded). "
                                      "The `all` group is the group of all subjects which was studied and defines common "
                                      "characteristica for all groups and individuals. Create the `all` group or rename group to `all`."})


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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        related_elastic = related_elastic_dict(instance)
        delete_elastic_study(related_elastic)

        return super().destroy(request)


###############################################################################################
# Elastic ViewSets
###############################################################################################

def delete_elastic_study(related_elastic):
    for doc, instances in related_elastic.items():
        try:
            doc().update(thing=instances, action="delete")
        except helpers.BulkIndexError:
            pass


def related_elastic_dict(study):
    related_elastic_dict = {}
    related_elastic_dict[StudyDocument] = study
    if study.reference:
        related_elastic_dict[ReferenceDocument] = study.reference

    related_elastic_dict[GroupDocument] = study.groups
    related_elastic_dict[IndividualDocument] = study.individuals
    related_elastic_dict[CharacteristicaDocument] = study.characteristica
    related_elastic_dict[InterventionDocument] = study.interventions
    related_elastic_dict[OutputDocument] = study.outputs
    related_elastic_dict[TimecourseDocument] = study.timecourses
    return related_elastic_dict




@csrf_exempt
def update_index_study(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        try:
            study = Study.objects.get(sid=data["sid"])
        except ObjectDoesNotExist:
            return JsonResponse({"success": "False", "reason": "Instance not in database"})

        action = data.get("action",'index')

        related_elastic = related_elastic_dict(study)

        for doc, instances in related_elastic.items():

            try:
                doc().update(thing=instances,action=action)
            except helpers.BulkIndexError:
                pass

        return JsonResponse({"success":"True"})


class ElasticStudyViewSet(DocumentViewSet):
    document_uid_field = "sid__raw"
    lookup_field = "sid"
    document = StudyDocument
    pagination_class = CustomPagination
    serializer_class = StudyElasticSerializer
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,CompoundSearchFilterBackend]
    permission_classes = (StudyPermission,)
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
                     'files'
                     )

    filter_fields = {'sid':'sid.raw','name': 'name.raw', "substances": "substances"}
    ordering_fields = {
        'sid': 'sid',
        "pk": 'pk',
        "pk_version":'pk_version',
        "name":"name",
        "design": "design.raw",
        "reference": "reference.raw",
        "creator":"creator.last_name",

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
                'match',
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

    def get_queryset(self):
        search = self.search
        group = user_group(self.request.user)

        if group in ["admin","reviewer"]:
            return search.query()

        elif group == "basic":

            qs = search.query(
                Q('match', access__raw=PUBLIC) |
                Q('match', creator__username__raw=self.request.user.username) |
                Q('match', curators__username__raw=self.request.user.username) |
                Q('match', collaborators__username__raw=self.request.user.username)

            )

            return qs

        elif group == "anonymous":

            qs = search.query(
                'match',
                **{"access__raw": PUBLIC}
            )

            return qs




class ElasticReferenceViewSet(DocumentViewSet):
    """Read/query/search references. """
    document_uid_field = "sid__raw"
    lookup_field = "sid"
    document = ReferenceDocument
    pagination_class = CustomPagination
    permission_classes = (IsAdminOrCreatorOrCurator,)
    serializer_class = ReferenceElasticSerializer
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,CompoundSearchFilterBackend]
    search_fields = ('sid','study_name','study_pk','pmid','title','abstract','name','journal')

    filter_fields = {'name': 'name.raw',}
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
                'match',
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

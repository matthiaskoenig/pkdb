import django_filters.rest_framework
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q as DQ
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend
from django_elasticsearch_dsl_drf.viewsets import BaseDocumentViewSet
from elasticsearch import helpers
from elasticsearch_dsl.query import Q
from rest_framework import filters
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from pkdb_app.interventions.documents import InterventionDocument
from pkdb_app.outputs.documents import OutputDocument, TimecourseDocument, TimecourseInterventionDocument, \
    OutputInterventionDocument
from pkdb_app.outputs.models import TimecourseIntervention, OutputIntervention
from pkdb_app.pagination import CustomPagination
from pkdb_app.studies.documents import ReferenceDocument, StudyDocument
from pkdb_app.subjects.documents import GroupDocument, IndividualDocument, \
    GroupCharacteristicaDocument, IndividualCharacteristicaDocument
from pkdb_app.subjects.models import GroupCharacteristica, IndividualCharacteristica
from pkdb_app.users.models import PUBLIC
from pkdb_app.users.permissions import IsAdminOrCreatorOrCurator, StudyPermission, user_group
from .models import Reference, Study
from .serializers import (
    ReferenceSerializer,
    StudySerializer,
    ReferenceElasticSerializer,
    StudyElasticSerializer
)


class ReferencesViewSet(viewsets.ModelViewSet):
    """ ReferenceViewSet """
    queryset = Reference.objects.all()
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    serializer_class = ReferenceSerializer
    lookup_field = "sid"
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        filters.SearchFilter,
    )
    filter_fields = ("sid",)
    search_fields = filter_fields
    permission_classes = (IsAdminOrCreatorOrCurator,)


class StudyViewSet(viewsets.ModelViewSet):
    """ StudyViewSet """
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


    def get_queryset(self):
        queryset = super().get_queryset()
        group = user_group(self.request.user)
        if group in ["admin", "reviewer"]:
            return queryset

        elif group == "basic":

            return queryset.filter(DQ(access=PUBLIC) |
                                   DQ(creator=self.request.user) |
                                   DQ(collaborators=self.request.user) |
                                   DQ(curators=self.request.user)).distinct()

        elif group == "anonymous":
            return queryset.filter(access=PUBLIC)

    def destroy(self, request, *args, **kwargs):

        # if get object does not find  an object it stops here

        instance = self.get_object()

        related_elastic = related_elastic_dict(instance)
        delete_elastic_study(related_elastic)
        return super().destroy(request, *args, **kwargs)



###############################################################################################
# Elastic ViewSets
###############################################################################################
import timeit


@csrf_exempt
def update_index_study(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        try:
            study = Study.objects.get(sid=data["sid"])

        except ObjectDoesNotExist:
            return JsonResponse({"success": "False", "reason": "Instance not in database"})

        related_elastic = related_elastic_dict(study)
        for doc, instances in related_elastic.items():
            start_time = timeit.default_timer()
            # code you want to evaluate

            try:
                action = data.get('action', 'index')
                doc().update(thing=instances, action=action)
            except helpers.BulkIndexError:
                raise helpers.BulkIndexError

            elapsed = timeit.default_timer() - start_time
            print(doc)
            print(elapsed)

        return JsonResponse({"success": "True"})


def delete_elastic_study(related_elastic):
    for doc, instances in related_elastic.items():
        try:
            doc().update(thing=instances, action="delete")
        except helpers.BulkIndexError:
            return False, "BulkIndexError"


def related_elastic_dict(study):
    """ Dictionary of elastic documents for given study.

    :param study:
    :return:
    """
    interventions = study.interventions.all()
    groups = study.groups.all()
    individuals = study.individuals.all()
    outputs = study.outputs.all()
    timecourses = study.timecourses.all()
    docs_dict = {
        StudyDocument: study,
        GroupDocument: groups,
        IndividualDocument: individuals,
        GroupCharacteristicaDocument: GroupCharacteristica.objects.select_related('group', 'characteristica').filter(group__in=groups),
        IndividualCharacteristicaDocument: IndividualCharacteristica.objects.select_related( 'individual', 'characteristica').filter(individual__in=individuals),
        TimecourseInterventionDocument: TimecourseIntervention.objects.select_related(
        'intervention', 'timecourse').filter(timecourse__in=timecourses),
        OutputInterventionDocument: OutputIntervention.objects.select_related(
        'intervention', 'output').filter(output__in=outputs),
        InterventionDocument: interventions,
        OutputDocument: study.outputs.all(),
        TimecourseDocument: study.timecourses.all(),

    }
    if study.reference:
        docs_dict[ReferenceDocument] = study.reference
    return docs_dict


class ElasticStudyViewSet(BaseDocumentViewSet):
    document_uid_field = "sid__raw"
    lookup_field = "sid"
    document = StudyDocument
    pagination_class = CustomPagination
    serializer_class = StudyElasticSerializer
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    permission_classes = (StudyPermission,)
    search_fields = (
        'sid',
        'pk_version',
        'creator.first_name',
        'creator.last_name',
        'creator.user',


        'curators.first_name',
        'curators.last_name',
        'curators.user',

        'name',
        'reference',
        'substances',
        'files',
    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }

    filter_fields = {
        'sid': 'sid.raw',
        'name': 'name.raw',
        'creator': 'creator.username.raw',
        'curator': 'curators.username.raw',
        'collaborator': 'collaborators.name.raw',
        'licence': 'licence.raw',
        'access': 'access.raw',
        'substance': 'substances.name.raw',
    }
    ordering_fields = {
        'sid': 'sid',
    }

    def get_queryset(self):
        search = self.search
        group = user_group(self.request.user)

        if group in ["admin", "reviewer"]:
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


class ElasticReferenceViewSet(BaseDocumentViewSet):
    """Read/query/search references. """
    document_uid_field = "sid__raw"
    lookup_field = "sid"
    document = ReferenceDocument
    pagination_class = CustomPagination
    permission_classes = (IsAdminOrCreatorOrCurator,)
    serializer_class = ReferenceElasticSerializer
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = ('sid', 'pmid', 'title', 'abstract', 'name', 'journal')
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {'name': 'name.raw', }
    ordering_fields = {
        'sid': 'sid',
        "pk": 'pk',
        "pmid": "pmid",
        "name": "name",
        "doi": "doi",
        "title": "title.raw",
        "abstract": "abstract.raw",
        "journal": "journal.raw",
        "date": "date",
        "pdf": "pdf",
        "authors": "authors.last_name",
    }

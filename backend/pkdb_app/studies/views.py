import operator
from copy import copy
from functools import reduce

import django_filters.rest_framework
from attr import dataclass
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q as DQ
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend
from django_elasticsearch_dsl_drf.viewsets import BaseDocumentViewSet
from elasticsearch import helpers
from elasticsearch_dsl.query import Q
from rest_framework import serializers
from pkdb_app.data.documents import DataAnalysisDocument
from pkdb_app.serializers import PkSerializer, PkStringSerializer
from rest_framework.response import Response
from rest_framework import filters, status
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from pkdb_app.interventions.documents import InterventionDocument
from pkdb_app.outputs.documents import OutputDocument, \
    OutputInterventionDocument
from pkdb_app.outputs.models import OutputIntervention
from pkdb_app.pagination import CustomPagination
from pkdb_app.studies.documents import ReferenceDocument, StudyDocument
from pkdb_app.subjects.documents import GroupDocument, IndividualDocument, \
    GroupCharacteristicaDocument, IndividualCharacteristicaDocument
from pkdb_app.subjects.models import GroupCharacteristica, IndividualCharacteristica, Individual, Group
from pkdb_app.users.models import PUBLIC
from pkdb_app.users.permissions import IsAdminOrCreatorOrCurator, StudyPermission, user_group
from rest_framework.views import APIView

from .models import Reference, Study
from .serializers import (
    ReferenceSerializer,
    StudySerializer,
    ReferenceElasticSerializer,
    StudyElasticSerializer,
)

from django.db.models import Subquery
from django.db.models import Q
from pkdb_app.interventions.views import ElasticInterventionViewSet
from pkdb_app.outputs.models import Output
from pkdb_app.interventions.models import Intervention
from pkdb_app.outputs.views import ElasticOutputViewSet
from pkdb_app.studies.models import Study
from pkdb_app.subjects.models import Group, Individual
from pkdb_app.subjects.views import GroupViewSet, IndividualViewSet

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
            # code you want to evaluate

            try:
                action = data.get('action', 'index')
                doc().update(thing=instances, action=action)
            except helpers.BulkIndexError:
                raise helpers.BulkIndexError



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
    dimensions = study.dimensions.all()


    related_outputs_intervention = [
        'intervention',
        'output',
        'output__individual',
        'output__group',
        'output__measurement_type__info_node',
        'output__tissue__info_node',
        'output__substance__info_node',
    ]


    related_outputs = [
        'individual',
        'group',
        'measurement_type__info_node',
        'tissue__info_node',
        'substance__info_node',
    ]

    docs_dict = {
        StudyDocument: study,
        GroupDocument: groups,
        IndividualDocument: individuals,
        GroupCharacteristicaDocument: GroupCharacteristica.objects.select_related('group', 'characteristica').filter(group__in=groups),
        IndividualCharacteristicaDocument: IndividualCharacteristica.objects.select_related('individual', 'characteristica').filter(individual__in=individuals),
        InterventionDocument: interventions,
        OutputDocument:  study.outputs.select_related(*related_outputs).prefetch_related('interventions'),
        OutputInterventionDocument: OutputIntervention.objects.select_related(*related_outputs_intervention).filter(intervention__in=interventions),
        DataAnalysisDocument: dimensions,
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
        'files',

        'substances.name'

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
        if hasattr(self, "initial_data"):

            id_queries = [Q('term', access__raw=pk) for pk in self.initial_data]

            if len(id_queries) == 1:
                search = search.query('match', sid__raw=self.initial_data[0])
            elif len(id_queries) > 1:
                search = search.query(reduce(operator.ior, id_queries))

        if group in ["admin", "reviewer"]:
            qs = search.query()

        elif group == "basic":

            qs = search.query(
                Q('match', access__raw=PUBLIC) |
                Q('match', creator__username__raw=self.request.user.username) |
                Q('match', curators__username__raw=self.request.user.username) |
                Q('match', collaborators__username__raw=self.request.user.username)
            )

        elif group == "anonymous":

            qs = search.query(
                'match',
                **{"access__raw": PUBLIC}
            )

        else:
            raise AssertionError("Group for user has to be provided.")

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




class PKData(object):
    def __init__(self,
                 interventions_query: dict = None,
                 groups_query: dict = None,
                 individuals_query: dict = None,
                 outputs_query: dict = None,
                 # data_query: dict = None,
                 studies_query: dict = None
                 ):
        self.groups_query = groups_query
        self.individuals_query = individuals_query
        self.interventions_query = interventions_query
        self.outputs_query = outputs_query
        # self.data_query = data_query
        self.studies_query = studies_query

        self.studies = Study.objects.filter(**self.studies_query)
        self.groups = Group.objects.filter(**self.groups_query)
        self.individuals = Individual.objects.filter(**self.individuals_query)
        self.interventions = Intervention.objects.filter(**self.interventions_query)
        self.outputs = Output.objects.filter(**self.outputs_query)

    def _update_outputs(self):
        outputs = self.outputs.filter(
            Q(group__in=Subquery(self.groups.values('pk'))) | Q(individual__in=Subquery(self.individuals.values('pk'))))
        outputs = outputs.filter(study__in=Subquery(self.studies.values('pk')))

        if len(outputs) < len(self.outputs):
            self.keep_concising = True
            self.outputs = outputs

    def concise(self):
        self.keep_concising = True
        while self.keep_concising:
            self.keep_concising = False
            self._update_outputs()
            if self.keep_concising:
                self.interventions = self.interventions.filter(outputs__in=self.outputs)
                self.individuals = self.individuals.filter(pk__in=Subquery(self.outputs.values("individual__pk")))
                self.groups = self.groups.filter(pk__in=Subquery(self.outputs.values("group__pk")))
                self.studies = self.studies.filter(pk__in=Subquery(self.outputs.values("study")))

    @property
    def intervention_view(self):
        view = ElasticInterventionViewSet
        view.initial_data = self.interventions.distinct().values_list('pk', flat=True)
        return view

    @property
    def group_view(self):
        view = GroupViewSet
        view.initial_data = self.groups.distinct().values_list('pk', flat=True)
        return view

    @property
    def individual_view(self):
        view = IndividualViewSet
        view.initial_data = self.interventions.distinct().values_list('pk', flat=True)
        return view

    @property
    def output_view(self):
        view = ElasticOutputViewSet
        view.initial_data = self.interventions.distinct().values_list('pk', flat=True)
        return view

    @property
    def study_view(self):
        view = ElasticStudyViewSet
        view.initial_data = self.studies.distinct().values_list('sid', flat=True)
        return view


class PKDataView(APIView):
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    study_filter = [f"study__{field}" for field in ElasticStudyViewSet.filter_fields]
    intervention_filter = [f"intervention__{field}" for field in ElasticInterventionViewSet.filter_fields]
    study_search = [f"study__{field}" for field in ElasticStudyViewSet.search_fields]
    intervention_search = [f"intervention__{field}" for field in ElasticInterventionViewSet.search_fields]

    #filter_fields = study_filter + intervention_filter
    #search_fields = study_search + intervention_search

    EXTRA = {
        "study": "studies__",
        "intervention": "interventions__",
        "group": "groups__",
        "individual": "individuals__",
        "output": "outputs__",
    }

    def _get_param(self, key, request):
        param = {}
        for key_request, value in request.GET.items():
            if key_request.startswith(self.EXTRA[key]):
                string_len = len(self.EXTRA[key])
                param[key_request[string_len:]] = value
        return param


    def get(self, request, *args, **kw):

        pkdata = PKData(
            studies_query=self._get_param("study",request),
            groups_query=self._get_param("group",request),
            individuals_query=self._get_param("individual",request),
            interventions_query=self._get_param("intervention",request),
            outputs_query=self._get_param("output", request),

        )
        pkdata.concise()
        request.GET = {}

        data = {
            "studies": pkdata.study_view.as_view({'get': 'list'})(request=request._request).data,
            "interventions": pkdata.intervention_view.as_view({'get': 'list'})(request=request._request).data,
            "groups": pkdata.group_view.as_view({'get': 'list'})(request=request._request).data,
            "individual": pkdata.individual_view.as_view({'get': 'list'})(request=request._request).data,
            "output": pkdata.output_view.as_view({'get': 'list'})(request=request._request).data,
        }
        response = Response(data, status=status.HTTP_200_OK)
        return response


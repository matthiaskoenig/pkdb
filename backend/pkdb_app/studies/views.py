from typing import Dict
import time
from django.test.client import RequestFactory

import django_filters.rest_framework
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q as DQ
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend
from django_elasticsearch_dsl_drf.viewsets import BaseDocumentViewSet, DocumentViewSet
from elasticsearch import helpers
from elasticsearch_dsl.query import Q
from pkdb_app.interventions.serializers import InterventionElasticSerializerAnalysis, InterventionElasticSerializer
from pkdb_app.outputs.serializers import OutputElasticSerializer
from pkdb_app.subjects.serializers import GroupCharacteristicaSerializer, IndividualCharacteristicaSerializer, \
    GroupElasticSerializer, IndividualElasticSerializer
from rest_framework import serializers
from pkdb_app.data.documents import DataAnalysisDocument
from pkdb_app.serializers import PkSerializer, StudySmallElasticSerializer, NameSerializer
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
from pkdb_app.subjects.models import GroupCharacteristica, IndividualCharacteristica
from pkdb_app.users.models import PUBLIC
from pkdb_app.users.permissions import IsAdminOrCreatorOrCurator, StudyPermission, user_group
from rest_framework.views import APIView

from .models import Reference
from .serializers import (
    ReferenceSerializer,
    StudySerializer,
    ReferenceElasticSerializer,
    StudyElasticSerializer, StudyAnalysisSerializer,
)

from django.db.models import Subquery
from django.db.models import Q
from pkdb_app.interventions.views import ElasticInterventionViewSet
from pkdb_app.outputs.models import Output
from pkdb_app.interventions.models import Intervention
from pkdb_app.outputs.views import ElasticOutputViewSet
from pkdb_app.studies.models import Study
from pkdb_app.subjects.models import Group, Individual
from pkdb_app.subjects.views import GroupViewSet, IndividualViewSet, IndividualCharacteristicaViewSet


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
        GroupCharacteristicaDocument: GroupCharacteristica.objects.select_related('group', 'characteristica').filter(
            group__in=groups),
        IndividualCharacteristicaDocument: IndividualCharacteristica.objects.select_related('individual',
                                                                                            'characteristica').filter(
            individual__in=individuals),
        InterventionDocument: interventions,
        OutputDocument: study.outputs.select_related(*related_outputs).prefetch_related('interventions'),
        OutputInterventionDocument: OutputIntervention.objects.select_related(*related_outputs_intervention).filter(
            intervention__in=interventions),
        DataAnalysisDocument: dimensions,
    }
    if study.reference:
        docs_dict[ReferenceDocument] = study.reference
    return docs_dict


class ElasticStudyViewSet(BaseDocumentViewSet):
    # document_uid_field = "sid__raw"
    # lookup_field = "sid"
    document = StudyDocument
    serializer_class = StudyElasticSerializer
    pagination_class = CustomPagination
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, MultiMatchSearchFilterBackend]
    # permission_classes = (StudyPermission,)
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
        group = user_group(self.request.user)
        if group in ["admin", "reviewer"]:
            return self.search.query()

        elif group == "basic":

            qs = self.search.query(
                Q('match', access__raw=PUBLIC) |
                Q('match', creator__username__raw=self.request.user.username) |
                Q('match', curators__username__raw=self.request.user.username) |
                Q('match', collaborators__username__raw=self.request.user.username)

            )

            return qs

        elif group == "anonymous":

            qs = self.search.query(
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


class PKData(object):
    """
   PKData represents a consistent set of pharmacokinetical data.

    """
    def __init__(self,
                 request,
                 interventions_query: dict = None,
                 groups_query: dict = None,
                 individuals_query: dict = None,
                 outputs_query: dict = None,
                 # data_query: dict = None,
                 studies_query: dict = None,
                 ):


        self.request = request
        self.groups_query = groups_query
        self.individuals_query = individuals_query
        self.interventions_query = {"normed":"true", **interventions_query}
        self.outputs_query = {"normed":"true",**outputs_query}
        # self.data_query = data_query
        self.studies_query = studies_query

        start_time = time.time()
        studies_pks = self.study_pks()
        groups_pks = self.group_pks()
        individuals_pks = self.individual_pks()
        interventions_pks = self.intervention_pks()
        outputs_pks = self.output_pks()

        elastic_time = time.time() - start_time
        print("Elastic Time")
        print(elastic_time)
        self.studies = Study.objects.filter(sid__in=studies_pks)
        self.groups = Group.objects.filter(pk__in=groups_pks)
        self.individuals = Individual.objects.filter(pk__in=individuals_pks)
        self.interventions = Intervention.objects.filter(pk__in=interventions_pks)
        self.outputs = Output.objects.filter(pk__in=outputs_pks)
        django_time = time.time() - start_time - elastic_time
        print("Django Time")
        print(django_time)

    def empty_get(self):
        """create an get request with no parameters in the url."""
        return RequestFactory().get("/").GET.copy()

    def _update_outputs(self):
        """ """
        outputs = self.outputs.filter(DQ(group__in=self.groups) | DQ(individual__in=self.individuals))
        outputs = outputs.filter(study__in=self.studies, interventions__in=self.interventions)

        if len(outputs) < len(self.outputs):
            self.keep_concising = True
            self.outputs = outputs

    def concise(self):
        self.keep_concising = True
        while self.keep_concising:
            self.keep_concising = False
            self._update_outputs()
            if self.keep_concising:
                self.interventions = self.interventions.filter(outputs__in=self.outputs).distinct()
                self.individuals = self.individuals.filter(
                    pk__in=Subquery(self.outputs.values("individual__pk"))).distinct()
                self.groups = self.groups.filter(pk__in=Subquery(self.outputs.values("group__pk"))).distinct()
                self.studies = self.studies.filter(sid__in=Subquery(self.outputs.values("study__sid"))).distinct()

    def intervention_pks(self):
        return self._pks(view_class=ElasticInterventionViewSet, query_dict=self.interventions_query)

    def group_pks(self):
        return self._pks(view_class=GroupViewSet, query_dict=self.groups_query)

    def individual_pks(self):
        return self._pks(view_class=IndividualViewSet, query_dict=self.individuals_query)

    def output_pks(self):
        return self._pks(view_class=ElasticOutputViewSet, query_dict=self.outputs_query )

    def study_pks(self):
        return self._pks(view_class=ElasticStudyViewSet, query_dict=self.studies_query, pk_field="sid")


    def set_request_get(self, query_dict:Dict):
        """

        :param query_dict:
        :return:
        """
        get = self.empty_get()
        for k, v in query_dict.items():
            get[k] = v
        self.request._request.GET = get

    def _pks(self, view_class: DocumentViewSet, query_dict: Dict, pk_field: str="pk"):
        """
        query elastic search for pks.

        """
        self.set_request_get(query_dict)
        view = view_class(request=self.request)
        queryset = view.filter_queryset(view.get_queryset())
        count = queryset.count()
        response = queryset.extra(size=count).execute()
        return [instance[pk_field] for instance in response]

    def _paginated_data(self, serializer, queryset, query_dict):
        paginator = CustomPagination()
        self.set_request_get(query_dict)
        page = paginator.paginate_queryset(queryset, self.request)
        if page is not None:
            return {
                "current_page": paginator.page.number,
                "last_page": paginator.page.paginator.num_pages,
                "data": {"count": paginator.page.paginator.count,
                         "data": serializer(page, many=True).data},
            }
        else:
            return {
                "current_page": 1,
                "last_page": 1,
                "data": {"count": 0,
                         "data": [],
                         }}


class PKDataView(APIView):

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
        request.GET = request.GET.copy()
        pkdata = PKData(
            request=request,
            studies_query=self._get_param("study", request),
            groups_query=self._get_param("group", request),
            individuals_query=self._get_param("individual", request),
            interventions_query=self._get_param("intervention", request),
            outputs_query=self._get_param("output", request),
        )
        start_time = time.time()
        pkdata.concise()
        concise_time =   time.time() - start_time
        print("Concise time")
        print(concise_time)

        data = {
            "studies": pkdata._paginated_data(StudyAnalysisSerializer, pkdata.studies, pkdata.studies_query),
            "groups": pkdata._paginated_data(GroupElasticSerializer,pkdata.groups, pkdata.groups_query),
            "individuals": pkdata._paginated_data(IndividualElasticSerializer,pkdata.individuals, pkdata.individuals_query),
            "interventions": pkdata._paginated_data(InterventionElasticSerializer, pkdata.interventions,pkdata.interventions_query),
            "outputs": pkdata._paginated_data(OutputElasticSerializer, pkdata.outputs, pkdata.outputs_query)
        }

        response = Response(data, status=status.HTTP_200_OK)
        return response

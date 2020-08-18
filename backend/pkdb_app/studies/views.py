from typing import Dict
import time
from django.test.client import RequestFactory

import django_filters.rest_framework
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q as DQ
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend, SearchFilterBackend
from django_elasticsearch_dsl_drf.viewsets import BaseDocumentViewSet, DocumentViewSet
from elasticsearch import helpers
from elasticsearch_dsl.query import Q

from pkdb_app.data.documents import DataAnalysisDocument, SubSetDocument
from pkdb_app.data.models import Data
from pkdb_app.data.views import SubSetViewSet
from pkdb_app.outputs.pk_calculation import Subset
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
from pkdb_app.studies.models import Study, Query, Reference
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
    filter_fields = (
        "sid",
        "name",
        "pmid",
        "title",
        "abstract",
        "journal")
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
    subsets = study.subsets.all()

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
        SubSetDocument: subsets,
    }
    if study.reference:
        docs_dict[ReferenceDocument] = study.reference
    return docs_dict


class ElasticStudyViewSet(BaseDocumentViewSet):
    document_uid_field = "sid__raw"
    lookup_field = "sid"
    document = StudyDocument
    serializer_class = StudyElasticSerializer
    pagination_class = CustomPagination
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
        'name': {'field': 'name.raw',
                 'lookups':[ LOOKUP_QUERY_IN, ],},
        'reference_name': {'field': 'reference.name.raw',
                 'lookups': [LOOKUP_QUERY_IN, ], },
        'creator': {'field': 'creator.username.raw',
                           'lookups': [LOOKUP_QUERY_IN, ], },
        'curators': {'field': 'curators.username.raw',
                    'lookups': [LOOKUP_QUERY_IN, ], },
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

        _hash = self.request.query_params.get("hash", [])
        if _hash:
            ids = list(Query.objects.get(hash=_hash).ids)
            _qs_kwargs = {'values': ids}

            self.search = self.search.query(
                'ids',
                **_qs_kwargs
            )

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
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, SearchFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = [
        'sid',
        'pmid',
        'name',
        'title',
        'abstract',]
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
                 subsets_query: dict = None,
                 studies_query: dict = None,
                 ):


        self.request = request
        self.groups_query = groups_query
        self.individuals_query = individuals_query
        self.interventions_query = {"normed":"true", **interventions_query}
        self.outputs_query = {"normed":"true", **outputs_query}
        self.subsets_query = subsets_query
        self.studies_query = studies_query

        start_time = time.time()
        studies_pks = self.study_pks()

        groups_pks = self.group_pks()
        elastic_time = time.time() - start_time
        print("Elastic Time Groups")
        print(elastic_time)

        individuals_pks = self.individual_pks()

        elastic_time = time.time() - elastic_time - start_time
        print("Elastic Time Individuals")
        print(elastic_time)

        interventions_pks = self.intervention_pks()

        elastic_time = time.time() - elastic_time - start_time
        print("Elastic Time Interventions")
        print(elastic_time)

        outputs_pks = self.output_pks()

        elastic_time = time.time() - elastic_time - start_time
        print("Elastic Time Outputs")
        print(elastic_time)



        subset_pks = self.subset_pks()


        elastic_time = time.time() - start_time
        print("Elastic Time")
        print(elastic_time)




        self.studies = Study.objects.filter(sid__in=studies_pks).only('sid','pk')
        self.groups = Group.objects.filter(pk__in=groups_pks).only('pk')
        self.individuals = Individual.objects.filter(pk__in=individuals_pks).only('pk')
        self.interventions = Intervention.objects.filter(pk__in=interventions_pks)
        self.outputs = Output.objects.filter(pk__in=outputs_pks).only('group','individual','interventions','study','data_points')
        self.subsets = Subset.objects.filter(pk__in=subset_pks)
        django_time = time.time() - start_time - elastic_time
        print("Django Time")
        print(django_time)

    def empty_get(self):
        """create an get request with no parameters in the url."""
        return RequestFactory().get("/").GET.copy()

    def _update_outputs(self):
        """ """

        outputs = self.outputs.filter(DQ(group__in=self.groups) | DQ(individual__in=self.individuals) ,study__in=self.studies, interventions__in=self.interventions)


        start_time = time.time()
        outputs_count = outputs.count()
        if outputs_count < self.outputs.count():
            self.keep_concising = True
            self.outputs = outputs

        update_outputs_time = time.time() - start_time
        print("Update Outputs Time")
        print(update_outputs_time)

    def concise(self):
        self.keep_concising = True

        while self.keep_concising:
            self.keep_concising = False

            self._update_outputs()

            self.interventions = Intervention.objects.filter(outputs__in=self.outputs).distinct()
            self.individuals = Individual.objects.filter(pk__in=Subquery(self.outputs.values("individual_id").distinct()))
            group_ids1 = Subquery(self.outputs.values("group_id"))
            group_ids2 = Subquery(self.individuals.values("group_id"))
            self.groups = Group.objects.filter(Q(pk__in=group_ids1) | Q(pk__in=group_ids2))
            self.studies = self.studies.filter(pk__in=Subquery(self.outputs.values("study_id").distinct()))
            self.subsets = self.subsets.filter(data_points__in=Subquery(self.outputs.values("data_points").distinct()))


    def intervention_pks(self):
        return self._pks(view_class=ElasticInterventionViewSet, query_dict=self.interventions_query)

    def group_pks(self):
        return self._pks(view_class=GroupViewSet, query_dict=self.groups_query)

    def individual_pks(self):
        return self._pks(view_class=IndividualViewSet, query_dict=self.individuals_query)

    def output_pks(self):
        return self._pks(view_class=ElasticOutputViewSet, query_dict=self.outputs_query )

    def subset_pks(self):
        return self._pks(view_class=SubSetViewSet, query_dict=self.subsets_query)

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
        response = queryset.source([pk_field]).scan()
        return [instance[pk_field] for instance in response]


class PKDataView(APIView):

    EXTRA = {
        "study": "studies__",
        "intervention": "interventions__",
        "group": "groups__",
        "individual": "individuals__",
        "output": "outputs__",
        "data": "data__",

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
            subsets_query=self._get_param("subsets", request),

        )
        start_time = time.time()
        pkdata.concise()
        concise_time = time.time() - start_time
        print("Concise time")
        print(concise_time)


        data = {
            "studies": list(pkdata.studies.values_list("id", flat=True)),
            "groups":  list(pkdata.groups.values_list("id", flat=True)),
            "individuals":  list(pkdata.individuals.values_list("id", flat=True)),
            "interventions":  list(pkdata.interventions.values_list("id", flat=True)),
            "outputs": list(pkdata.outputs.values_list("id", flat=True)),
            "subsets": list(pkdata.subsets.values_list("id", flat=True)),
        }
        start_time = time.time()

        resources = {}
        queries = []
        for resource, ids in data.items():


            #query = Query.objects.create(resource=resource, ids=ids)
            query = Query(resource=resource, ids=ids)
            queries.append(query)
            resources[resource] = {"hash": query.hash, "count":len(ids)}
        Query.objects.bulk_create(queries)

        concise_time = time.time() - start_time
        print("Save Ids")
        print(concise_time)

        response = Response(resources, status=status.HTTP_200_OK)


        return response

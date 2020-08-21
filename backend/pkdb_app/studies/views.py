
import tempfile
import zipfile
from collections import namedtuple
from io import StringIO
from typing import Dict
import time
import pandas as pd
from django.db import connection
from django.test.client import RequestFactory

import django_filters.rest_framework
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q as DQ, Prefetch
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend, SearchFilterBackend
from django_elasticsearch_dsl_drf.viewsets import BaseDocumentViewSet, DocumentViewSet
from elasticsearch import helpers
from elasticsearch_dsl.query import Q

from pkdb_app.data.documents import DataAnalysisDocument, SubSetDocument
from pkdb_app.data.serializers import DataAnalysisSerializer
from pkdb_app.data.views import SubSetViewSet, DataAnalysisViewSet
from pkdb_app.interventions.serializers import InterventionElasticSerializer, InterventionElasticSerializerAnalysis
from pkdb_app.outputs.serializers import OutputInterventionSerializer
from pkdb_app.subjects.serializers import GroupCharacteristicaSerializer, IndividualCharacteristicaSerializer
from rest_framework.generics import get_object_or_404
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
    StudyElasticSerializer, StudyAnalysisSerializer,
)

from django.db.models import Subquery
from django.db.models import Q
from pkdb_app.interventions.views import ElasticInterventionViewSet, ElasticInterventionAnalysisViewSet
from pkdb_app.outputs.models import Output
from pkdb_app.interventions.models import Intervention
from pkdb_app.outputs.views import ElasticOutputViewSet, OutputInterventionViewSet
from pkdb_app.studies.models import Study, Query, Reference
from pkdb_app.subjects.models import Group, Individual
from pkdb_app.subjects.views import GroupViewSet, IndividualViewSet, GroupCharacteristicaViewSet, \
    IndividualCharacteristicaViewSet


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


    @staticmethod
    def filter_on_permissions(user, queryset):

        group = user_group(user)
        if group in ["admin", "reviewer"]:
            return queryset

        elif group == "basic":
            return queryset.filter(DQ(access=PUBLIC) |
                                   DQ(creator=user) |
                                   DQ(collaborators=user) |
                                   DQ(curators=user)).distinct()

        elif group == "anonymous":
            return queryset.filter(access=PUBLIC)

    def get_queryset(self):
        queryset = super().get_queryset()
        self.filter_on_permissions(self.request.user, queryset)

    def destroy(self, request, *args, **kwargs):

        # if get object does not find  an object it stops here

        instance = self.get_object()

        related_elastic = related_elastic_dict(instance)
        delete_elastic_study(related_elastic)
        return super().destroy(request, *args, **kwargs)


###############################################################################################
# Elastic ViewSets
###############################################################################################

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

            ids = list(get_object_or_404(Query,hash=_hash).ids)
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

    returns a concise PKData
    """
    def __init__(self,
                 request,
                 interventions_query: dict = None,
                 groups_query: dict = None,
                 individuals_query: dict = None,
                 outputs_query: dict = None,
                 studies_query: dict = None,
                 ):

        #  --- Init ---
        time_start = time.time()

        self.request = request


        time_init = time.time()

        self.outputs = Output.objects.select_related("study__sid").prefetch_related(
            Prefetch(
                'interventions',
                queryset=Intervention.objects.only('id'))).only(
            'group_id', 'individual_id', "id", "interventions__id", "timecourse__id", "output_type")

        #  --- Elastic ---
        if studies_query:
            self.studies_query = studies_query
            studies_pks = self.study_pks()
            time_elastic_studies = time.time()
            self.outputs = self.outputs.filter(study__sid__in=studies_pks)

        else:
            self.outputs = self.outputs.filter(study_id__in=Subquery(StudyViewSet.filter_on_permissions(request.user,Study.objects).values_list("id", flat=True)))


        if groups_query or individuals_query:
            self.groups_query = groups_query
            groups_pks = self.group_pks()
            time_elastic_groups = time.time()

            self.individuals_query = individuals_query
            individuals_pks = self.individual_pks()
            time_elastic_individuals = time.time()

            self.outputs = self.outputs.filter(
            DQ(group_id__in=groups_pks) | DQ(individual_id__in=individuals_pks))


        if interventions_query:
            self.interventions_query = {"normed": "true", **interventions_query}
            interventions_pks = self.intervention_pks()
            time_elastic_interventions = time.time()
            self.outputs = self.outputs.filter(interventions__id__in=interventions_pks)

        if outputs_query:
            self.outputs_query = {"normed": "true", **outputs_query}
            outputs_pks = self.output_pks()
            time_elastic_outputs = time.time()
            self.outputs = self.outputs.filter(id__in=outputs_pks)

        time_elastic = time.time()

        studies = set()
        groups = set()
        individuals = set()
        interventions = set()
        outputs =set()
        timecourses =set()

        time_loop_start = time.time()

        for output in self.outputs.filter(normed=True).values("study_id","group_id", "individual_id", "id", "interventions__id", "output_type", "timecourse__id"):
            studies.add(output["study_id"])
            if output["group_id"]:
                groups.add(output["group_id"])
            else:
                individuals.add(output["individual_id"])
            outputs.add(output["id"])

            if output["output_type"] == Output.OutputTypes.Timecourse:
                timecourses.add(output["timecourse__id"])
            if output["interventions__id"]:
                interventions.add(output["interventions__id"])




        time_loop_end = time.time()




        self.ids = {
            "studies": list(studies),
            "groups": list(groups),
            "individuals": list(individuals),
            "interventions": list(interventions),
            "outputs": list(outputs),
            "timecourses": list(timecourses),
        }


        time_django = time.time()

        print("-" * 80)
        for q in connection.queries:
            print("db query:", q["time"])

        print("init:", time_init - time_start)
        print("elastic:", time_elastic - time_init)
        print("django:", time_django - time_elastic)
        print("Loop:", time_loop_end- time_loop_start)

        print("-" * 80)

    def empty_get(self):
        """create an get request with no parameters in the url."""
        return RequestFactory().get("/").GET.copy()


    def intervention_pks(self):
        return self._pks(view_class=ElasticInterventionViewSet, query_dict=self.interventions_query)

    def group_pks(self):
        return self._pks(view_class=GroupViewSet, query_dict=self.groups_query)

    def individual_pks(self):
        return self._pks(view_class=IndividualViewSet, query_dict=self.individuals_query)

    def output_pks(self):
        return self._pks(view_class=ElasticOutputViewSet, query_dict=self.outputs_query,scan_size=20000)

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

    def _pks(self, view_class: DocumentViewSet, query_dict: Dict, pk_field: str="pk", scan_size=10000):
        """
        query elastic search for pks.

        """
        self.set_request_get(query_dict)
        view = view_class(request=self.request)
        queryset = view.filter_queryset(view.get_queryset())

        response = queryset.source([pk_field]).params(size=scan_size).scan()
        return [instance[pk_field] for instance in response]

    def data_by_query_dict(self,query_dict, viewset, serializer):
        view = viewset(request=self.request)
        queryset = view.filter_queryset(view.get_queryset())
        queryset = queryset.filter("terms",**query_dict)
        return serializer(queryset.scan(), many=True).data



class PKDataView(APIView):

    EXTRA = {
        "study": "studies__",
        "intervention": "interventions__",
        "group": "groups__",
        "individual": "individuals__",
        "output": "outputs__",
        "subsets": "subsets__",

    }

    def _get_param(self, key, request):
        param = {}
        for key_request, value in request.GET.items():
            if key_request.startswith(self.EXTRA[key]):
                string_len = len(self.EXTRA[key])
                param[key_request[string_len:]] = value
        return param

    def get(self, request, *args, **kw):
        time_start_request = time.time()

        request.GET = request.GET.copy()
        pkdata = PKData(
            request=request,
            studies_query=self._get_param("study", request),
            groups_query=self._get_param("group", request),
            individuals_query=self._get_param("individual", request),
            interventions_query=self._get_param("intervention", request),
            outputs_query=self._get_param("output", request),
        )







        time_pkdata = time.time()

        resources = {}
        queries = []
        for resource, ids in pkdata.ids.items():
            query = Query(resource=resource, ids=ids)
            queries.append(query)
            resources[resource] = {"hash": query.hash, "count": len(ids)}
        Query.objects.bulk_create(queries)

        time_hash = time.time()


        if request.GET.get("download"):

            Sheet = namedtuple("Sheet", ["sheet_name", "query_dict", "viewset", "serializer"])
            table_content = {
                "studies": Sheet("Studies", {"pk":pkdata.ids["studies"]}, ElasticStudyViewSet, StudyAnalysisSerializer),
                "groups": Sheet("Groups", {"group_pk":pkdata.ids["groups"]}, GroupCharacteristicaViewSet, GroupCharacteristicaSerializer),
                "individuals": Sheet("Individuals", {"individual_pk": pkdata.ids["individuals"]}, IndividualCharacteristicaViewSet,IndividualCharacteristicaSerializer),
                "interventions": Sheet("Interventions",{"pk":pkdata.ids["interventions"]} ,ElasticInterventionAnalysisViewSet, InterventionElasticSerializerAnalysis),
                "outputs": Sheet("Outputs",{"output_pk":pkdata.ids["outputs"]}, OutputInterventionViewSet, OutputInterventionSerializer),
                "timecourses": Sheet("Timecourses", {"subset_pk": pkdata.ids["timecourses"]}, DataAnalysisViewSet,DataAnalysisSerializer),

            }
            with tempfile.SpooledTemporaryFile() as tmp:
                with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as archive:
                    for key, sheet in table_content.items():
                        print(key)
                        string_buffer = StringIO()
                        data = pkdata.data_by_query_dict(sheet.query_dict,sheet.viewset,sheet.serializer)
                        pd.DataFrame(data).to_csv(string_buffer)
                        archive.writestr(f'{key}.csv', string_buffer.getvalue())
                tmp.seek(0)
                resp = HttpResponse(tmp.read(), content_type='application/x-zip-compressed')
                resp['Content-Disposition'] = "attachment; filename=%s" % "pkdata.zip"
                return resp


        response = Response(resources, status=status.HTTP_200_OK)
        time_response = time.time()

        print("-" * 80)
        print("pkdata:", time_pkdata - time_start_request)
        print("hash:", time_hash - time_pkdata)
        print("-" * 80)
        print("total:", time_response - time_start_request)
        print("-" * 80)



        return response


import tempfile
import uuid
import zipfile
from collections import namedtuple
from datetime import datetime
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
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend, CompoundSearchFilterBackend
from django_elasticsearch_dsl_drf.viewsets import BaseDocumentViewSet, DocumentViewSet
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from elasticsearch import helpers
from elasticsearch_dsl.query import Q

from pkdb_app.data.documents import DataAnalysisDocument, SubSetDocument
from pkdb_app.data.models import SubSet, Data
from pkdb_app.data.serializers import TimecourseSerializer
from pkdb_app.data.views import SubSetViewSet
from pkdb_app.documents import  UUID_PARAM
from pkdb_app.interventions.serializers import InterventionElasticSerializerAnalysis
from pkdb_app.outputs.serializers import OutputInterventionSerializer
from pkdb_app.subjects.serializers import GroupCharacteristicaSerializer, IndividualCharacteristicaSerializer
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework import filters, status, serializers
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
from pkdb_app.subjects.models import GroupCharacteristica, IndividualCharacteristica, Group, Individual
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
from pkdb_app.studies.models import Study, IdCollection, Reference
from pkdb_app.subjects.views import GroupViewSet, IndividualViewSet, GroupCharacteristicaViewSet, \
    IndividualCharacteristicaViewSet


class ReferencesViewSet(viewsets.ModelViewSet):
    """ ReferenceViewSet """
    swagger_schema = None
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
        "journal"
    )
    search_fields = filter_fields
    permission_classes = (IsAdminOrCreatorOrCurator,)


class StudyViewSet(viewsets.ModelViewSet):
    """ StudyViewSet """
    swagger_schema = None
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
        return self.filter_on_permissions(self.request.user, queryset)

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

@method_decorator(name='list', decorator=swagger_auto_schema(manual_parameters=[UUID_PARAM]))
class ElasticStudyViewSet(BaseDocumentViewSet, APIView):
    """ Endpoint to query studies

    The studies endpoint gives access to the studies data. A study is a container of consistent
    pharmacokinetics data. This container mostly contains data reported in a single scientific paper.
    """
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
        'reference.pmid',
        'reference.title',

        'files',
        'substances.sid'
        'substances.label'
    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {
        'sid': 'sid.raw',
        'name': {
            'field': 'name.raw',
            'lookups': [LOOKUP_QUERY_IN],
        },
        'reference_name': {
            'field': 'reference.name.raw',
            'lookups': [LOOKUP_QUERY_IN],
        },
        'creator': {
            'field': 'creator.username.raw',
            'lookups': [LOOKUP_QUERY_IN],
        },
        'curators': {
            'field': 'curators.username.raw',
            'lookups': [LOOKUP_QUERY_IN]
        },
        'collaborator': 'collaborators.name.raw',
        'licence': {
            'field': 'licence.raw',
            'lookups': [LOOKUP_QUERY_IN],
        },
        'access': {
            'field': 'access.raw',
            'lookups': [LOOKUP_QUERY_IN],
        },
        'substance': 'substances.name.raw',
    }
    ordering_fields = {
        'sid': 'sid',
    }

    @swagger_auto_schema(responses={200: StudyElasticSerializer(many=False)})
    def get_object(self):
        """ Test """
        return super().get_object()

    @swagger_auto_schema(responses={200: StudyElasticSerializer(many=True)}, manual_parameters=[UUID_PARAM])
    def get_queryset(self):
        """ Test """
        group = user_group(self.request.user)

        _uuid = self.request.query_params.get("uuid", [])
        if _uuid:
            ids = list(get_object_or_404(IdCollection, uuid=_uuid, resource=self.document.Index.name).ids)

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

class StudyAnalysisViewSet(ElasticStudyViewSet):
    swagger_schema = None
    serializer_class = StudyAnalysisSerializer
    filter_fields = {
        'study_sid': {'field': 'sid.raw',
                  'lookups': [
                      LOOKUP_QUERY_IN,
                      LOOKUP_QUERY_EXCLUDE,

                  ],
                      },
        'study_name': {'field': 'name.raw',
                   'lookups': [
                       LOOKUP_QUERY_IN,
                       LOOKUP_QUERY_EXCLUDE,

                   ],
                       },
    }


class ElasticReferenceViewSet(BaseDocumentViewSet):
    """Read/query/search references. """
    swagger_schema = None
    document_uid_field = "sid__raw"
    lookup_field = "sid"
    document = ReferenceDocument
    pagination_class = CustomPagination
    permission_classes = (IsAdminOrCreatorOrCurator,)
    serializer_class = ReferenceElasticSerializer
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, OrderingFilterBackend, CompoundSearchFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = (
        'sid',
        'pmid',
        'name',
        'title',
        'abstract',
    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {
        'name': 'name.raw'
    }
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
    """ PKData represents a consistent set of pharmacokinetic data. """
    def __init__(self,
                 request,
                 concise: bool = True,
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

        self.outputs = Output.objects.filter(normed=True).select_related("study__sid").prefetch_related(
            Prefetch(
                'interventions',
                queryset=Intervention.objects.only('id'))).only(
            'group_id', 'individual_id', "id", "interventions__id", "subset__id", "output_type")


        #  --- Elastic ---
        if studies_query:
            self.studies_query = studies_query
            studies_pks = self.study_pks()
            time_elastic_studies = time.time()
            self.outputs = self.outputs.filter(study_id__in=studies_pks)

        else:
            studies_pks = StudyViewSet.filter_on_permissions(request.user,Study.objects).values_list("id", flat=True)
            self.outputs = self.outputs.filter(study_id__in=Subquery(studies_pks))

        self.studies = Study.objects.filter(id__in=studies_pks)

        if groups_query or individuals_query:
            self.groups_query = groups_query
            groups_pks = self.group_pks()
            time_elastic_groups = time.time()

            self.individuals_query = individuals_query
            individuals_pks = self.individual_pks()
            time_elastic_individuals = time.time()
            if concise:
                self.outputs = self.outputs.filter(
                DQ(group_id__in=groups_pks) | DQ(individual_id__in=individuals_pks))
            else:
                self.studies = self.studies.filter(DQ(groups__id__in=groups_pks) | DQ(individuals__id__in=individuals_pks))



        if interventions_query:
            self.interventions_query = {"normed": "true", **interventions_query}
            interventions_pks = self.intervention_pks()
            time_elastic_interventions = time.time()
            if concise:
                self.outputs = self.outputs.filter(interventions__id__in=interventions_pks)
            else:
                self.studies = self.studies.filter(interventions__id__in=interventions_pks)

        if outputs_query:
            self.outputs_query = {"normed": "true", **outputs_query}
            outputs_pks = self.output_pks()
            time_elastic_outputs = time.time()
            if concise:
                self.outputs = self.outputs.filter(id__in=outputs_pks)
            else:

                self.studies = self.studies.filter(outputs__id__in=outputs_pks)


        time_elastic = time.time()

        time_loop_start = time.time()
        if concise:
            studies = set()
            groups = set()
            individuals = set()
            interventions = set()
            outputs = set()
            timecourses = set()
            scatters = set()

            for output in self.outputs.values("study_id", "group_id", "individual_id", "id", "interventions__id", "subset__id", "output_type"):
                studies.add(output["study_id"])
                if output["group_id"]:
                    groups.add(output["group_id"])
                else:
                    individuals.add(output["individual_id"])
                outputs.add(output["id"])

                if output["interventions__id"]:
                    interventions.add(output["interventions__id"])

                if output["output_type"] == Output.OutputTypes.Timecourse:
                    timecourses.add(output["subset__id"])

                if (output["subset__id"] is not None) & (output["output_type"] == Output.OutputTypes.Array):
                    scatters.add(output["subset__id"])

            self.ids = {
                "studies": list(studies),
                "groups": list(groups),
                "individuals": list(individuals),
                "interventions": list(interventions),
                "outputs": list(outputs),
                "timecourses": list(timecourses),
                "scatters": list(scatters),
            }

        else:
            study_pks = self.studies.distinct().values_list("pk", flat=True)

            self.interventions = Intervention.objects.filter(study_id__in=study_pks, normed=True)
            self.groups = Group.objects.filter(study_id__in=study_pks)
            self.individuals = Individual.objects.filter(study_id__in=study_pks)
            self.outputs = Output.objects.filter(study_id__in=study_pks, normed=True)
            self.subset = SubSet.objects.filter(study_id__in=study_pks)

            self.ids = {
                "studies": list(study_pks),
                "groups": list(self.groups.values_list("pk", flat=True)),
                "individuals": list(self.individuals.values_list("pk", flat=True)),
                "interventions": list(self.interventions.values_list("pk", flat=True)),
                "outputs": list(self.outputs.values_list("pk", flat=True)),
                "timecourses": list(self.subset.filter(data__data_type=Data.DataTypes.Timecourse).values_list("pk", flat=True)),
                "scatters": list(self.subset.filter(data__data_type=Data.DataTypes.Scatter).values_list("pk", flat=True)),
            }

        time_loop_end = time.time()

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
        return self._pks(view_class=ElasticStudyViewSet, query_dict=self.studies_query, pk_field="pk")

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

    def data_by_query_dict(self,query_dict, viewset, serializer, boost):
        view = viewset(request=self.request)
        queryset = view.filter_queryset(view.get_queryset())
        if boost:
            queryset=queryset.filter("terms", **query_dict).source(serializer.Meta.fields)
            return [hit.to_dict() for hit in queryset.params(size=5000).scan()]

        else:
            queryset = queryset.filter("terms", **query_dict)

            return serializer(queryset.params(size=5000).scan(), many=True).data




class ResponseSerializer(serializers.Serializer):
    """Documentation of response schema."""
    uuid = serializers.UUIDField(
        required=True,
        allow_null=False,
        help_text="The resulting queries can be accessed by adding this uuid as "
               "an argument to the endpoints: /studies/, /groups/, /individuals/, /outputs/, /timecourses/, /subsets/."
    )
    studies = serializers.IntegerField(required=True, allow_null=False, help_text="Number of resulting studies.")
    groups = serializers.IntegerField(required=True, allow_null=False, help_text="Number of resulting groups.")
    individuals = serializers.IntegerField(required=True, allow_null=False, help_text="Number of resulting individuals.")
    outputs = serializers.IntegerField(required=True, allow_null=False, help_text="Number of resulting outputs.")
    timecourses = serializers.IntegerField(required=True, allow_null=False, help_text="Number of resulting timecourses.")
    scatters = serializers.IntegerField(required=True, allow_null=False, help_text="Number of resulting scatters.")


class PKDataView(APIView):
    """Endpoint to filter and query data.

    The filter endpoint is the main endpoint for complex queries, such as searches and filtering. A filter query returns
    a unique id corresponding to the query, which allows to access the complete set of tables
    (studies, groups, individuals and interventions, outputs, timecourses, and scatters) for the search.
    In addition an overview of the counts in the tables is provided.
    ```
    {
      "uuid": "6a15733e-0659-4224-985a-9c71120911d5",
      "studies": 430,
      "groups": 887,
      "individuals": 5748,
      "interventions": 1291,
      "outputs": 70636,
      "timecourses": 2946,
      "scatters": 37
    }
    ```
    Two main parameters control the output of the filter query:
    * `download`: which allows to download the results as zip archive
    * `concise`: switching between concise and non-concise data

    The filter endpoint provides the option of filtering on any of the tables mentioned
    early. Arguments can be provided with the prefixes `['studies__' , 'groups__', 'individuals__', 'interventions__',
    'outputs__', 'subsets__']` for the respective tables.
    """

    EXTRA = {
        "study": "studies__",
        "group": "groups__",
        "individual": "individuals__",
        "intervention": "interventions__",
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

    # additional parameters
    download__param = openapi.Parameter(
        'download',
        openapi.IN_QUERY,
        description="The download parameter allows to download the results of the filter query. "
                    "If set to True, a zip archive is returned containing '.csv' files for all tables.",
        type=openapi.TYPE_BOOLEAN,
        default=False
    )

    concise__param = openapi.Parameter(
        'concise',
        openapi.IN_QUERY,
        description="The concise parameter to reduce the set to the most concise amount "
                    "of instances in each table or to return studies which meet the "
                    "filtered criteria and all the content (related set tables) of the "
                    "studies. E.g. Filtering for “thalf -- elimination half life” with “"
                    "concise:true” will return all studies containing “thalf” outputs, "
                    "all interventions which have been applied before measuring thalf, "
                    "and all groups and individuals for which half has been measured. "
                    "Filtering for “thalf -- elimination half life” with “concise:false” "
                    "will return all studies containing “thalf” outputs, all interventions "
                    "which have been applied in these studies, and all groups and individuals "
                    "in these studies.",
        type=openapi.TYPE_BOOLEAN,
        default=True
    )

    @swagger_auto_schema(
        manual_parameters=[concise__param, download__param],
        responses={
            200: openapi.Response(
                description="Returns a 'uuid' and the number of entries for each table. "
                            "This 'uuid' can be used as an argument in the endpoints of the "
                            "tables (studies, groups, individuals, interventions, outputs, subsets). "
                            "For subsets endpoint the 'data_type'['timecourse', 'scatter'] "
                            "has to be provided.",
                schema=ResponseSerializer)
        }

    )

    def get(self, request, *args, **kw):
        time_start_request = time.time()

        request.GET = request.GET.copy()
        pkdata = PKData(
            request=request,
            concise="false" != request.GET.get("concise", True),
            studies_query=self._get_param("study", request),
            groups_query=self._get_param("group", request),
            individuals_query=self._get_param("individual", request),
            interventions_query=self._get_param("intervention", request),
            outputs_query=self._get_param("output", request),
        )

        time_pkdata = time.time()

        # calculation of uuid
        queries = []
        delete_queries = IdCollection.objects.filter(expire__lte=datetime.now())
        delete_queries.delete()
        _uuid = uuid.uuid4()
        resources = {"uuid": _uuid}
        for resource, ids in pkdata.ids.items():
            query = IdCollection(resource=resource, ids=ids, uuid=_uuid)
            queries.append(query)
            resources[resource] = len(ids)
        IdCollection.objects.bulk_create(queries)

        time_uuid = time.time()

        if request.GET.get("download") == "true":



            def serialize_scatters(ids):
                scatter_subsets = SubSet.objects.filter(id__in=ids)
                return [t.scatter_representation for t in scatter_subsets]

            def serialize_timecourses(ids):
                scatter_subsets = SubSet.objects.filter(id__in=ids)
                return [t.timecourse_representation for t in scatter_subsets]

            Sheet = namedtuple("Sheet", ["sheet_name", "query_dict", "viewset", "serializer", "function", "boost_performance",])
            table_content = {
                "studies": Sheet("Studies", {"pk": pkdata.ids["studies"]}, ElasticStudyViewSet, StudyAnalysisSerializer, None, False),
                "groups": Sheet("Groups", {"group_pk": pkdata.ids["groups"]}, GroupCharacteristicaViewSet, GroupCharacteristicaSerializer, None, True,),
                "individuals": Sheet("Individuals", {"individual_pk": pkdata.ids["individuals"]}, IndividualCharacteristicaViewSet,IndividualCharacteristicaSerializer, None, True),
                "interventions": Sheet("Interventions", {"pk": pkdata.ids["interventions"]} ,ElasticInterventionAnalysisViewSet, InterventionElasticSerializerAnalysis, None, False),
                "outputs": Sheet("Outputs", {"output_pk": pkdata.ids["outputs"]}, OutputInterventionViewSet, OutputInterventionSerializer,None, True),
                "timecourses": Sheet("Timecourses", {"pk": pkdata.ids["timecourses"]}, SubSetViewSet, TimecourseSerializer, None, False),
                "scatters": Sheet("Scatter", {"subset_pk": pkdata.ids["scatters"]}, None, None, serialize_scatters, None),
            }


            with tempfile.SpooledTemporaryFile() as tmp:
                with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as archive:
                    download_times = {}

                    for key, sheet in table_content.items():
                        download_time_start =  time.time()

                        string_buffer = StringIO()
                        if sheet.function:
                            df = pd.DataFrame(sheet.function(sheet.query_dict["subset_pk"]))
                            df.to_csv(string_buffer)
                            archive.writestr(f'{key}.csv', string_buffer.getvalue())
                            download_times[key] = time.time() - download_time_start

                        else:
                            df = pd.DataFrame(pkdata.data_by_query_dict(sheet.query_dict,sheet.viewset,sheet.serializer, sheet.boost_performance))
                            if len(df) < 0:
                                df = df[sheet.serializer.Meta.fields]
                            df.to_csv(string_buffer)
                            archive.writestr(f'{key}.csv', string_buffer.getvalue())
                            download_times[key] = time.time() - download_time_start
                            """
                            if key == "outputs":
                                string_buffer = StringIO()
                                download_time_start_timecourse = time.time()
                                def sorted_tuple(v):
                                    return sorted(tuple(v))
                                timecourse_df = df[df["output_type"] == Output.OutputTypes.Timecourse]

                                def unique_or_sorted_list(v):
                                    values = v.unique()
                                    if len(values) == 1:
                                        return values[0]
                                    return tuple(values)

                                if len(timecourse_df) !=0:
                                    #timecourse_df = pd.pivot_table(data=timecourse_df,index=["output_pk"], aggfunc=sorted_tuple, dropna=False).apply(SubSet.to_list)
                                    #timecourse_df = pd.pivot_table(data=timecourse_df,index=["label","study_name"], aggfunc=tuple, dropna=False).apply(SubSet.to_list)
                                    timecourse_df = pd.pivot_table(data=timecourse_df, index=["output_pk"],aggfunc=unique_or_sorted_list,fill_value=np.NAN)#.reset_index()
                                    timecourse_df = pd.pivot_table(data=timecourse_df,index=["label","study_name"], aggfunc= unique_or_sorted_list, fill_value=np.NAN)#.reset_index()
                                    print(timecourse_df.columns)

                                    #timecourse_df = timecourse_df[table_content["outputs"].serializer.Meta.fields]
                                else:
                                    timecourse_df = pd.DataFrame([])
                                timecourse_df.to_csv(string_buffer)
                                archive.writestr('timecourse.csv', string_buffer.getvalue())
                                download_times["timecourse"] = time.time()-download_time_start_timecourse
                                """



                    archive.write('download_extra/README.md', 'README.md')
                    archive.write('download_extra/TERMS_OF_USE.md', 'TERMS_OF_USE.md')



                tmp.seek(0)
                resp = HttpResponse(tmp.read(), content_type='application/x-zip-compressed')
                resp['Content-Disposition'] = "attachment; filename=%s" % "pkdata.zip"
                print("-" * 80)
                print("File Creation")
                for k, v in download_times.items():
                    print(k, v)

                return resp

        response = Response(resources, status=status.HTTP_200_OK)
        time_response = time.time()

        print("-" * 80)
        print("pkdata:", time_pkdata - time_start_request)
        print("uuid:", time_uuid - time_pkdata)
        print("-" * 80)
        print("total:", time_response - time_start_request)
        print("-" * 80)

        return response

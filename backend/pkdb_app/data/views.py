from django.utils.decorators import method_decorator
from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE
from django_elasticsearch_dsl_drf.filter_backends import (
    FilteringFilterBackend,
    IdsFilterBackend,
    MultiMatchSearchFilterBackend
)
from django_elasticsearch_dsl_drf.viewsets import BaseDocumentViewSet
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView

from pkdb_app.documents import AccessView, UUID_PARAM
from pkdb_app.data.documents import DataAnalysisDocument, SubSetDocument
from pkdb_app.data.serializers import DataAnalysisSerializer, SubSetElasticSerializer, TimecourseSerializer

from pkdb_app.pagination import CustomPagination


class DataAnalysisViewSet(AccessView):
    swagger_schema = None
    document = DataAnalysisDocument
    serializer_class = DataAnalysisSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    ignore = [404]
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = (
        'study_sid',
        'study_name',
        'output_pk',
        "data_pk",
    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {
        'study_sid': {
            'field': 'study_sid.raw',
            'lookups': [
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_EXCLUDE,
            ],
        },
        'study_name': {
            'field': 'study_name.raw',
            'lookups': [
               LOOKUP_QUERY_IN,
               LOOKUP_QUERY_EXCLUDE,
            ],
        },
        'output_pk': {
            'field': 'output_pk',
            'lookups': [
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_EXCLUDE,
            ],
        },
    }

class SubSetViewSet(AccessView):
    """ Endpoint to query subsets (timecourses and scatters)

    The subets endpoint gives access to the subset data. A Subset is a collection of outputs which can be either a
    timecourse or scatter. A timecourse subset consists of outputs measured at different time points. A scatter subset
    contains correlated data which commonly are displayed as scatter plots.
    """
    #document_uid_field = "id"
    lookup_field = "id"
    ignore = [404]
    document = SubSetDocument
    serializer_class = SubSetElasticSerializer
    pagination_class = CustomPagination
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = (
         "name",
         "data_type",
         "study.sid",
         "study.name",
         "array.data_points.point.outputs.group.name",
         "array.data_points.point.outputs.individual.name",
         "array.data_points.point.outputs.interventions.name",
         "array.data_points.point.outputs.measurement_type.label",
         "array.data_points.point.outputs.choice.label",
         "array.data_points.point.outputs.substance.label",
         "array.data_points.point.outputs.tissue.label",
    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {'operator': 'and'}
    filter_fields = {
        "name": "name.raw",
        "data_type": "data_type.raw"
    }
    @swagger_auto_schema(responses={200: SubSetElasticSerializer(many=False)})
    def get_object(self):
        """ Test """
        return super().get_object()

class TimecourseViewSet(AccessView):
    """ Endpoint to query timecourses

    The timecourses endpoints gives access to timecourses.
    """
    document = SubSetDocument
    serializer_class = TimecourseSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = (
         "name",
         "data_type",
         "study.sid",
         "study.name",
         "array.data_points.point.outputs.group.name",
         "array.data_points.point.outputs.individual.name",
         "array.data_points.point.outputs.interventions.name",
         "array.data_points.point.outputs.measurement_type.label",
         "array.data_points.point.outputs.choice.label",
         "array.data_points.point.outputs.substance.label",
         "array.data_points.point.outputs.tissue.label",
    )
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {'operator': 'and'}
    filter_fields = {
        'study_sid': {'field': 'study_sid.raw',
                      'lookups': [
                          LOOKUP_QUERY_IN,
                          LOOKUP_QUERY_EXCLUDE,

                      ],
                      },
        'study_name': {'field': 'study_name.raw',
                       'lookups': [
                           LOOKUP_QUERY_IN,
                           LOOKUP_QUERY_EXCLUDE,

                       ],
                       },

    }

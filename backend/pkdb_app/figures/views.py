from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN, LOOKUP_QUERY_EXCLUDE
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend
from pkdb_app.documents import AccessView
from pkdb_app.figures.documents import FigureAnalysisDocument
from pkdb_app.figures.serializers import FigureAnalysisSerializer

from pkdb_app.pagination import CustomPagination


###############################################################################################
# Elastic Views
###############################################################################################



class FigureAnalysisViewSet(AccessView):
    document = FigureAnalysisDocument
    serializer_class = FigureAnalysisSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend]
    search_fields = ('study_sid','study_name', 'output_pk',)
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
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
        'output_pk': {'field': 'output_pk',
                      'lookups': [
                          LOOKUP_QUERY_IN,
                          LOOKUP_QUERY_EXCLUDE,
                      ],
                      },

    }


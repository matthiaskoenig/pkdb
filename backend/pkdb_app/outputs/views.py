from django.urls import reverse
from django_elasticsearch_dsl_drf.constants import LOOKUP_QUERY_IN
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend, MultiMatchSearchFilterBackend
from pkdb_app.categorials.models import MeasurementType, Tissue
from rest_framework import viewsets
from rest_framework.response import Response

from pkdb_app.documents import AccessView
from pkdb_app.outputs.models import Output, OutputIntervention, TimecourseIntervention
from .documents import OutputDocument, TimecourseDocument
from .serializers import (OutputElasticSerializer, TimecourseElasticSerializer, OutputAnalysisSerializer,
                          OutputSerializer, OutputInterventionSerializer, TimecourseInterventionSerializer)
from ..pagination import CustomPagination
import pandas as pd
import numpy as np
import math
###############################################################################################
# Option Views
###############################################################################################


class OutputOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
        options = {}
        options["measurememnt_types"] = {k.name: k._asdict() for k in MeasurementType.objects.all()}
        options["substances"] = reverse('substances_elastic-list')
        options["tissue"] =  [k.name for k in Tissue.objects.all()]

        return options

    def list(self, request):
        return Response(self.get_options())

class TimecourseOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
            options = {}
            options["measurememnt_types"] = {k.name: k._asdict() for k in MeasurementType.objects.all()}
            options["substances"] = reverse('substances_elastic-list')
            options["tissue"] = [k.name for k in Tissue.objects.all()]
            return options

    def list(self, request):
        return Response(self.get_options())



###############################################################################################
# Elastic Views
###############################################################################################

class ElasticOutputViewSet(AccessView):
    document = OutputDocument
    serializer_class = OutputElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,MultiMatchSearchFilterBackend]
    search_fields = ('study','measurement_type','substance','group.name', 'individual.name', "tissue",'time_unit','interventions.name')
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {'pk':'pk',
                     'study':'study.raw',
                     'tissue':"tissue.raw",
                     'time':'time.raw',
                     'choice': 'choice.raw',
                     'normed':'normed',
                     'calculated':'calculated',
                     'unit':'unit',
                     'access':'access',
                     'substance':'substance',
                     'measurement_type':'measurement_type.raw',
                     'group_pk': {'field': 'group.pk',
                                    'lookups': [
                                        LOOKUP_QUERY_IN,
                                    ],
                                },
                     'timecourse_pk': {'field': 'timecourse.pk',
                                  'lookups': [
                                      LOOKUP_QUERY_IN,
                                  ],
                                  },
                     'individual_pk': {'field': 'individual.pk',
                                  'lookups': [
                                      LOOKUP_QUERY_IN,
                                  ]},
                     'interventions_pk': {'field': 'interventions.pk',
                                                         'lookups': [
                                                             LOOKUP_QUERY_IN,
                                                         ],
                                  }}

    ordering_fields = {'measurement_type':'measurement_type.raw',
                       'tissue':'tissue.raw',
                       'substance':'substance',
                       'group': 'group.name',
                       'individual': 'individual.name',
                       'value':'value',
                       }

class OutputInterventionViewSet(viewsets.ModelViewSet):
    queryset = OutputIntervention.objects.all().select_related('intervention', 'output','intervention__ex__interventionset__study',)
    serializer_class = OutputInterventionSerializer
    model = OutputIntervention

class TimecourseInterventionViewSet(viewsets.ModelViewSet):
    queryset = TimecourseIntervention.objects.all().select_related('intervention', 'timecourse','intervention__ex__interventionset__study',)
    serializer_class = TimecourseInterventionSerializer
    model = TimecourseIntervention

class OutputAnalysisViewSet(ElasticOutputViewSet):
    #pagination_class = None
    #paginator = None
    #PAGE_SIZE = 10000

    #def paginate_queryset(self, queryset):
    #       return None

    def list(self, request, *args, **kwargs):
        results = super().list(request, *args, **kwargs)

        df = pd.DataFrame(results.data["data"]["data"])
        #df = pd.DataFrame(results.data)
        #print(len(df))

        lst_col = "interventions"
        df = pd.DataFrame({col: np.repeat(df[col].values, df[lst_col].str.len())
                             for col in df.columns.difference([lst_col])}).assign(
            **{lst_col: np.concatenate(df[lst_col].values)})[df.columns.tolist()]

        df["intervention_pk"] = df["interventions"].apply(lambda intervention: intervention.get("pk",None))

        def get_pk(data):
            if isinstance(data,dict):
               return data.get("pk",None)


        df["group_pk"] = df["group"].apply(get_pk)
        df["individual_pk"] = df["individual"].apply(get_pk)
        df["timecourse_pk"] = df["timecourse"].apply(get_pk)
        df["individual_pk"] = df["individual"].apply(get_pk)

        df = df.where(df.notnull(), None)

        del df["raw"]
        del df["timecourse"]
        del df["interventions"]
        del df["individual"]
        del df["group"]
        del df["allowed_users"]


        results.data["data"]["data"] = df.to_dict('records')
        del results.data["data"]["count"]
        #results.data = df.to_dict('records')
        return results




class ElasticTimecourseViewSet(AccessView):
    document = TimecourseDocument
    serializer_class = TimecourseElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,MultiMatchSearchFilterBackend]
    search_fields = ('study','measurement_type','substance',"tissue",'time_unit','group.name', 'individual.name','interventions.name')
    multi_match_search_fields = {field: {"boost": 1} for field in search_fields}
    multi_match_options = {
        'operator': 'and'
    }
    filter_fields = {'pk': 'pk',
                     'normed': 'normed',
                     'study': 'study.raw',
                     'substance': 'substance',
                     'measurement_type': 'measurement_type.raw',
                     'group_pk': {'field': 'group.pk',
                                  'lookups': [
                                      LOOKUP_QUERY_IN,
                                  ],
                                  },
                     'individual_pk': {'field': 'individual.pk',
                                       'lookups': [
                                           LOOKUP_QUERY_IN,
                                       ],
                                       }}
    ordering_fields = {'measurement_type':'measurement_type.raw',
                       'tissue':'tissue.raw',
                       'group':'group.name',
                       'individual': 'individual.name',
                       'substance':'substance',
                       }

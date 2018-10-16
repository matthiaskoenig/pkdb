import django_filters.rest_framework
from django_elasticsearch_dsl_drf.constants import SUGGESTER_TERM, SUGGESTER_PHRASE, SUGGESTER_COMPLETION
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, SearchFilterBackend, \
    SuggesterFilterBackend, OrderingFilterBackend
from django_elasticsearch_dsl_drf.pagination import PageNumberPagination
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from rest_framework import viewsets
from rest_framework.response import Response

from pkdb_app.categoricals import INTERVENTION_DICT, INTERVENTION_ROUTE, INTERVENTION_FORM, INTERVENTION_APPLICATION, \
    OUTPUT_TISSUE_DATA, PK_DATA_DICT
from pkdb_app.interventions.documents import SubstanceDocument, InterventionDocument, OutputDocument
from pkdb_app.interventions.models import (
    Substance,
    InterventionSet,
    OutputSet,
    Intervention,
    Output,
    Timecourse,
    InterventionEx, OutputEx, TimecourseEx)
from pkdb_app.interventions.serializers import (
    SubstanceSerializer,
    SubstanceReadSerializer,
    InterventionSetReadSerializer,
    OutputSetReadSerializer,
    InterventionReadSerializer,
    OutputReadSerializer,
    TimecourseReadSerializer,
    InterventionExReadSerializer, OutputExReadSerializer, TimecourseExReadSerializer, InterventionElasticSerializer,
    OutputElasticSerializer)
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticatedOrReadOnly

from pkdb_app.pagination import CustomPagination
from pkdb_app.units import TIME_UNITS


class SubstanceViewSet(viewsets.ModelViewSet):
    queryset = Substance.objects.all()
    serializer_class = SubstanceSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


###############################################################################################
# Read Views
###############################################################################################


class InterventionSetReadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InterventionSet.objects.all()
    serializer_class = InterventionSetReadSerializer
    permission_classes = (AllowAny,)


class InterventionReadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Intervention.objects.all()
    serializer_class = InterventionReadSerializer
    permission_classes = (AllowAny,)
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
    )
    filter_fields = ("final",)

class InterventionOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
        options = {}
        options["categories"] = {k: item._asdict() for k, item in sorted(INTERVENTION_DICT.items())}
        options["substances"] = map(str, Substance.objects.all().order_by('name'))
        options["route"] = INTERVENTION_ROUTE
        options["form"] = INTERVENTION_FORM
        options["application"] = INTERVENTION_APPLICATION
        options["time_unit"] = TIME_UNITS
        return options

    def list(self, request):
        return Response(self.get_options())

class OutputOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
        options = {}
        options["pktypes"] = {k:item._asdict() for k, item in sorted(PK_DATA_DICT.items())}
        options["substances"] = map( str, Substance.objects.all().order_by('name'))
        options["tissue"] = OUTPUT_TISSUE_DATA
        options["time_unit"] = TIME_UNITS
        return options

    def list(self, request):
        return Response(self.get_options())

class TimecourseOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
            options = {}
            options["pktypes"] = {k: item._asdict() for k, item in sorted(PK_DATA_DICT.items())}
            options["substances"] = map(str, Substance.objects.all().order_by('name'))
            options["tissue"] = OUTPUT_TISSUE_DATA
            options["time_unit"] = TIME_UNITS
            return options

    def list(self, request):
        return Response(self.get_options())



class InterventionExReadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InterventionEx.objects.all()
    serializer_class = InterventionExReadSerializer
    permission_classes = (AllowAny,)


class OutputSetReadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OutputSet.objects.all()
    serializer_class = OutputSetReadSerializer
    permission_classes = (AllowAny,)


class OutputReadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Output.objects.all()
    serializer_class = OutputReadSerializer
    permission_classes = (AllowAny,)
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
    )
    filter_fields = ("final",)


class OutputExReadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OutputEx.objects.all()
    serializer_class = OutputExReadSerializer
    permission_classes = (AllowAny,)


class TimecourseReadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Timecourse.objects.all()
    serializer_class = TimecourseReadSerializer
    permission_classes = (AllowAny,)
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
    )
    filter_fields = ("final",)


class TimecourseExReadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TimecourseEx.objects.all()
    serializer_class = TimecourseExReadSerializer
    permission_classes = (AllowAny,)


class SubstanceReadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Substance.objects.all()
    serializer_class = SubstanceReadSerializer
    permission_classes = (AllowAny,)


class ElasticSubstanceViewSet(DocumentViewSet):
    document = SubstanceDocument
    serializer_class = SubstanceSerializer
    pagination_class = CustomPagination
    lookup_field = "pk"
    filter_backends = [FilteringFilterBackend,SearchFilterBackend]
    search_fields = ('name',)
    filter_fields = {'name': 'name.raw',}


class ElasticInterventionViewSet(DocumentViewSet):
    document = InterventionDocument
    serializer_class = InterventionElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "pk"
    filter_backends = [FilteringFilterBackend,OrderingFilterBackend,SearchFilterBackend]
    search_fields = ('name','category','substance.name',"form","application",'route','time_unit')
    filter_fields = {'name': 'name.raw','pk':'pk'}
    ordering_fields = {'name': 'name.raw',
                       'category':'category.raw',
                       'choice':'choice.raw',
                       'application':'application.raw',
                       'substance':'substance.name',
                       'value':'value'}

class ElasticOutputViewSet(DocumentViewSet):
    document = OutputDocument
    serializer_class = OutputElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "pk"
    filter_backends = [FilteringFilterBackend,OrderingFilterBackend,SearchFilterBackend]
    search_fields = ('pktype','substance.name',"tissue",'time_unit')
    filter_fields = {'pk':'pk'}
    ordering_fields = {'pktype':'pktype.raw',
                       'tissue':'tissue.raw',
                       'substance':'substance.name',
                       'value':'value',
                       }

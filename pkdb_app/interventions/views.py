import django_filters.rest_framework
from rest_framework import viewsets
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
    InterventionExReadSerializer, OutputExReadSerializer, TimecourseExReadSerializer)
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticatedOrReadOnly


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

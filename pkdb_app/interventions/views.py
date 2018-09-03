
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
from rest_framework.permissions import AllowAny, IsAdminUser


class SubstanceViewSet(viewsets.ModelViewSet):
    queryset = Substance.objects.all()
    serializer_class = SubstanceSerializer
    permission_classes = (AllowAny,)


###############################################################################################
# Read Views
###############################################################################################


class InterventionSetReadViewSet(viewsets.ModelViewSet):
    queryset = InterventionSet.objects.all()
    serializer_class = InterventionSetReadSerializer
    permission_classes = (AllowAny,)


class InterventionReadViewSet(viewsets.ModelViewSet):
    queryset = Intervention.objects.all()
    serializer_class = InterventionReadSerializer
    permission_classes = (AllowAny,)


class InterventionExReadViewSet(viewsets.ModelViewSet):
    queryset = InterventionEx.objects.all()
    serializer_class = InterventionExReadSerializer
    permission_classes = (AllowAny,)


class OutputSetReadViewSet(viewsets.ModelViewSet):
    queryset = OutputSet.objects.all()
    serializer_class = OutputSetReadSerializer
    permission_classes = (AllowAny,)


class OutputReadViewSet(viewsets.ModelViewSet):
    queryset = Output.objects.all()
    serializer_class = OutputReadSerializer
    permission_classes = (AllowAny,)


class OutputExReadViewSet(viewsets.ModelViewSet):
    queryset = OutputEx.objects.all()
    serializer_class = OutputExReadSerializer
    permission_classes = (AllowAny,)


class TimecourseReadViewSet(viewsets.ModelViewSet):
    queryset = Timecourse.objects.all()
    serializer_class = TimecourseReadSerializer
    permission_classes = (AllowAny,)


class TimecourseExReadViewSet(viewsets.ModelViewSet):
    queryset = TimecourseEx.objects.all()
    serializer_class = TimecourseExReadSerializer
    permission_classes = (AllowAny,)


class SubstanceReadViewSet(viewsets.ModelViewSet):
    queryset = Substance.objects.all()
    serializer_class = SubstanceReadSerializer
    permission_classes = (AllowAny,)


from rest_framework import viewsets
from pkdb_app.interventions.models import Substance, InterventionSet, OutputSet, Intervention, Output, Timecourse
from pkdb_app.interventions.serializers import SubstanceSerializer, SubstanceReadSerializer, \
    InterventionSetReadSerializer, OutputSetReadSerializer, InterventionReadSerializer, OutputReadSerializer, \
    TimecourseReadSerializer
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


class OutputSetReadViewSet(viewsets.ModelViewSet):
    queryset = OutputSet.objects.all()
    serializer_class = OutputSetReadSerializer
    permission_classes = (AllowAny,)


class OutputReadViewSet(viewsets.ModelViewSet):
    queryset = Output.objects.all()
    serializer_class = OutputReadSerializer
    permission_classes = (AllowAny,)


class TimecourseReadViewSet(viewsets.ModelViewSet):
    queryset = Timecourse.objects.all()
    serializer_class = TimecourseReadSerializer
    permission_classes = (AllowAny,)


class SubstanceReadViewSet(viewsets.ModelViewSet):
    queryset = Substance.objects.all()
    serializer_class = SubstanceReadSerializer
    permission_classes = (AllowAny,)
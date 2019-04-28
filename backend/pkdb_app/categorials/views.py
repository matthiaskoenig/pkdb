from pkdb_app.categorials.models import InterventionType, CharacteristicType, PharmacokineticType
from pkdb_app.categorials.serializers import InterventionTypeSerializer, CharacteristicTypeSerializer, \
    PharmacokineticTypeSerializer
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser


class InterventionTypeViewSet(viewsets.ModelViewSet):
    queryset = InterventionType.objects.all()
    serializer_class = InterventionTypeSerializer
    permission_classes = (IsAdminUser,)
    lookup_field = "url_slug"


class CharacteristicTypeViewSet(viewsets.ModelViewSet):
    queryset = CharacteristicType.objects.all()
    serializer_class = CharacteristicTypeSerializer
    permission_classes = (IsAdminUser,)
    lookup_field = "url_slug"


class PharmacokineticTypeViewSet(viewsets.ModelViewSet):
    queryset = PharmacokineticType.objects.all()
    serializer_class = PharmacokineticTypeSerializer
    permission_classes = (IsAdminUser,)
    lookup_field = "url_slug"


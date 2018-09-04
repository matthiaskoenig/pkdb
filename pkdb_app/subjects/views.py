from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework import viewsets
from pkdb_app.subjects.models import (
    DataFile,
    Characteristica,
    Individual,
    Group,
    GroupSet,
    IndividualSet,
    GroupEx, CharacteristicaEx, IndividualEx)
from pkdb_app.subjects.serializers import (
    DataFileSerializer,
    DataFileReadSerializer,
    CharacteristicaReadSerializer,
    IndividualReadSerializer,
    GroupReadSerializer,
    GroupSetReadSerializer,
    IndividualSetReadSerializer,
    GroupExReadSerializer, CharacteristicaExReadSerializer, IndividualExReadSerializer)


class DataFileViewSet(viewsets.ModelViewSet):

    queryset = DataFile.objects.all()
    serializer_class = DataFileSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
############################################################
#Read Views
###########################################################

class DataFileReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = DataFile.objects.all()
    serializer_class = DataFileReadSerializer
    permission_classes = (AllowAny,)


class CharacteristicaReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Characteristica.objects.all()
    serializer_class = CharacteristicaReadSerializer
    permission_classes = (AllowAny,)

class CharacteristicaExReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = CharacteristicaEx.objects.all()
    serializer_class = CharacteristicaExReadSerializer
    permission_classes = (AllowAny,)

class IndividualReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Individual.objects.all()
    serializer_class = IndividualReadSerializer
    permission_classes = (AllowAny,)

class IndividualExReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = IndividualEx.objects.all()
    serializer_class = IndividualExReadSerializer
    permission_classes = (AllowAny,)

class GroupReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Group.objects.all()
    serializer_class = GroupReadSerializer
    permission_classes = (AllowAny,)

class GroupExReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = GroupEx.objects.all()
    serializer_class = GroupExReadSerializer
    permission_classes = (AllowAny,)

class GroupSetReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = GroupSet.objects.all()
    serializer_class = GroupSetReadSerializer
    permission_classes = (AllowAny,)


class IndividualSetReadViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = IndividualSet.objects.all()
    serializer_class = IndividualSetReadSerializer
    permission_classes = (AllowAny,)

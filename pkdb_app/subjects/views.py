from rest_framework.permissions import AllowAny
from rest_framework import viewsets
from pkdb_app.subjects.models import DataFile, Characteristica, Individual, Group, GroupSet, IndividualSet
from pkdb_app.subjects.serializers import DataFileSerializer, DataFileReadSerializer, CharacteristicaReadSerializer, \
    IndividualReadSerializer, GroupReadSerializer, GroupSetReadSerializer, IndividualSetReadSerializer


class DataFileViewSet(viewsets.ModelViewSet):

    queryset = DataFile.objects.all()
    serializer_class = DataFileSerializer
    permission_classes = (AllowAny,)


class DataFileReadViewSet(viewsets.ModelViewSet):

    queryset = DataFile.objects.all()
    serializer_class = DataFileReadSerializer
    permission_classes = (AllowAny,)

class CharacteristicaReadViewSet(viewsets.ModelViewSet):

    queryset = Characteristica.objects.all()
    serializer_class = CharacteristicaReadSerializer
    permission_classes = (AllowAny,)

class IndividualReadViewSet(viewsets.ModelViewSet):

    queryset = Individual.objects.all()
    serializer_class = IndividualReadSerializer
    permission_classes = (AllowAny,)

class GroupReadViewSet(viewsets.ModelViewSet):

    queryset = Group.objects.all()
    serializer_class = GroupReadSerializer
    permission_classes = (AllowAny,)


class GroupSetReadViewSet(viewsets.ModelViewSet):

    queryset = GroupSet.objects.all()
    serializer_class = GroupSetReadSerializer
    permission_classes = (AllowAny,)


class IndividualSetReadViewSet(viewsets.ModelViewSet):

    queryset = IndividualSet.objects.all()
    serializer_class = IndividualSetReadSerializer
    permission_classes = (AllowAny,)

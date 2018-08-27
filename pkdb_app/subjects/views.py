from rest_framework.permissions import AllowAny
from rest_framework import viewsets
from pkdb_app.subjects.models import DataFile
from pkdb_app.subjects.serializers import DataFileSerializer


class DataFileViewSet(viewsets.ModelViewSet):

    queryset = DataFile.objects.all()
    serializer_class = DataFileSerializer
    permission_classes = (AllowAny,)

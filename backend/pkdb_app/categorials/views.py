from pkdb_app.categorials.models import MeasurementType
from pkdb_app.categorials.serializers import MeasurementTypeSerializer
from pkdb_app.users.permissions import IsAdminOrCreator
from rest_framework import viewsets


class MeasurementTypeViewSet(viewsets.ModelViewSet):
    queryset = MeasurementType.objects.all()
    serializer_class = MeasurementTypeSerializer
    permission_classes = (IsAdminOrCreator,)
    lookup_field = "url_slug"


# Create your views here.
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny

from pkdb_app.comments.models import Description
from pkdb_app.comments.serializers import DescriptionReadSerializer


class DescriptionReadViewSet(viewsets.ModelViewSet):

    queryset = Description.objects.all()
    serializer_class = DescriptionReadSerializer
    filter_backends = (filters.SearchFilter,)
    filter_fields = ('text',)
    search_fields = filter_fields
    permission_classes = (AllowAny,)
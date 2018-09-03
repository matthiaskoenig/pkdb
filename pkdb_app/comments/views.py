
# Create your views here.
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny

from pkdb_app.comments.models import Description, Comment
from pkdb_app.comments.serializers import DescriptionReadSerializer, CommentReadSerializer


class DescriptionReadViewSet(viewsets.ModelViewSet):

    queryset = Description.objects.all()
    serializer_class = DescriptionReadSerializer
    filter_backends = (filters.SearchFilter,)
    filter_fields = ("text",)
    search_fields = filter_fields
    permission_classes = (AllowAny,)

class CommentReadViewSet(viewsets.ModelViewSet):

    queryset = Comment.objects.all()
    serializer_class = CommentReadSerializer
    filter_backends = (filters.SearchFilter,)
    filter_fields = ("text",)
    search_fields = filter_fields
    permission_classes = (AllowAny,)

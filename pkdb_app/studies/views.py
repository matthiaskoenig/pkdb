from rest_framework.exceptions import ValidationError

from rest_framework.permissions import AllowAny, IsAdminUser
from pkdb_app.subjects.serializers import GroupSerializer
from .models import Author, Reference, Study
from .serializers import AuthorValidationSerializer, ReferenceSerializer, StudySerializer
from rest_framework import viewsets
import django_filters.rest_framework
from rest_framework import filters
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import  views


class AuthorsViewSet(viewsets.ModelViewSet):

    queryset = Author.objects.all()
    serializer_class = AuthorValidationSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
    filter_fields = ('first_name', 'last_name')
    search_fields = filter_fields
    permission_classes = (AllowAny,)


class ReferencesViewSet(viewsets.ModelViewSet):

    queryset = Reference.objects.all()
    parser_classes = (JSONParser,MultiPartParser, FormParser)
    serializer_class = ReferenceSerializer
    lookup_field = "sid"
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
    filter_fields = ('sid',)

    #filter_fields = ( 'pmid', 'doi','title', 'abstract', 'journal','date', 'authors')
    search_fields = filter_fields
    permission_classes = (AllowAny,)


class FileUploadView(views.APIView):
    def put(self, request, filename, format=None):
        file_obj = request.FILES['file']

        # do some stuff with uploaded file
        return Response(status=204)


class StudyViewSet(viewsets.ModelViewSet):
    queryset = Study.objects.all()
    serializer_class = StudySerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter,)
    filter_fields = ('sid',)
    search_fields = filter_fields
    permission_classes = (AllowAny,)

    @staticmethod
    def group_validation(request):
        if "groupset" in request.data:
            if request.data["groupset"]:
                groupset = request.data["groupset"]
                if "groups" in groupset:
                    groups = groupset.get("groups", [])
                    parents = set([group.get("parent") for group in groups if group.get("parent")] )
                    groups = set([group.get("name") for group in groups if group.get("name")])

                    # validate if groups are missing
                    missing_groups = parents - groups
                    if missing_groups:
                        if missing_groups is not None:
                            msg = {"groups": f"<{missing_groups}> have been used but not defined"}
                            raise ValidationError(msg)

    def partial_update(self, request, *args, **kwargs):
        self.group_validation(request)
        return super().partial_update(request, *args, **kwargs)


    def update(self, request, *args, **kwargs):
        self.group_validation(request)
        return super().update(request, *args, **kwargs)


    def create(self, request, *args, **kwargs):
        self.group_validation(request)
        return super().create(request, *args, **kwargs)

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAdminUser
from .models import Author, Reference, Study, Keyword
from .serializers import AuthorSerializer, ReferenceSerializer, StudySerializer, StudyReadSerializer, \
    ReferenceReadSerializer, AuthorReadSerializer, KeywordSerializer, KeywordReadSerializer
from rest_framework import viewsets
import django_filters.rest_framework
from rest_framework import filters
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

class KeywordViewSet(viewsets.ModelViewSet):
    queryset = Keyword.objects.all()
    serializer_class = KeywordSerializer
    permission_classes = (AllowAny,)

class AuthorsViewSet(viewsets.ModelViewSet):

    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
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

###############################################################################################
# Read ViewSets
###############################################################################################
class StudyReadViewSet(viewsets.ModelViewSet):
    queryset = Study.objects.all()
    serializer_class = StudyReadSerializer
    lookup_field = "sid"
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter,)
    filter_fields = ('sid',)
    search_fields = filter_fields
    permission_classes = (AllowAny,)

class ReferencesReadViewSet(viewsets.ModelViewSet):

    queryset = Reference.objects.all()
    serializer_class = ReferenceReadSerializer
    lookup_field = "sid"
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
    filter_fields = ( 'pmid', 'doi','title', 'abstract', 'journal','date', 'authors')
    search_fields = filter_fields
    permission_classes = (AllowAny,)

class AuthorsReadViewSet(viewsets.ModelViewSet):

    queryset = Author.objects.all()
    serializer_class = AuthorReadSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
    filter_fields = ('first_name', 'last_name')
    search_fields = filter_fields
    permission_classes = (AllowAny,)

class KeywordReadViewSet(viewsets.ModelViewSet):
    queryset = Keyword.objects.all()
    serializer_class = KeywordReadSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter,)
    filter_fields = ('name',)
    search_fields = filter_fields
    permission_classes = (AllowAny,)
from .models import Author, Reference, Study
from .serializers import AuthorSerializer, ReferenceSerializer, StudySerializer
from rest_framework import viewsets, generics
import django_filters.rest_framework
from rest_framework import filters
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status, views

class AuthorsViewSet(viewsets.ModelViewSet):

    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
    filter_fields = ('first_name', 'last_name')
    search_fields = filter_fields


class ReferencesViewSet(viewsets.ModelViewSet):

    queryset = Reference.objects.all()
    parser_classes = (JSONParser,MultiPartParser, FormParser)
    serializer_class = ReferenceSerializer
    lookup_field = "sid"
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
    filter_fields = ('sid',)

    #filter_fields = ( 'pmid', 'doi','title', 'abstract', 'journal','date', 'authors')
    search_fields = filter_fields


class FileUploadView(views.APIView):
    def put(self, request, filename, format=None):
        file_obj = request.FILES['file']

        # do some stuff with uploaded file
        return Response(status=204)

    """
        def post(self, request, *args, **kwargs):
        file_serializer = ReferenceSerializer(data=request.data)
        if file_serializer.is_valid():
            file_serializer.save()
            return Response(file_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    """




class StudyViewSet(viewsets.ModelViewSet):
    queryset = Study.objects.all()
    serializer_class = StudySerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter,)
    filter_fields = ('sid',)
    search_fields = filter_fields




#class InterventionsViewSet(viewsets.ModelViewSet):

#    queryset = Intervention.objects.all()
#    serializer_class = InterventionSerializer
#    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
#    filter_fields = ('comment','description','type')
 #   search_fields = filter_fields


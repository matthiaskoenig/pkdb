from rest_framework.exceptions import ValidationError

from pkdb_app.subjects.serializers import GroupSerializer
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


    @staticmethod
    def group_validation(request):
        if "groupset" in request.data:
            groupset = request.data["groupset"]
            groups = groupset.get("groups", [])
            parents = set([group.get("parent") for group in groups])
            groups = set([group.get("name") for group in groups])
            missing_groups = parents - groups
            if missing_groups:
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

    '''
        study_request = request.copy()
        study_data = study_request.data
        basic_keys = ["sid","name","pkdb_version","design","substances","reference","curators","files"]
        study_core_data = [study_data.pop(basic_keys) for key in basic_keys]
        request.data = study_core_data
        response = super().create(request, *args, **kwargs)
        
        if "groupset" in study_data:
            groupset = study_data["groupset"]
            groups = groupset.get("groups", [])
            for group in groups:
                serializer = GroupSerializer(data=group,)
            
        if "individualset" in study_data:
            indivdualset = study_data["individualset"]
            individuals = indivdualset.get("individuals", [])
            #upload individuals
            
        if "interventionset" in study_data:
            interventionset = study_data["interventionset"]
            interventions = interventionset.get("interventions", [])
            #upload interventions


        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    '''





#class InterventionsViewSet(viewsets.ModelViewSet):

#    queryset = Intervention.objects.all()
#    serializer_class = InterventionSerializer
#    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
#    filter_fields = ('comment','description','type')
 #   search_fields = filter_fields


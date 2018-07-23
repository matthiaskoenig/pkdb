from .models import Author, Reference, Study
from .serializers import AuthorSerializer, ReferenceSerializer, StudySerializer
from rest_framework import viewsets
import django_filters.rest_framework
from rest_framework import filters


class AuthorsViewSet(viewsets.ModelViewSet):

    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
    filter_fields = ('first_name', 'last_name')
    search_fields = filter_fields


class ReferencesViewSet(viewsets.ModelViewSet):

    queryset = Reference.objects.all()
    serializer_class = ReferenceSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
    filter_fields = ('sid',)

    #filter_fields = ( 'pmid', 'doi','title', 'abstract', 'journal','date', 'authors')
    search_fields = filter_fields


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


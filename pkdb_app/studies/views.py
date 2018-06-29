from .models import Author,Study,Intervention
from .serializers import AuthorSerializer,InterventionSerializer,StudySerializer
from rest_framework import viewsets
import django_filters.rest_framework
from rest_framework import filters


# Create your views here.
class AuthorsViewSet(viewsets.ModelViewSet):

    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
    filter_fields = ('first_name', 'last_name')
    search_fields = filter_fields


class StudiesViewSet(viewsets.ModelViewSet):

    queryset = Study.objects.all()
    serializer_class = StudySerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
    filter_fields = ( 'comment','description','title','pmid')
    search_fields = filter_fields


class InterventionsViewSet(viewsets.ModelViewSet):

    queryset = Intervention.objects.all()
    serializer_class = InterventionSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
    filter_fields = ('comment','description','type')
    search_fields = filter_fields


from .models import Author,Study,Intervention
from .serializers import AuthorSerializer,InterventionSerializer,StudySerializer
from rest_framework import viewsets

# Create your views here.
class AuthorsViewSet(viewsets.ModelViewSet):

    queryset = Author.objects.all()
    serializer_class = AuthorSerializer


class StudiesViewSet(viewsets.ModelViewSet):

    queryset = Study.objects.all()
    serializer_class = StudySerializer


class InterventionsViewSet(viewsets.ModelViewSet):

    queryset = Intervention.objects.all()
    serializer_class = InterventionSerializer



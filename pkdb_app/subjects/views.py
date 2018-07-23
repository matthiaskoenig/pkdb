from .models import Group, CharacteristicValue
from .serializers import GroupSerializer, CharacteristicValueSerializer
from rest_framework import viewsets
import django_filters.rest_framework
from rest_framework import filters


class GroupsViewSet(viewsets.ModelViewSet):

    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
    filter_fields = ('description',)
    search_fields = filter_fields


class CharacteristicValuesViewSet(viewsets.ModelViewSet):

    queryset = CharacteristicValue.objects.all()
    serializer_class = CharacteristicValueSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
    filter_fields = ( 'choice', 'count','category')
    search_fields = filter_fields



#class InterventionsViewSet(viewsets.ModelViewSet):

#    queryset = Intervention.objects.all()
#    serializer_class = InterventionSerializer
#    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter,)
#    filter_fields = ('comment','description','type')
 #   search_fields = filter_fields


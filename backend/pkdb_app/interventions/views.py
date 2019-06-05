from django.urls import reverse
from django_elasticsearch_dsl_drf.filter_backends import FilteringFilterBackend, CompoundSearchFilterBackend, \
    OrderingFilterBackend, IdsFilterBackend
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from pkdb_app.categorials.models import MeasurementType
from pkdb_app.interventions.models import INTERVENTION_ROUTE, INTERVENTION_FORM, INTERVENTION_APPLICATION
from rest_framework import viewsets
from rest_framework.response import Response

from ..interventions.documents import InterventionDocument

from ..interventions.serializers import InterventionElasticSerializer

from ..pagination import CustomPagination



###############################################################################################
# Option Views
###############################################################################################


class InterventionOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
        options = {}
        options["measurement_type"] = {k.name: k._asdict() for k in MeasurementType.objects.all()}
        options["substances"] = reverse('substances_elastic-list')
        options["route"] = INTERVENTION_ROUTE
        options["form"] = INTERVENTION_FORM
        options["application"] = INTERVENTION_APPLICATION
        return options

    def list(self, request):
        return Response(self.get_options())


###############################################################################################
# Elastic Views
###############################################################################################



class ElasticInterventionViewSet(DocumentViewSet):
    document = InterventionDocument
    serializer_class = InterventionElasticSerializer
    pagination_class = CustomPagination
    lookup_field = "id"
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,CompoundSearchFilterBackend]
    search_fields = ('name','measurement_type','substance.name',"form","application",'route','time_unit','normed')
    filter_fields = {'name': 'name.raw','pk':'pk','normed':'normed',}
    ordering_fields = {'name': 'name.raw',
                       'measurement_type':'measurement_type.raw',
                       'choice':'choice.raw',
                       'normed':'normed',
                       'application':'application.raw',
                       'substance':'substance.name',
                       'value':'value'}

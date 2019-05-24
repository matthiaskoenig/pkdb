from pkdb_app.categorials.models import MeasurementType
from pkdb_app.users.permissions import StudyPermission
from rest_framework import viewsets
from rest_framework.response import Response

from pkdb_app.pagination import CustomPagination
from pkdb_app.subjects.models import (
    DataFile,
)
from pkdb_app.subjects.serializers import (
    DataFileSerializer,
    IndividualElasticSerializer, GroupElasticSerializer, CharacteristicaReadSerializer)

from pkdb_app.subjects.documents import IndividualDocument, CharacteristicaDocument, GroupDocument
############################################################
#Elastic Search Views
###########################################################
from django_elasticsearch_dsl_drf.filter_backends import (
    FilteringFilterBackend,
    OrderingFilterBackend,
    CompoundSearchFilterBackend,
    IdsFilterBackend, )

from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet



class GroupViewSet(DocumentViewSet):
    document = GroupDocument
    serializer_class = GroupElasticSerializer
    lookup_field = 'id'
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,CompoundSearchFilterBackend]
    pagination_class = CustomPagination


    # Define search fields
    search_fields = (
        'name',
        'study.name',
        'parent.name',
        'characteristica_all_normed.measurement_type',
        'characteristica_all_normed.choice',
        'characteristica_all_normed.ctype',

    )

    # Filter fields
    filter_fields = {
        'id': 'id',
        'name': 'name.raw',
        'parent': 'group.name.raw',
        'study': 'study.name.raw',
        'ctype':'ctype.raw'

    }

    # Define ordering fields
    ordering_fields = {
        'id':'id',
        'study': 'study.raw',
        #'group': 'group.raw',
        'name': 'name.raw',
    }


class IndividualViewSet(DocumentViewSet):

    document = IndividualDocument
    serializer_class = IndividualElasticSerializer
    lookup_field = 'id'
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,CompoundSearchFilterBackend]
    pagination_class = CustomPagination


    # Define search fields
    search_fields = (
        'name',
        'study.name',
        'group.name',
        'characteristica_all_normed.measurement_type.name',
        'characteristica_all_normed.choice',

    )

    # Filter fields
    filter_fields = {
        'id': 'id',
        'name': 'name.raw',
        'group': 'group.name.raw',
        'study': 'study.name.raw',
    }

    # Define ordering fields
    ordering_fields = {
        'id':'id',
        'study': 'study.raw',
        'group': 'group.raw',
        'name': 'name.raw',
    }


class CharacteristicaViewSet(DocumentViewSet):
    pagination_class = CustomPagination
    document = CharacteristicaDocument
    serializer_class = CharacteristicaReadSerializer
    lookup_field = 'id'
    filter_backends = [FilteringFilterBackend,IdsFilterBackend,OrderingFilterBackend,CompoundSearchFilterBackend]

    search_fields = (
        'choice',
        'group_name',
    )
    ordering_fields = {
        'choice': 'choice.raw',
        "count": 'count',
    }

    filter_fields = {
        'all_group_pks': {
            'field': 'all_group_pks',
        },
        'id': 'id',
        'value': 'value',
        'mean': 'mean',
        'median': 'median',
        'min': 'min',
        'max':'max',
        'se':  'se',
        'sd':  'sd',
        'cv':'cv',
        'normed':'normed',
        'group_name': 'group_name.raw',
        'group_pk': 'group_pk',
        'individual_name': 'individual_name.raw',
        'individual_pk': 'individual_pk',
    }

############################################################
#Views queried not from elastic search
###########################################################
class DataFileViewSet(viewsets.ModelViewSet):

    queryset = DataFile.objects.all()
    serializer_class = DataFileSerializer
    permission_classes = (StudyPermission,)


    def create(self, request, *args, **kwargs):

        try:
            DataFile.objects.filter(file=f"data/{request.data['file'].name}").delete()

        #same_files = DataFile.objects.filter(file = request.data["file"].name)
        except DataFile.DoesNotExist:
            pass

        return super().create(request, *args, **kwargs)





class CharacteristicaOptionViewSet(viewsets.ViewSet):

    @staticmethod
    def get_options():
        options = {}
        options["measurement_types"] = {k.key: k._asdict() for k in MeasurementType.objects.all()}
        return options

    def list(self, request):
        return Response(self.get_options())



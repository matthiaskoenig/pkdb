from rest_framework import serializers

from pkdb_app.interventions.models import Substance
from ..serializers import BaseSerializer

'''
class MedicationStepSerializer(BaseSerializer):
    class Meta:
        model = MedicationStep
        fields = "__all__"


class ProtocolSerializer(BaseSerializer):
    protokol_steps = MedicationStepSerializer(many=True, read_only=False)

    class Meta:
        model = Protocol
        fields = "__all__"


'''


class SubstanceSerializer(serializers.Serializer):

    class Meta:
        model = Substance
        fields = ["name"]






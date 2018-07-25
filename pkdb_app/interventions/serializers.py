from rest_framework import serializers
from .models import Protocol,  MedicationStep
from ..serializers import BaseSerializer


class MedicationStepSerializer(BaseSerializer):
    class Meta:
        model = MedicationStep
        fields = "__all__"


class ProtocolSerializer(BaseSerializer):
    protokol_steps = MedicationStepSerializer(many=True, read_only=False)

    class Meta:
        model = Protocol
        fields = "__all__"


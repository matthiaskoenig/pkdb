"""
Serializers for interventions.
"""



# ----------------------------------
# Interventions
# ----------------------------------
from pkdb_app.categorials.models import Unit, Choice, CharacteristicType, InterventionType, PharmacokineticType
from rest_framework import serializers


class UnitSerializer(serializers.ModelSerializer):

    class Meta:
        model = Unit
        fields = ["name"]

class ChoiceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Choice
        fields = ["name"]


class CharacteristicTypeSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True)
    units = UnitSerializer(many=True)


    class Meta:
        model = CharacteristicType
        fields = ["key","units","category","dtype","choices"]


class InterventionTypeSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True)
    units = UnitSerializer(many=True)

    class Meta:
        model = InterventionType
        fields = ["key","units","category","dtype","choices"]


class PharmacokineticTypeSerializer(serializers.ModelSerializer):
    units = UnitSerializer(many=True)

    class Meta:
        model = PharmacokineticType
        fields = ["key","units","category","description"]


###############################################################################################
# Elastic Serializer
###############################################################################################




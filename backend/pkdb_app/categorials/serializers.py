"""
Serializers for interventions.
"""



# ----------------------------------
# Interventions
# ----------------------------------
from pkdb_app.categorials.models import Unit, Choice, CharacteristicType, InterventionType, PharmacokineticType
from pkdb_app.utils import update_or_create_multiple
from rest_framework import serializers


class UnitSerializer(serializers.ModelSerializer):

    class Meta:
        model = Unit
        fields = ["name"]
    def to_representation(self, instance):
        return instance.name

class ChoiceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Choice
        fields = ["name"]

    def to_representation(self, instance):
        return instance.name

class BaseSerializer(serializers.ModelSerializer):

    def to_internal_value(self, data):
        data["units"] = [{"name":unit} for unit in data.get("units",[])]
        if data.get("choices"):
            data["choices"] = [{"name":choice} for choice in data.get("choices",[])]
        else:
            data["choices"] = []
        return super().to_internal_value(data)

    def create(self, validated_data):

        units_data = validated_data.pop("units", [])
        choices_data = validated_data.pop("choices", [])
        instance = self.Meta.model.objects.create(**validated_data)
        update_or_create_multiple(instance, units_data, "units")

        if choices_data:
            update_or_create_multiple(instance, choices_data, "choices")
            instance.save()

        instance.save()

        return instance

    def update(self, instance, validated_data):
        units_data = validated_data.pop("units", [])
        choices_data = validated_data.pop("choices", [])

        for name, value in validated_data.items():
            setattr(instance, name, value)

        instance.units.clear()
        if hasattr(instance,'choices'):
            instance.choices.clear()

        update_or_create_multiple(instance, units_data, "units")
        if choices_data:
            update_or_create_multiple(instance, choices_data, "choices")
            instance.save()

        instance.save()
        return instance



class CharacteristicTypeSerializer(BaseSerializer):
    choices = ChoiceSerializer(many=True)
    units = UnitSerializer(many=True)


    class Meta:
        model = CharacteristicType
        fields = ["key","units","category","dtype","choices","url_slug"]



class InterventionTypeSerializer(BaseSerializer):
    choices = ChoiceSerializer(many=True, allow_null=True)
    units = UnitSerializer(many=True)

    class Meta:
        model = InterventionType
        fields = ["key","units","category","dtype","choices","url_slug"]


class PharmacokineticTypeSerializer(BaseSerializer):
    units = UnitSerializer(many=True)

    class Meta:
        model = PharmacokineticType
        fields = ["key","units","description","url_slug"]





###############################################################################################
# Elastic Serializer
###############################################################################################




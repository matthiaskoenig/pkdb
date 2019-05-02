"""
Serializers for interventions.
"""



# ----------------------------------
# Interventions
# ----------------------------------
from pkdb_app.categorials.models import Unit, Choice, CharacteristicType, InterventionType, PharmacokineticType, Keyword
from pkdb_app.serializers import WrongKeyValidationSerializer
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


class BaseSerializer(WrongKeyValidationSerializer):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["creator"] = instance.creator.username
        return data

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        data["creator"] = self.context['request'].user.id
        data["units"] = [{"name":unit} for unit in data.get("units",[])]

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
        print(validated_data)
        units_data = validated_data.pop("units", [])
        choices_data = validated_data.pop("choices", [])


        for name, value in validated_data.items():
            setattr(instance, name, value)

        instance.units.clear()
        if hasattr(instance,'choices'):
            instance.choices.clear()

        update_or_create_multiple(instance, units_data, "units")

        if choices_data:
            print(choices_data)
            update_or_create_multiple(instance, choices_data, "choices")

        instance.save()
        return instance



class CharacteristicTypeSerializer(BaseSerializer):
    choices = ChoiceSerializer(many=True)
    units = UnitSerializer(many=True)

    class Meta:
        model = CharacteristicType
        fields = ["key","units","category","dtype","choices","url_slug","creator"]

    def to_internal_value(self, data):
        data["choices"] = data.get("choices", [])

        if data["choices"]:
            data["choices"] = [{"name": choice} for choice in data["choices"]]
        return super().to_internal_value(data)

class InterventionTypeSerializer(BaseSerializer):
    choices = ChoiceSerializer(many=True, allow_null=True)
    units = UnitSerializer(many=True)

    class Meta:
        model = InterventionType
        fields = ["key","units","category","dtype","choices","url_slug","creator"]

    def to_internal_value(self, data):
        data["choices"] = data.get("choices", [])

        if data["choices"]:
            data["choices"] = [{"name": choice} for choice in data["choices"]]
        return super().to_internal_value(data)


class PharmacokineticTypeSerializer(BaseSerializer):
    units = UnitSerializer(many=True)

    class Meta:
        model = PharmacokineticType
        fields = ["key","units","description","url_slug","creator"]





# ----------------------------------
# Keyword
# ----------------------------------


class KeywordSerializer(WrongKeyValidationSerializer):
    """ Keyword. """

    class Meta:
        model = Keyword
        fields = ["name","creator"]

    def create(self, validated_data):
        keyword, created = Keyword.objects.update_or_create(**validated_data)
        return keyword

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        data["creator"] = self.context['request'].user.id
        return super().to_internal_value(data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["creator"] = instance.creator.username
        return data


###############################################################################################
# Elastic Serializer
###############################################################################################


from rest_framework import serializers
from .models import Group, GroupSet,Individual,IndividualSet,Characteristica

from ..studies.models import Reference
from ..serializers import ParserSerializer

BASE_FIELDS = ()
from collections import OrderedDict



class CharacteristicaSerializer(serializers.ModelSerializer):

    count = serializers.IntegerField(required=False)

    class Meta:
        model = Characteristica
        fields = "__all__"

    def to_representation(self, instance):
        result = super().to_representation(instance)
        return OrderedDict([(key, result[key]) for key in result if result[key] is not None])


class GroupSerializer(ParserSerializer):
    characteristica = CharacteristicaSerializer(many=True,read_only=False, required=False)

    class Meta:
        model = Group
        fields = ["name","count","characteristica"]



    def to_internal_value(self, data):
        """

        :param data:
        :return:
        """
        data = self.generic_parser(data,"characteristica")
        return super(GroupSerializer, self).to_internal_value(data)


class GroupSetSerializer(ParserSerializer):
    characteristica = CharacteristicaSerializer(many=True,read_only=False, required=False)
    groups = GroupSerializer(many=True, read_only=False)

    class Meta:
        model = GroupSet
        fields = ["description","characteristica","groups"]

    def to_internal_value(self, data):
        """

        :param data:
        :return:
        """
        data = self.generic_parser(data,"characteristica")
        return super(GroupSetSerializer, self).to_internal_value(data)




'''
class CharacteristicValueSerializer(serializers.ModelSerializer):

    count = serializers.IntegerField(required=False)

    class Meta:
        model = Characteristica
        fields = "__all__"

    def to_representation(self, instance):
        result = super().to_representation(instance)
        return OrderedDict([(key, result[key]) for key in result if result[key] is not None])


class GroupSerializer(serializers.ModelSerializer):
    characteristic_values = CharacteristicValueSerializer(many=True, read_only=False)
    interventions = ProtocolSerializer(many=True, read_only=False)

    class Meta:
            model = Group
            fields = BASE_FIELDS + ( 'name', 'count','description','characteristic_values', 'intervention')


    def create(self, validated_data):
        group , _ = Group.objects.update_or_create(name=validated_data["name"], defaults=validated_data)
        return group

    def to_representation(self, instance):
        """
        this method reduces the serialized output to not non-values.
        :param instance:
        :return:
        """
        result = super().to_representation(instance)
        return OrderedDict([(key, result[key]) for key in result if result[key] is not None])


'''

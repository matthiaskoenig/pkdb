from rest_framework import serializers
from .models import Group, CharacteristicValue
from ..studies.models import Reference
from ..serializers import BaseSerializer
BASE_FIELDS = ()
from collections import OrderedDict


class CharacteristicValueSerializer(serializers.ModelSerializer):

    class Meta:
        model = CharacteristicValue
        fields = "__all__"

    def to_representation(self, instance):
        result = super().to_representation(instance)
        return OrderedDict([(key, result[key]) for key in result if result[key] is not None])


class GroupSerializer(serializers.ModelSerializer):
    characteristic_values = CharacteristicValueSerializer(many=True, read_only=False)

    class Meta:
            model = Group
            fields = BASE_FIELDS + ( 'characteristic_values', 'name', 'description', 'count',)

    def create(self, validated_data):
        group , _ = Group.objects.update_or_create(name=validated_data["name"], defaults=validated_data)
        return group

    def to_representation(self, instance):
        result = super().to_representation(instance)
        return OrderedDict([(key, result[key]) for key in result if result[key] is not None])


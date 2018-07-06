from rest_framework import serializers
from .models import Group, CharacteristicValue

BASE_FIELDS = ()


class CharacteristicValueSerializer(serializers.ModelSerializer):

    class Meta:
        model = CharacteristicValue
        fields = "__all__"


class GroupSerializer(serializers.ModelSerializer):
    characteristic_values = CharacteristicValueSerializer(many=True,read_only=False)

    class Meta:
            model = Group
            fields = BASE_FIELDS + ('reference','characteristic_values','sid','description','count',)

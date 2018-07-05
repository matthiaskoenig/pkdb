from rest_framework import serializers
from .models import Group

BASE_FIELDS = ()



class GroupSerializer(serializers.ModelSerializer):

    class Meta:
            model = Group
            fields = BASE_FIELDS + ('sid','description','count')
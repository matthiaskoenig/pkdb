from rest_framework import serializers

from pkdb_app.comments.models import Description


class DescriptionsSerializer(serializers.ModelSerializer):

    class Meta:
        fields = ["text"]
        model = Description

    def to_internal_value(self, data):
        return {"text": data}

    def to_representation(self, instance):
        return instance.text

from rest_framework import serializers

from pkdb_app.comments.models import Description, Comment
from pkdb_app.serializers import WrongKeyValidationSerializer
from pkdb_app.users.models import User


class DescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["text"]
        model = Description

    def to_internal_value(self, data):
        self._validate_description(data=data)
        return super().to_internal_value({"text": data})

    def to_representation(self, instance):
        return instance.text

    def _validate_description(self, data):
        if not (isinstance(data, str)):
            raise serializers.ValidationError(
                {
                    "descriptions": "Description must be a String",
                    "detail": {str(data)},
                }
            )
        elif len(data) == 0:
            raise serializers.ValidationError(
                {
                    "descriptions": "empty descriptions are not allowed",
                    "detail": {str(data)},
                })


class CommentSerializer(WrongKeyValidationSerializer):
    class Meta:
        fields = ["text", "user"]
        model = Comment

    def _validate_comment(self, data):

        if not (isinstance(data, list) and len(data) == 2):
            raise serializers.ValidationError(
                {
                    "comments": "comment must be a list of the form ['username', 'comment']",
                    "detail": {str(data)},
                }
            )
        elif len(data[1]) == 0:
            raise serializers.ValidationError(
                {
                    "comments": "empty comments are not allowed",
                    "detail": {str(data)},
                })


    def to_internal_value(self, data):
        self._validate_comment(data)
        user = self.get_or_val_error(User, username=data[0])

        return {"text": data[1], "user": user}


    def to_representation(self, instance):
        return [instance.user.username, instance.text]


###############################################################################################
# Read Serializer
###############################################################################################
class DescriptionElasticSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["pk", "text"]
        model = Description


class CommentElasticSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["pk", "username", "text", ]
        model = Comment

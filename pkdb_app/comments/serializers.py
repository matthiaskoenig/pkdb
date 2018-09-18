from rest_framework import serializers

from pkdb_app.comments.models import Description, Comment
from pkdb_app.serializers import WrongKeyValidationSerializer
from pkdb_app.users.models import User


class DescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["text"]
        model = Description

    def to_internal_value(self, data):
        return super().to_internal_value({"text": data})

    def to_representation(self, instance):
        return instance.text


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

    def to_internal_value(self, data):
        self._validate_comment(data)
        user = self.get_or_val_error(User, username=data[0])
        return {"text": data[1], "user": user}

    def to_representation(self, instance):
        return [instance.user.username, instance.text]


###############################################################################################
# Read Serializer
###############################################################################################
class DescriptionReadSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        fields = ["pk", "text"]
        model = Description


class CommentReadSerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="users_read-detail"
    )
    class Meta:
        fields = ["pk", "text","user"]
        model = Comment
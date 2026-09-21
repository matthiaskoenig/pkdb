"""Upload and elasticsearch serializers for comments and descriptions."""

from rest_framework import serializers

from pkdb_app.comments.models import Comment, Description
from pkdb_app.serializers import WrongKeyValidationSerializer
from pkdb_app.users.models import User


class DescriptionSerializer(serializers.ModelSerializer):
    """Upload serializer that reads and writes a description as a plain string."""

    class Meta:
        fields = ["text"]
        model = Description

    def to_internal_value(self, data):
        """Validate the raw string and wrap it as the ``text`` field value."""
        self._validate_description(data=data)
        return super().to_internal_value({"text": data})

    def to_representation(self, instance):
        """Represent the description as its plain text, not as an object."""
        return instance.text

    def _validate_description(self, data):
        """Raise a validation error unless data is a non-empty string."""
        if not (isinstance(data, str)):
            raise serializers.ValidationError(
                {  # ty: ignore[invalid-argument-type]  # DRF renders any detail value with force_str, the stub type is narrower
                    "descriptions": "Description must be a String",
                    "detail": {str(data)},
                }
            )
        if len(data) == 0:
            raise serializers.ValidationError(
                {  # ty: ignore[invalid-argument-type]  # DRF renders any detail value with force_str, the stub type is narrower
                    "descriptions": "empty descriptions are not allowed",
                    "detail": {str(data)},
                }
            )


class CommentSerializer(WrongKeyValidationSerializer):
    """Upload serializer for a comment.

    A comment is read and written as a ``[username, text]`` pair.
    """

    class Meta:
        fields = ["text", "user"]
        model = Comment

    def _validate_comment(self, data):
        """Raise a validation error for data which is no comment.

        A comment is a two element list with non-empty text.
        """
        if not (isinstance(data, list) and len(data) == 2):
            raise serializers.ValidationError(
                {  # ty: ignore[invalid-argument-type]  # DRF renders any detail value with force_str, the stub type is narrower
                    "comments": "comment must be a list of the form ['username', 'comment']",
                    "detail": {str(data)},
                }
            )
        if len(data[1]) == 0:
            raise serializers.ValidationError(
                {  # ty: ignore[invalid-argument-type]  # DRF renders any detail value with force_str, the stub type is narrower
                    "comments": "empty comments are not allowed",
                    "detail": {str(data)},
                }
            )

    def to_internal_value(self, data):
        """Resolve the user by username and pair it with the comment text."""
        self._validate_comment(data)
        user = self.get_or_val_error(User, username=data[0])

        return {"text": data[1], "user": user}

    def to_representation(self, instance):
        """Represent the comment as a ``[username, text]`` pair."""
        return [instance.user.username, instance.text]


###############################################################################################
# Read Serializer
###############################################################################################
class DescriptionElasticSerializer(serializers.ModelSerializer):
    """Elasticsearch read serializer exposing a description's primary key and text."""

    class Meta:
        fields = ["pk", "text"]
        model = Description


class CommentElasticSerializer(serializers.ModelSerializer):
    """Elasticsearch read serializer exposing a comment's author name and text."""

    class Meta:
        fields = [
            "pk",
            "username",
            "text",
        ]
        model = Comment

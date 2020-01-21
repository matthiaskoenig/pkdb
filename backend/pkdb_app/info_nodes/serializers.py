from rest_framework import serializers

from pkdb_app import utils
from pkdb_app.info_nodes.models import InfoNode, Synonym, Annotation
from pkdb_app.serializers import WrongKeyValidationSerializer

class SynonymSerializer(WrongKeyValidationSerializer):
    class Meta:
        model = Synonym
        fields = ["name"]

    def to_internal_value(self, data):
        return {"name": data}

    def to_representation(self, instance):
        return instance.name

class AnnotationSerializer(serializers.ModelSerializer):
    term = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    label = serializers.CharField(allow_null=True)

    class Meta:
        model = Annotation
        fields = ["term", "relation", "collection", "description", "label"]


class InfoNodeSerializer(serializers.Serializer):
    """ Substance. """
    parents = utils.SlugRelatedField(many=True, slug_field="name", queryset=InfoNode.objects.order_by('name'),
                                     required=False, allow_null=True)
    synonyms = SynonymSerializer(many=True, read_only=False, required=False, allow_null=True)
    annotations = AnnotationSerializer(many=True, read_only=False, required=False, allow_null=True)

    class Meta:
        model = InfoNode
        fields = ["sid", "url_slug", "name", "parents", "chebi", "formula", "charge", "mass", "description", "synonyms",
                  "creator", "annotations"]

    def to_internal_value(self, data):
        data["creator"] = self.context['request'].user.id
        return super().to_internal_value(data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["creator"] = instance.creator.username
        return data

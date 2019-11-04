"""
Serializers for substances.
"""
from pkdb_app import utils
from pkdb_app.categorials.serializers import AnnotationSerializer, SynonymSerializer
from rest_framework import serializers

from pkdb_app.substances.models import Substance
from pkdb_app.serializers import WrongKeyValidationSerializer

# ----------------------------------
from ..utils import update_or_create_multiple


# ----------------------------------
# Substance
# ----------------------------------



class SubstanceSerializer(WrongKeyValidationSerializer):
    """ Substance. """
    parents = utils.SlugRelatedField(many=True, slug_field="name", queryset=Substance.objects.order_by('name'),
                                     required=False, allow_null=True)
    synonyms = SynonymSerializer(many=True, read_only=False, required=False, allow_null=True)
    annotations = AnnotationSerializer(many=True, read_only=False, required=False, allow_null=True)

    class Meta:
        model = Substance
        fields = ["sid", "url_slug", "name", "parents", "chebi", "formula", "charge", "mass", "description", "synonyms",
                  "creator", "annotations"]

    def to_internal_value(self, data):
        data["creator"] = self.context['request'].user.id
        return super().to_internal_value(data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["creator"] = instance.creator.username
        return data

    def create(self, validated_data):
        synonyms_data = validated_data.pop("synonyms", [])
        parents_data = validated_data.pop("parents", [])
        annotations_data = validated_data.pop("annotations", [])

        substance = Substance.objects.create(**validated_data)
        update_or_create_multiple(substance, synonyms_data, "synonyms", lookup_fields=["name"])
        update_or_create_multiple(substance, annotations_data, "annotations", lookup_fields=["term", "relation"])

        substance.parents.add(*parents_data)

        substance.save()
        return substance

    def update(self, instance, validated_data):
        synonyms_data = validated_data.pop("synonyms", [])
        parents_data = validated_data.pop("parents", [])
        annotations_data = validated_data.pop("annotations", [])

        instance.parents.clear()
        instance.synonyms.all().delete()
        instance.annotations.clear()

        for name, value in validated_data.items():
            setattr(instance, name, value)
        update_or_create_multiple(instance, synonyms_data, "synonyms", lookup_fields=["name"])
        update_or_create_multiple(instance, annotations_data, "annotations", lookup_fields=["term"])

        instance.parents.add(*parents_data)
        instance.save()

        return instance


class SubstanceStatisticsSerializer(serializers.ModelSerializer):
    """ Substance. """
    # studies = serializers.StringRelatedField(many=True, read_only=True)
    interventions = serializers.PrimaryKeyRelatedField(many=True, source="interventions_normed", read_only=True)
    outputs = serializers.PrimaryKeyRelatedField(many=True, source="outputs_normed", read_only=True)
    outputs_calculated = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    timecourses = serializers.PrimaryKeyRelatedField(many=True, source="timecourses_normed", read_only=True)

    class Meta:
        model = Substance
        fields = ["name", "outputs", "outputs_calculated", "interventions", "timecourses"]


###############################################################################################
# Elastic Serializer
###############################################################################################

class SubstanceSmallElasticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Substance
        fields = ["sid", 'url_slug']


class SubstanceElasticSerializer(serializers.HyperlinkedModelSerializer):
    parents = SubstanceSmallElasticSerializer(many=True)
    annotations = AnnotationSerializer(many=True, allow_null=True)
    synonyms = SynonymSerializer(many=True, read_only=True, required=False, allow_null=True)

    class Meta:
        model = Substance
        fields = ["sid", 'url_slug', "name", "mass", "charge", "formula", "derived", "description", "parents", "annotations", "synonyms"]


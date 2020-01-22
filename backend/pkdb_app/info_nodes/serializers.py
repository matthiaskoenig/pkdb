from rest_framework import serializers

from pkdb_app import utils
from pkdb_app.info_nodes.models import InfoNode, Synonym, Annotation, Unit, MeasurementType, Substance
from pkdb_app.serializers import WrongKeyValidationSerializer, ExSerializer


class EXMeasurementTypeableSerializer(ExSerializer):
    measurement_type = serializers.CharField(allow_blank=False)
    measurement_type_map = serializers.CharField(allow_blank=False)


class MeasurementTypeableSerializer(EXMeasurementTypeableSerializer):
    substance = utils.SlugRelatedField(
        slug_field="name",
        queryset=Substance.objects.all(),
        read_only=False,
        required=False,
        allow_null=True,
    )

    measurement_type = utils.SlugRelatedField(
        slug_field="name",
        queryset=MeasurementType.objects.all())

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        return rep


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
        fields = ["sid", "url_slug", "name", "parents", "description", "ntype","synonyms","creator", "annotations"]

    def to_internal_value(self, data):
        data["creator"] = self.context['request'].user.id
        return super().to_internal_value(data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["creator"] = instance.creator.username
        return data


class InfoNodeMainSerializer(serializers.ModelSerializer):
    info_node = InfoNodeSerializer(read_only=True)
    class Meta:
        model = None  # is set in the get_serializer_class function in the view




class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ["name"]

    def to_representation(self, instance):
        return instance.name


class MeasurementTypeSerializer(InfoNodeMainSerializer):
    units = UnitSerializer(many=True, allow_null=True)

    class Meta:
        model = None  # is set in the get_serializer_class function in the view

###############################################################################################
# Elastic Serializer
###############################################################################################

class SmallInfoNodeElasticSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfoNode
        fields = ["sid", 'url_slug']


class SubstanceExtraSerializer(serializers.ModelSerializer):
        model = Substance
        fields = [ "mass", "charge", "formula", "derived"]


class MeasurementTypeExtraSerializer(serializers.ModelSerializer):
    model = MeasurementTypeSerializer
    fields = ["units", "dtype", "choices"]


class InfoNodeElasticSerializer(serializers.ModelSerializer):
    parents = SmallInfoNodeElasticSerializer(many=True)
    annotations = AnnotationSerializer(many=True, allow_null=True)
    synonyms = SynonymSerializer(many=True, read_only=True, required=False, allow_null=True)
    substance = SubstanceExtraSerializer(required=False, allow_null=True)
    measurement_type = MeasurementTypeExtraSerializer(required=False, allow_null=True)

    class Meta:
        model = InfoNode
        fields = ["sid", "name", 'url_slug', "description", "parents", "annotations", "synonyms", "substance","measurement_type"]
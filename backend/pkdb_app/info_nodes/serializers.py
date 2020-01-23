from rest_framework import serializers

from pkdb_app import utils
from django.apps import apps
from pkdb_app.info_nodes.models import InfoNode, Synonym, Annotation, Unit, MeasurementType, Substance
from pkdb_app.serializers import WrongKeyValidationSerializer, ExSerializer
from pkdb_app.utils import update_or_create_multiple


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


class InfoNodeSerializer(serializers.ModelSerializer):
    """ Substance. """
    parents = utils.SlugRelatedField(many=True, slug_field="sid", queryset=InfoNode.objects.order_by('sid'),
                                     required=False, allow_null=True)
    synonyms = SynonymSerializer(many=True, read_only=False, required=False, allow_null=True)
    annotations = AnnotationSerializer(many=True, read_only=False, required=False, allow_null=True)

    class Meta:
        model = InfoNode
        fields = ["sid", "url_slug", "name", "parents", "description", "ntype","synonyms","creator", "annotations"]

    def create(self, validated_data):
        synonyms_data = validated_data.pop("synonyms", [])
        parents_data = validated_data.pop("parents", [])
        annotations_data = validated_data.pop("annotations", [])

        ntype = validated_data.get('ntype')
        extra_fields = validated_data.get(ntype, {})

        NOTE_TYPES = {
            "info_node":"InfoNode",
            "measurement_type": "MeasurementType",
            "substance": "Substance",
            "route": "Route",
            "form": "Form",
            "application": "Application",
            "tissue": "Tissue",
            "choice": "Choice",
        }

        Model = apps.get_model('info_nodes', NOTE_TYPES[ntype])
        instance = InfoNode.objects.create(**validated_data)
        update_or_create_multiple(instance, annotations_data, 'annotations', lookup_fields=["term", "relation"])
        update_or_create_multiple(instance, synonyms_data, 'synonyms', lookup_fields=["name"])
        instance.parents.add(*parents_data)
        instance.save()

        if Model != InfoNode:
            if Model == MeasurementType:
                units = extra_fields.pop('units', [])
                specific_instance = Model.objects.create(info_node=instance, **extra_fields)
                update_or_create_multiple(specific_instance, units, 'units', lookup_fields=["name"])
            else:
                specific_instance = Model.objects.create(info_node=instance, **extra_fields)

            specific_instance.save()

        return instance



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
from rest_framework import serializers

from pkdb_app import utils
from django.apps import apps

from pkdb_app.info_nodes.documents import InfoNodeDocument
from pkdb_app.info_nodes.models import InfoNode, Synonym, Annotation, Unit, MeasurementType, Substance, Choice, Route, \
    Form, Tissue, Application
from pkdb_app.serializers import WrongKeyValidationSerializer, ExSerializer
from pkdb_app.utils import update_or_create_multiple


class EXMeasurementTypeableSerializer(ExSerializer):
    measurement_type = serializers.CharField(allow_blank=False)
    measurement_type_map = serializers.CharField(allow_blank=False)


class MeasurementTypeableSerializer(EXMeasurementTypeableSerializer):
    substance = utils.SlugRelatedField(
        slug_field="name",
        queryset=InfoNode.objects.filter(ntype=InfoNode.NTypes.Substance),
        read_only=False,
        required=False,
        allow_null=True,
    )

    measurement_type = utils.SlugRelatedField(
        slug_field="name",
        queryset=InfoNode.objects.filter(ntype=InfoNode.NTypes.MeasurementType)
    )

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


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ["name"]

    def to_internal_value(self, data):
        return {"name": data}

    def to_representation(self, instance):
        return instance.name

class SubstanceExtraSerializer(serializers.ModelSerializer):
    derived = serializers.BooleanField(read_only=True)
    class Meta:
        model = Substance
        fields = ["mass", "charge", "formula", "derived"]


class MeasurementTypeExtraSerializer(serializers.ModelSerializer):
    units = UnitSerializer(many=True, allow_null=True, required=False)
    choices = serializers.SlugRelatedField("sid", many=True, queryset=InfoNode.objects.filter(ntype=InfoNode.NTypes.Choice), required=False, allow_null=True)
    class Meta:
        model = MeasurementType
        fields = ["units", "choices"]



class InfoNodeSerializer(serializers.ModelSerializer):
    """ Substance. """
    parents = utils.SlugRelatedField(many=True, slug_field="sid", queryset=InfoNode.objects.all(),
                                     required=False, allow_null=True)
    synonyms = SynonymSerializer(many=True, read_only=False, required=False, allow_null=True)
    annotations = AnnotationSerializer(many=True, read_only=False, required=False, allow_null=True)
    measurement_type = MeasurementTypeExtraSerializer(allow_null=True, required=False)
    substance = SubstanceExtraSerializer(allow_null=True, required=False)

    class Meta:
        model = InfoNode
        fields = ["sid", "url_slug", "name", "ntype", "dtype", "parents", "description","synonyms","creator", "annotations", "measurement_type", "substance"]


    @staticmethod
    def related_sets():
        return {
            "info_node":InfoNode,
            "measurement_type": MeasurementType,
            "substance": Substance,
            "route": Route,
            "form": Form,
            "application": Application,
            "tissue": Tissue,
            "choice": Choice,
        }
    @staticmethod
    def related_many_create():
        return {
            "annotations": Annotation,
            "synonyms": Synonym,
        }
    @staticmethod
    def related_many_add():
        return {
            "annotations": Annotation,
            "synonyms": Synonym
        }

    def pop(self, data):
        pop_data = {"add":{},"create":[]}
        for key in self.related_many_add():
            pop_data["add"][key] = data.pop(key, [])

        for key in self.related_many_create():
            pop_data["create"][key] = data.pop(key, [])
        return pop_data


    def update(self, instance, validated_data):
        instance.delete()
        return self.create(validated_data)




    def create(self, validated_data):
        synonyms_data = validated_data.pop("synonyms", [])
        parents_data = validated_data.pop("parents", [])
        annotations_data = validated_data.pop("annotations", [])

        ntype = validated_data.get('ntype')
        extra_fields = validated_data.pop(ntype, {})

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
        if validated_data["name"] == "sex":

            print("I am here")

        Model = apps.get_model('info_nodes', NOTE_TYPES[ntype])
        instance = InfoNode.objects.create(**validated_data)

        update_or_create_multiple(instance, annotations_data, 'annotations', lookup_fields=["term", "relation"])
        update_or_create_multiple(instance, synonyms_data, 'synonyms', lookup_fields=["name"])
        instance.parents.add(*parents_data)
        instance.save()

        if Model != InfoNode:
            if Model == MeasurementType:
                units = extra_fields.pop('units', [])
                choices = extra_fields.pop('choices', [])

                specific_instance = Model.objects.create(info_node=instance, **extra_fields)
                specific_instance.choices.add(*[info_node.choice for info_node in choices])

                update_or_create_multiple(specific_instance, units, 'units', lookup_fields=["name"])


            else:
                specific_instance = Model.objects.create(info_node=instance, **extra_fields)

            specific_instance.save()

        InfoNodeDocument().update(instance)

        return instance



    def to_internal_value(self, data):
        data["creator"] = self.context['request'].user.id
        return super().to_internal_value(data)

    def to_representation(self, instance):

        data = super().to_representation(instance)
        data["creator"] = instance.creator.username
        return data


###############################################################################################
# Elastic Serializer
###############################################################################################

class SmallInfoNodeElasticSerializer(serializers.ModelSerializer):
    annotations = AnnotationSerializer(many=True, allow_null=True)
    class Meta:
        model = InfoNode
        fields = ["sid", "name", "description", "annotations"]


class InfoNodeElasticSerializer(serializers.ModelSerializer):
    parents = SmallInfoNodeElasticSerializer(many=True)
    annotations = AnnotationSerializer(many=True, allow_null=True)
    synonyms = serializers.SerializerMethodField()
    substance = SubstanceExtraSerializer(required=False, allow_null=True)
    measurement_type = MeasurementTypeExtraSerializer(required=False, allow_null=True)

    class Meta:
        model = InfoNode
        fields = ["sid", "name", 'url_slug', "ntype", "dtype", "description","synonyms", "parents", "annotations", "measurement_type", "substance"]
    @staticmethod
    def get_synonyms(obj):
        """Get synonyms."""
        if obj.synonyms:
            return list(obj.synonyms)
        else:
            return []
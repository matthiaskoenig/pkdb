"""
Serializers for interventions.
"""

# ----------------------------------
# Interventions
# ----------------------------------
from pkdb_app import utils
from pkdb_app.categorials.models import Unit, Choice, MeasurementType, Annotation, Tissue, Form, Application, Route, \
    Synonym
from pkdb_app.serializers import WrongKeyValidationSerializer, ExSerializer
from pkdb_app.substances.models import Substance
from pkdb_app.utils import update_or_create_multiple
from rest_framework import serializers

FIELDS_CATEGORIAL = ["sid", "name", "creator", "url_slug", "description", "annotations", "synonyms"]

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


class NameFieldSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["name"]

    def to_representation(self, instance):
        return instance.name


class UnitSerializer(NameFieldSerializer):
    class Meta:
        model = Unit
        fields = ["name"]

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

#delete ?
class BaseCategorySerializer(WrongKeyValidationSerializer):
    annotations = AnnotationSerializer(many=True, allow_null=True)
    synonyms = SynonymSerializer(many=True, read_only=False, required=False, allow_null=True)

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        data["creator"] = self.context['request'].user.id
        return super().to_internal_value(data)


class ChoiceSerializer(serializers.ModelSerializer):
    annotations = AnnotationSerializer(many=True, allow_null=True)

    class Meta:
        model = Choice
        fields = ["name", "annotations", "description"]

class BaseSerializer(WrongKeyValidationSerializer):
    annotations = AnnotationSerializer(many=True, allow_null=True)
    synonyms = SynonymSerializer(many=True, read_only=False, required=False, allow_null=True)

    def pop_related(self, data):
        related_instances = ["annotations","synonyms"]
        return {related: data.pop(related, []) for related in related_instances}


    def update_or_create_related(self, instance, related_dict):
        lookup_fields = {"annotations": ["term", "relation"], "synonyms": ["name"]}

        for related, related_data in related_dict.items():
            if hasattr(instance, related):
                related_instance = getattr(instance, related)
                related_instance.clear()

            update_or_create_multiple(instance, related_data, related, lookup_fields=lookup_fields[related])

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["creator"] = instance.creator.username
        return data

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        data["creator"] = self.context['request'].user.id
        return super().to_internal_value(data)

    def create(self, validated_data):
        related_dict = self.pop_related(validated_data)
        instance = self.Meta.model.objects.create(**validated_data)
        self.update_or_create_related(instance, related_dict)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        related_dict = self.pop_related(validated_data)
        for name, value in validated_data.items():
            setattr(instance, name, value)
        self.update_or_create_related(instance, related_dict)
        instance.save()
        return instance


class TissueSerializer(BaseSerializer):
    class Meta:
        model = Tissue
        fields = FIELDS_CATEGORIAL


class FormSerializer(BaseSerializer):

    class Meta:
        model = Form
        fields = FIELDS_CATEGORIAL


class ApplicationSerializer(BaseSerializer):
    class Meta:
        model = Application
        fields = FIELDS_CATEGORIAL


class RouteSerializer(BaseSerializer):

    class Meta:
        model = Route
        fields = FIELDS_CATEGORIAL


class MeasurementTypeSerializer(BaseSerializer):
    units = UnitSerializer(many=True, allow_null=True)

    class Meta:
        model = MeasurementType
        fields = ["name", "url_slug", "dtype", "creator", "description", "units", "annotations", "synonyms","choices"]

    def pop_related(self, data):
        related_instances = ["units", "choices", "annotations","synonyms"]
        return {related: data.pop(related, []) for related in related_instances}


    def update_or_create_related(self, instance, related_dict):
        lookup_fields = {"units": ["name"], "choices": ["name"], "synonyms": ["name"], "annotations": ["term", "relation"]}

        for related, related_data in related_dict.items():
            if hasattr(instance, related):
                related_instance = getattr(instance, related)
                related_instance.clear()

            update_or_create_multiple(instance, related_data, related, lookup_fields=lookup_fields[related])

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        data["creator"] = self.context['request'].user.id
        for field in ["units"]:
            data[field] = [{"name": value} for value in data.get(field, [])]

        return super().to_internal_value(data)


class MeasurementTypeElasticSerializer(serializers.ModelSerializer):
    units = UnitSerializer(many=True, allow_null=True)
    annotations = AnnotationSerializer(many=True, allow_null=True)
    choices = ChoiceSerializer(many=True, allow_null=True)
    synonyms = SynonymSerializer(many=True, read_only=False, required=False, allow_null=True)

    class Meta:
        model = MeasurementType
        fields = ["name", "url_slug", "dtype", "description", "units", "annotations", "choices", "synonyms"]

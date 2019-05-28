"""
Serializers for interventions.
"""

# ----------------------------------
# Interventions
# ----------------------------------
from pkdb_app.categorials.models import Unit, Choice,Keyword, MeasurementType, Annotation, XRef
from pkdb_app.serializers import WrongKeyValidationSerializer, ExSerializer
from pkdb_app.substances.models import Substance
from pkdb_app.utils import update_or_create_multiple
from rest_framework import serializers


class EXMeasurementTypeableSerializer(ExSerializer):
    pass

class MeasurementTypeableSerializer(EXMeasurementTypeableSerializer):
    substance = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Substance.objects.all(),
        read_only=False,
        required=False,
        allow_null=True,
    )

    measurement_type = serializers.SlugRelatedField(
        slug_field="name",
        queryset=MeasurementType.objects.all())


class NameFieldSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["name"]

    def to_representation(self, instance):
        return instance.name


class UnitSerializer(NameFieldSerializer):
    class Meta:
        model = Unit
        fields = ["name"]



class ChoiceSerializer(NameFieldSerializer):
    class Meta:
        model = Choice
        fields = ["name"]


class AnnotationSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    class Meta:
        model = Annotation
        fields = ["name","relation"]




class XRefSerializer(NameFieldSerializer):
    class Meta:
        model = XRef
        fields = ["name"]


class BaseSerializer(WrongKeyValidationSerializer):

    def pop_related(self,data):
        related_instances = ["units","choices","annotations","xrefs"]
        return {related:data.pop(related,[]) for related in related_instances}


    def update_or_create_related(self,instance, related_dict):

        for related,related_data in related_dict.items():
            if hasattr(instance, related):
                related_instance = getattr(instance,related)
                related_instance.clear()
            update_or_create_multiple(instance, related_data, related, lookup_field="name")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["creator"] = instance.creator.username
        return data

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        data["creator"] = self.context['request'].user.id
        for field in ["units","xrefs","choices"]:
            data[field] = [{"name":value} for value in data.get(field,[])]


        return super().to_internal_value(data)

    def create(self, validated_data):
        related_dict = self.pop_related(validated_data)
        instance = self.Meta.model.objects.create(**validated_data)
        self.update_or_create_related(instance,related_dict)
        instance.save()

        return instance

    def update(self, instance, validated_data):
        related_dict = self.pop_related(validated_data)
        for name, value in validated_data.items():
            setattr(instance, name, value)
        self.update_or_create_related(instance,related_dict)
        instance.save()
        return instance


class MeasurementTypeSerializer(BaseSerializer):
    choices = ChoiceSerializer(many=True, allow_null=True)
    units = UnitSerializer(many=True, allow_null=True)
    xrefs = XRefSerializer(many=True, allow_null=True)
    annotations = AnnotationSerializer(many=True, allow_null=True)

    class Meta:
        model = MeasurementType
        fields = ["name", "url_slug", "dtype", "creator", "description", "units", "xrefs", "annotations", "choices"]


# ----------------------------------
# Keyword
# ----------------------------------
class KeywordSerializer(WrongKeyValidationSerializer):
    """ Keyword. """

    class Meta:
        model = Keyword
        fields = ["name","creator"]

    def create(self, validated_data):
        keyword, created = Keyword.objects.update_or_create(**validated_data)
        return keyword

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        data["creator"] = self.context['request'].user.id
        return super().to_internal_value(data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["creator"] = instance.creator.username
        return data


###############################################################################################
# Elastic Serializer
###############################################################################################

class KeywordElasticSerializer(serializers.ModelSerializer):
    """ Keyword. """

    class Meta:
        model = Keyword
        fields = ["name"]


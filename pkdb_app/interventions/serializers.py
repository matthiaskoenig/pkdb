"""
Serializers for interventions.
"""
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from rest_framework import serializers

from pkdb_app.comments.serializers import DescriptionsSerializer
from pkdb_app.interventions.models import Substance, InterventionSet, Intervention, Output, OutputSet, Timecourse
from pkdb_app.serializers import ParserSerializer
from pkdb_app.subjects.models import Individual, Group, DataFile
from pkdb_app.utils import un_map, validate_categorials


class SubstanceSerializer(serializers.ModelSerializer):
    """ Substance. """
    class Meta:
        model = Substance
        fields = ["name"]

    def create(self, validated_data):
        substance, created = Substance.objects.update_or_create(**validated_data)
        return substance


class InterventionSerializer(ParserSerializer):
    """ Intervention."""
    substance = serializers.SlugRelatedField(slug_field="name",queryset=Substance.objects.all(),read_only=False, required=False, allow_null=True)

    class Meta:
        model = Intervention
        fields = ["category", "name", "route", "form", "application", "time", "time_unit", "value", "unit", "substance"]

    def to_internal_value(self, data):
        data = self.split_to_map(data)
        data = self.drop_blank(data)
        data = self.strip(data)
        return super().to_internal_value(data)

    def validate(self, data):
        validated_data = super().validate(data)
        return validate_categorials(validated_data, "intervention")

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        return un_map(rep)


class InterventionSetSerializer(ParserSerializer):
    """ InterventionSet. """
    interventions = InterventionSerializer(many=True, read_only=False, required=False, allow_null=True)
    descriptions = DescriptionsSerializer(many=True, read_only=False, required=False, allow_null=True)

    class Meta:
        model = InterventionSet
        fields = ["descriptions", "interventions"]

    def to_internal_value(self, data):
        """

        :param data:
        :return:
        """
        data = self.split_entries_for_key(data, "interventions")
        return super(InterventionSetSerializer, self).to_internal_value(data)


class OutputSerializer(ParserSerializer):
    """
    Output
    """
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(),
                                               read_only=False, required=False, allow_null=True)
    individual = serializers.PrimaryKeyRelatedField(queryset=Individual.objects.all(),
                                                    read_only=False, required=False, allow_null=True)
    interventions = serializers.PrimaryKeyRelatedField(queryset=Intervention.objects.all(), many=True,
                                                       read_only=False, required=False, allow_null=True)
    substance = serializers.SlugRelatedField(slug_field="name", queryset=Substance.objects.all(),
                                             read_only=False, required=False, allow_null=True)
    source = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)
    figure = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Output
        fields = ["source", "figure", "format"] + \
                 ["value", "mean", "median", "min", "max", "sd", "se", "cv", "unit"] + \
                 ["value_map", "mean_map", "median_map", "min_map", "max_map", "sd_map", "se_map", "cv_map", "unit_map"] + \
                 ["pktype", "pktype_map", "time", "time_unit", "time_unit_map",
                    "time_map", "group", "group_map", "individual", "individual_map", "interventions", "interventions_map",
                    "substance", "substance_map", "tissue", "tissue_map", "subset_map"]

    def to_internal_value(self, data):
        study_sid = self.context['request'].path.split("/")[-2]
        data = self.split_to_map(data)

        if "group" in data :
            if data["group"]:
                try:
                    data["group"] = Group.objects.get(Q(groupset__study__sid=study_sid) & Q(name=data.get("group"))).pk
                except ObjectDoesNotExist:
                    msg = f'group: {data.get("group")} in study: {study_sid} does not exist'
                    raise serializers.ValidationError(msg)

        if "individual" in data:
            if data["individual"]:
                try:
                    data["individual"] = Individual.objects.get(Q(individualset__study__sid=study_sid) & Q(name=data.get("individual"))).pk
                except ObjectDoesNotExist:
                    msg = f'individual: {data.get("individual")} in study: {study_sid} does not exist'
                    raise serializers.ValidationError(msg)

        if "interventions" in data:
            if data["interventions"]:
                interventions = []
                for internvention in data["interventions"]:
                    try:
                        interventions.append(Intervention.objects.get(Q(interventionset__study__sid=study_sid) & Q(name=internvention)).pk)
                    except ObjectDoesNotExist:
                        msg = f'intervention: {internvention} in study: {study_sid} does not exist'
                        raise serializers.ValidationError(msg)
                    data["interventions"] = interventions

        data = self.strip(data)
        data = self.drop_blank(data)
        data = self.drop_empty(data)

        return super().to_internal_value(data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if "group" in rep:
            rep["group"] = instance.group.name
        if "interventions" in rep:
            rep["interventions"] = [intervention.name for intervention in instance.interventions.all()]
        for file in ["source", "figure"]:
            if file in rep:
                current_site = f'http://{get_current_site(self.context["request"]).domain}'
                rep[file] = current_site + getattr(instance, file).file.url

        return un_map(rep)

    def validate(self, data):
        validated_data = super().validate(data)

        # either group or individual set
        if validated_data.get("individual") and (validated_data.get("group") or validated_data.get("group_map")):
            raise serializers.ValidationError(
                ["individual and group cannot be set together on output.",
                validated_data
            ])
        if not validated_data.get("individual") and not (validated_data.get("group") or validated_data.get("group_map")):
            raise serializers.ValidationError(
                ["either individual or group must be set together on output.",
                validated_data
            ])

        return validated_data


class TimecourseSerializer(OutputSerializer):
    """ Timecourse. """
    class Meta:
        model = Timecourse
        fields = ["source", "figure", "format"] + \
                 ["value", "mean", "median", "min", "max", "sd", "se", "cv", "unit", ] \
                 + ["value_map", "mean_map", "median_map", "min_map", "max_map", "sd_map", "se_map", "cv_map",
                    "unit_map"] \
                 + ["pktype", "pktype_map", "time",
                    "time_map", "time_unit","subset_map",
                    "time_unit_map", "group", "group_map", "individual", "individual_map", "interventions",
                    "interventions_map",
                    "substance", "substance_map", "tissue", "tissue_map"]


class OutputSetSerializer(ParserSerializer):
    """
    OutputSet
    """
    outputs = OutputSerializer(many=True, read_only=False, required=False, allow_null=True)
    timecourses = TimecourseSerializer(many=True, read_only=False, required=False, allow_null=True)
    descriptions = DescriptionsSerializer(many=True,read_only=False,required=False, allow_null=True )

    class Meta:
        model = OutputSet
        fields = ["descriptions","outputs","timecourses"]

    def to_internal_value(self, data):
        """
        :param data:
        :return:
        """
        data = self.split_entries_for_key(data, "outputs")
        data = self.split_entries_for_key(data, "timecourses")

        return super().to_internal_value(data)

"""
Serializers for interventions.
"""
import pandas as pd
from copy import deepcopy

from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Q
from rest_framework import serializers

from pkdb_app.categoricals import FORMAT_MAPPING
from pkdb_app.comments.serializers import DescriptionsSerializer
from pkdb_app.interventions.models import Substance, InterventionSet, Intervention, Output, OutputSet, Timecourse, \
    InterventionEx, OutputEx, TimecourseEx
from pkdb_app.serializers import ExSerializer, MappingSerializer, WrongKeyValidationSerializer, BaseOutputExSerializer

from pkdb_app.subjects.models import IndividualEx, Group, DataFile, Individual, GroupEx
from pkdb_app.utils import validate_categorials, recursive_iter, set_keys

from pkdb_app.subjects.serializers import VALUE_MAP_FIELDS,VALUE_FIELDS,EXTERN_FILE_FIELDS

# ----------------------------------
# Serializer FIELDS
# ----------------------------------
INTERVENTION_FIELDS = ["name","category", "route", "form", "application", "time", "time_unit","substance","route","choice"]

INTERVENTION_MAP_FIELDS = ["name_map", "route_map", "form_map", "application_map","time_map", "time_unit_map",
                            "unit_map","substance_map","route_map","choice_map"]

OUTPUT_FIELDS = ["pktype", "tissue", "substance", "time", "time_unit"]

OUTPUT_MAP_FIELDS = ["pktype_map", "tissue_map", "substance_map", "time_map", "time_unit_map"]

# ----------------------------------
# substance
# ----------------------------------
class SubstanceSerializer(WrongKeyValidationSerializer):
    """ Substance. """
    class Meta:
        model = Substance
        fields = ["name"]

    def create(self, validated_data):
        substance, created = Substance.objects.update_or_create(**validated_data)
        return substance


# ----------------------------------
# Interventions
# ----------------------------------
class InterventionSerializer(ExSerializer):
    substance = serializers.SlugRelatedField(slug_field="name",queryset=Substance.objects.all(),read_only=False, required=False, allow_null=True)

    class Meta:
        model = Intervention
        fields = VALUE_FIELDS + INTERVENTION_FIELDS

    def to_internal_value(self, data):
        data = self.retransform_map_fields(data)
        data = self.retransform_ex_fields(data)
        return super(serializers.ModelSerializer, self).to_internal_value(data)


class InterventionExSerializer(ExSerializer):
    substance = serializers.SlugRelatedField(slug_field="name",queryset=Substance.objects.all(),read_only=False, required=False, allow_null=True)

    ######
    source = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)
    figure = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)

    # internal data
    interventions = InterventionSerializer(many=True, write_only=True, required=False, allow_null=True)


    class Meta:
        model = InterventionEx
        fields = EXTERN_FILE_FIELDS + VALUE_MAP_FIELDS + VALUE_FIELDS + INTERVENTION_FIELDS + INTERVENTION_MAP_FIELDS + ['interventions']

    def to_internal_value(self, data):


        # ----------------------------------
        # decompress external format
        # ----------------------------------
        temp_interventions = self.split_entry(data)
        interventions = []
        for intervention in temp_interventions:
            interventions_from_file = self.entries_from_file(intervention)
            interventions.extend(interventions_from_file)
        # ----------------------------------
        # finished
        # ----------------------------------

        #data = self.transform_ex_fields(data)
        data = self.transform_map_fields(data)

        data["interventions"] = interventions
        return super(WrongKeyValidationSerializer, self).to_internal_value(data)


    def validate(self, attrs):
        validate_categorials(attrs, "intervention")
        return super().validate(attrs)



class InterventionSetSerializer(ExSerializer):
    """ InterventionSet. """
    intervention_exs = InterventionExSerializer(many=True, read_only=False, required=False, allow_null=True)
    descriptions = DescriptionsSerializer(many=True, read_only=False, required=False, allow_null=True)

    class Meta:
        model = InterventionSet
        fields = ["descriptions", "intervention_exs"]


# ----------------------------------
# results
# ----------------------------------

class OutputSerializer(ExSerializer):
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(),
                                               read_only=False, required=False, allow_null=True)
    individual = serializers.PrimaryKeyRelatedField(queryset=Individual.objects.all(),
                                                    read_only=False, required=False, allow_null=True)
    interventions = serializers.PrimaryKeyRelatedField(queryset=Intervention.objects.all(), many=True,
                                                       read_only=False, required=False, allow_null=True)
    substance = serializers.SlugRelatedField(slug_field="name", queryset=Substance.objects.all(),
                                             read_only=False, required=False, allow_null=True)



    class Meta:
        model = OutputEx
        fields = OUTPUT_FIELDS + VALUE_FIELDS + \
                 ["group","individual","interventions"]

    def to_internal_value(self, data):

        data = self.retransform_map_fields(data)
        #data = self.retransform_ex_fields(data)
        data =  self.to_internal_related_fields(data)

        return super(serializers.ModelSerializer, self).to_internal_value(data)


class OutputExSerializer(BaseOutputExSerializer):
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

    # internal data
    outputs = OutputSerializer(many=True, write_only=True, required=False, allow_null=True)

    class Meta:
        model = OutputEx
        fields = EXTERN_FILE_FIELDS + OUTPUT_FIELDS + OUTPUT_MAP_FIELDS + VALUE_FIELDS + VALUE_MAP_FIELDS + \
                 ["group","individual","interventions"] + \
                 ["group_map","individual_map","interventions_map","outputs"]


    def to_internal_value(self, data):
        # ----------------------------------
        # decompress external format
        # ----------------------------------
        temp_outputs = self.split_entry(data)
        outputs = []
        for output in temp_outputs:
            outputs_from_file = self.entries_from_file(output)
            outputs.extend(outputs_from_file)
        # ----------------------------------
        # finished
        # ----------------------------------
        data = self.transform_map_fields(data)
        data["outputs"] = outputs
        data = self.to_internal_related_fields(data)
        return super(WrongKeyValidationSerializer, self).to_internal_value(data)

class TimecourseSerializer(BaseOutputExSerializer):
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(),
                                               read_only=False, required=False, allow_null=True)
    individual = serializers.PrimaryKeyRelatedField(queryset=Individual.objects.all(),
                                                       read_only=False, required=False, allow_null=True)
    interventions = serializers.PrimaryKeyRelatedField(queryset=Intervention.objects.all(), many=True,
                                                          read_only=False, required=False, allow_null=True)
    substance = serializers.SlugRelatedField(slug_field="name", queryset=Substance.objects.all(),
                                             read_only=False, required=False, allow_null=True)

    class Meta:
        model = Timecourse
        fields = OUTPUT_FIELDS + VALUE_FIELDS + ["group", "individual", "interventions"]

    def to_internal_value(self, data):
        # ----------------------------------
        # decompress external format
        # ----------------------------------
        data = self.to_internal_related_fields(data)
        return super(WrongKeyValidationSerializer, self).to_internal_value(data)


class TimecourseExSerializer(BaseOutputExSerializer):
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
    # internal data
    timecourses = TimecourseSerializer(many=True, write_only=True, required=False, allow_null=True)



    class Meta:
        model = TimecourseEx
        fields = EXTERN_FILE_FIELDS + OUTPUT_FIELDS + OUTPUT_MAP_FIELDS + VALUE_FIELDS + VALUE_MAP_FIELDS + \
                 ["group", "individual", "interventions"] + \
                 ["group_map", "individual_map", "interventions_map"] + ["timecourses"]

    def to_internal_value(self, data):
        # ----------------------------------
        # decompress external format
        # ----------------------------------
        temp_timecourses = self.split_entry(data)
        timecourses = []
        for timecourse in temp_timecourses:
            timecourses_from_file = self.array_from_file(timecourse)
            timecourses.append(timecourses_from_file)
        # ----------------------------------
        # finished
        # ----------------------------------

        # data = self.transform_ex_fields(data)
        data = self.transform_map_fields(data)

        data["timecourses"] = timecourses
        data = self.to_internal_related_fields(data)
        return super(WrongKeyValidationSerializer, self).to_internal_value(data)


class OutputSetSerializer(ExSerializer):
    """
    OutputSet
    """
    output_exs = OutputExSerializer(many=True, read_only=False, required=False, allow_null=True)
    timecourse_exs = TimecourseExSerializer(many=True, read_only=False, required=False, allow_null=True)
    descriptions = DescriptionsSerializer(many=True,read_only=False,required=False, allow_null=True)

    class Meta:
        model = OutputSet
        fields = ["descriptions","timecourse_exs","output_exs"]
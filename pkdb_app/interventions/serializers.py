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

        data = self.transform_ex_fields(data)
        data = self.transform_map_fields(data)

        data["interventions"] = interventions


        return super(WrongKeyValidationSerializer, self).to_internal_value(data)


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





'''
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
        return unmap_keys(rep)


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

class CleanOutputSerializer(ParserSerializer):
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(),
                                               read_only=False, required=False, allow_null=True)
    individual = serializers.PrimaryKeyRelatedField(queryset=IndividualEx.objects.all(),
                                                    read_only=False, required=False, allow_null=True)
    interventions = serializers.PrimaryKeyRelatedField(queryset=Intervention.objects.all(), many=True,
                                                       read_only=False, required=False, allow_null=True)
    substance = serializers.SlugRelatedField(slug_field="name", queryset=Substance.objects.all(),
                                             read_only=False, required=False, allow_null=True)
    source = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)
    figure = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)

    class Meta:
        model = CleanOutput
        fields = ["source", "figure", "format"] + \
                 ["value", "mean", "median", "min", "max", "sd", "se", "cv", "unit"] + \
                 ["pktype", "time", "time_unit","group",  "individual",  "interventions",
                 "substance", "tissue"]

    def to_internal_value(self,data):

        data = self.strip(data)
        data = self.drop_blank(data)
        data = self.drop_empty(data)
        study_sid = self.context['request'].path.split("/")[-2]

        if "group" in data:
            if data["group"]:
                try:
                    data["group"] = Group.objects.get(
                        Q(groupset__study__sid=study_sid) & Q(name=data.get("group"))).pk
                except ObjectDoesNotExist:
                    msg = f'group: {data.get("group")} in study: {study_sid} does not exist'
                    raise serializers.ValidationError(msg)

        if "individual" in data:
            if data["individual"]:
                try:
                    data["individual"] = Individual.objects.get(
                        Q(individualset__study__sid=study_sid) & Q(name=data.get("individual"))).pk
                except ObjectDoesNotExist:
                    msg = f'individual: clean individual {data.get("individual")} in study: {study_sid} does not exist'
                    raise serializers.ValidationError(msg)

        if "interventions" in data:
            if data["interventions"]:
                interventions = []
                for internvention in data["interventions"]:
                    try:
                        interventions.append(Intervention.objects.get(
                            Q(interventionset__study__sid=study_sid) & Q(name=internvention)).pk)
                    except ObjectDoesNotExist:
                        msg = f'intervention: {internvention} in study: {study_sid} does not exist'
                        raise serializers.ValidationError(msg)
                    data["interventions"] = interventions

        return super().to_internal_value(data)


class OutputSerializer(CleanOutputSerializer):
    """
    Output
    """

    cleaned = CleanOutputSerializer(many=True,write_only=True, required=False, allow_null=True)

    class Meta:
        model = Output
        fields = ["cleaned"]+["source", "figure", "format"] + \
                 ["value", "mean", "median", "min", "max", "sd", "se", "cv", "unit"] + \
                 ["value_map", "mean_map", "median_map", "min_map", "max_map", "sd_map", "se_map", "cv_map", "unit_map"] + \
                 ["pktype", "pktype_map", "time", "time_unit", "time_unit_map",
                    "time_map", "group", "group_map", "individual", "individual_map", "interventions", "interventions_map",
                    "substance", "substance_map", "tissue", "tissue_map", "subset_map"]

    def to_internal_value(self, data):
        initial_data = deepcopy(data)
        data = self.split_to_map(data)
        study_sid = self.context['request'].path.split("/")[-2]

        if "group" in data:
            if data["group"]:
                try:
                    data["group"] = Group.objects.get(
                        Q(groupset__study__sid=study_sid) & Q(name=data.get("group"))).pk
                except ObjectDoesNotExist:
                    msg = f'group: {data.get("group")} in study: {study_sid} does not exist'
                    raise serializers.ValidationError(msg)

        if "individual" in data:
            if data["individual"]:
                try:
                    data["individual"] = IndividualEx.objects.get(
                        Q(individualset__study__sid=study_sid) & Q(name=data.get("individual"))).pk
                except ObjectDoesNotExist:
                    msg = f'individual: {data.get("individual")} in study: {study_sid} does not exist'
                    raise serializers.ValidationError(msg)

        if "interventions" in data:
            if data["interventions"]:
                interventions = []
                for internvention in data["interventions"]:
                    try:
                        interventions.append(Intervention.objects.get(
                            Q(interventionset__study__sid=study_sid) & Q(name=internvention)).pk)
                    except ObjectDoesNotExist:
                        msg = f'intervention: {internvention} in study: {study_sid} does not exist'
                        raise serializers.ValidationError(msg)
                    data["interventions"] = interventions

        data = self.strip(data)
        data = self.drop_blank(data)
        data = self.drop_empty(data)

        # ---------------------------------------
        # add cleaned outputs
        # ---------------------------------------
        cleaned_outputs = []

        # check if any mapping
        is_mapping = any("map" in field for field in data.keys())

        if is_mapping:

            source = initial_data.get("source")
            delimiter = FORMAT_MAPPING[initial_data.pop("format")].delimiter
            src = DataFile.objects.get(pk=source)
            try:
                outputs_data = pd.read_csv(src.file, delimiter=delimiter, keep_default_na=False)
            except:
                raise serializers.ValidationError(["cannot read csv"], data)

            if "subset" in initial_data:
                subset = initial_data.pop("subset")
                values = subset.split("==")
                values = [v.strip() for v in values]
                if len(values) != 2:
                    raise serializers.ValidationError(["field has wrong pattern 'col_value'=='cell_value'", data])

                outputs_data = outputs_data.loc[outputs_data[values[0]] == values[1]]

                if len(outputs_data) == 0 :
                    raise serializers.ValidationError([f"the cell value <{values[1]}>' is missing in column <{values[0]}>", data])

            recursive_output_dict = list(recursive_iter(initial_data))

            for output in outputs_data.itertuples():

                output_dict = initial_data.copy()

                for keys, value in recursive_output_dict:

                    if isinstance(value, str):
                        if "==" in value:
                            values = value.split("==")
                            values = [v.strip() for v in values]
                            if len(values) != 2 or values[0] != "col":
                                raise serializers.ValidationError(["field has wrong pattern col=='col_value'", data])
                            try:
                                output_value = getattr(output, values[1])

                            except AttributeError:
                                raise serializers.ValidationError(
                                    [f"key <{values[1]}> is missing in file <{source}> ", data])

                            set_keys(output_dict, output_value, *keys)

                cleaned_outputs.append(deepcopy(output_dict))

        else:
            cleaned_outputs.append(initial_data)


        data["cleaned"] = cleaned_outputs

        # finish clean outputs
        # -------------------------------------------

        return super(ParserSerializer,self).to_internal_value(data)

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

        return unmap_keys(rep)

    def validate(self, data):
        validated_data = super().validate(data)

        # either group or individual set
        if (validated_data.get("individual") and validated_data.get("individual_map")) and (validated_data.get("group") or validated_data.get("group_map")):
            raise serializers.ValidationError(
                ["individual and group cannot be set together on output.",
                validated_data
            ])
        if not (validated_data.get("individual") or validated_data.get("individual_map")) and not (validated_data.get("group") or validated_data.get("group_map")):
            raise serializers.ValidationError(
                ["either individual or group must be set on output.",
                validated_data
            ])

        return validated_data

class CleanTimecourseSerializer(CleanOutputSerializer):

    class Meta:
        model = CleanTimecourse
        fields = CleanOutputSerializer.Meta.fields


class TimecourseSerializer(OutputSerializer):
    cleaned = CleanTimecourseSerializer(many=True,write_only=True, required=False, allow_null=True)

    """ Timecourse. """

    class Meta:
        model = Timecourse
        fields = ["cleaned"]+["source", "figure", "format"] + \
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
'''

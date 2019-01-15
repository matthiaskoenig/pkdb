"""
Serializers for interventions.
"""
import pandas as pd
from datetime import timedelta
from decimal import Decimal
import numpy as np
from django.contrib.sites.shortcuts import get_current_site
from rest_framework import serializers
import time

from pkdb_app.comments.serializers import DescriptionSerializer, CommentSerializer, DescriptionElasticSerializer, \
    CommentElasticSerializer
from pkdb_app.interventions.models import (
    Substance,
    InterventionSet,
    Intervention,
    Output,
    OutputSet,
    Timecourse,
    InterventionEx,
    OutputEx,
    TimecourseEx,
)
from pkdb_app.serializers import (
    ExSerializer,
    WrongKeyValidationSerializer,
    BaseOutputExSerializer,
    NA_VALUES)

from pkdb_app.subjects.models import Group, DataFile, Individual
from pkdb_app.categoricals import validate_categorials, MEDICATION, DOSING

from pkdb_app.subjects.serializers import (
    VALUE_MAP_FIELDS,
    VALUE_FIELDS,
    EXTERN_FILE_FIELDS, GroupSmallElasticSerializer, IndividualSmallElasticSerializer, VALUE_FIELDS_NO_UNIT)

# ----------------------------------
# Serializer FIELDS
# ----------------------------------
from pkdb_app.utils import list_of_pk

INTERVENTION_FIELDS = [
    "name",
    "category",
    "route",
    "form",
    "application",
    "time",
    "time_unit",
    "substance",
    "route",
    "choice",
]
INTERVENTION_MAP_FIELDS = [
    "name_map",
    "route_map",
    "form_map",
    "application_map",
    "time_map",
    "time_unit_map",
    "unit_map",
    "substance_map",
    "route_map",
    "choice_map",
]

OUTPUT_FIELDS = ["pktype", "tissue", "substance", "time", "time_unit"]
OUTPUT_MAP_FIELDS = [
    "pktype_map",
    "tissue_map",
    "substance_map",
    "time_map",
    "time_unit_map",
]


# ----------------------------------
# Substance
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
    substance = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Substance.objects.all(),
        read_only=False,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Intervention
        fields = VALUE_FIELDS + INTERVENTION_FIELDS

    def to_internal_value(self, data):
        data.pop("comments", None)
        data = self.retransform_map_fields(data)
        data = self.retransform_ex_fields(data)
        self.validate_wrong_keys(data)
        category = data.get("category")

        print(data)
        if any([category == MEDICATION,category == DOSING]):
            self._validate_requried_key(data,"substance")
            self._validate_requried_key(data,"route")
            self._validate_requried_key(data,"value")
            self._validate_requried_key(data,"unit")
            #if category == DOSING:
            #    self._validate_requried_key(data,"time")
            #    self._validate_requried_key(data,"time_unit")

        return super(serializers.ModelSerializer, self).to_internal_value(data)


class InterventionExSerializer(ExSerializer):
    substance = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Substance.objects.all(),
        read_only=False,
        required=False,
        allow_null=True,
    )

    ######
    source = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )
    figure = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    # internal data
    interventions = InterventionSerializer(
        many=True, write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = InterventionEx
        fields = (
            EXTERN_FILE_FIELDS
            + VALUE_MAP_FIELDS
            + VALUE_FIELDS
            + INTERVENTION_FIELDS
            + INTERVENTION_MAP_FIELDS
            + ["interventions", "comments"]
        )

    def to_internal_value(self, data):
        # ----------------------------------
        # decompress external format
        # ----------------------------------
        if not isinstance(data, dict):
            raise serializers.ValidationError(f"each intervention has to be a dict and not <{data}>")
        temp_interventions = self.split_entry(data)
        for key in VALUE_FIELDS_NO_UNIT:
            if data.get(key) in NA_VALUES:
                data[key] = None

        interventions = []
        for intervention in temp_interventions:
            interventions_from_file = self.entries_from_file(intervention)
            interventions.extend(interventions_from_file)
        # ----------------------------------
        # finished
        # ----------------------------------

        data = self.transform_map_fields(data)

        data["interventions"] = interventions
        self.validate_wrong_keys(data)

        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def validate(self, attrs):
        try:
            # perform via dedicated function on categorials
            validate_categorials(data=attrs, category_class="intervention")
        except ValueError as err:
            raise serializers.ValidationError(err)

        return super().validate(attrs)


class InterventionSetSerializer(ExSerializer):
    """ InterventionSet. """

    intervention_exs = InterventionExSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    class Meta:
        model = InterventionSet
        fields = ["descriptions", "intervention_exs", "comments"]

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        self.validate_wrong_keys(data)

        return data


# ----------------------------------
# Outputs
# ----------------------------------
class OutputSerializer(ExSerializer):
    group = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), read_only=False, required=False, allow_null=True
    )
    individual = serializers.PrimaryKeyRelatedField(
        queryset=Individual.objects.all(),
        read_only=False,
        required=False,
        allow_null=True,
    )
    interventions = serializers.PrimaryKeyRelatedField(
        queryset=Intervention.objects.all(),
        many=True,
        read_only=False,
        required=False,
        allow_null=True,
    )
    substance = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Substance.objects.all(),
        read_only=False,
        required=True,
    )

    class Meta:
        model = Output
        fields = OUTPUT_FIELDS + VALUE_FIELDS + ["group", "individual", "interventions"]

    def to_internal_value(self, data):
        data.pop("comments", None)
        data = self.retransform_map_fields(data)
        data = self.to_internal_related_fields(data)
        self.validate_wrong_keys(data)



        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def validate(self, attrs):
        self._validate_group_output(attrs)
        self._validate_individual_output(attrs)
        self._validate_pktype(attrs)
        self._validate_time_unit(attrs)
        self._validate_requried_key(attrs,"substance")
        self._validate_requried_key(attrs,"tissue")
        self._validate_requried_key(attrs,"interventions")

        return super().validate(attrs)


class OutputExSerializer(BaseOutputExSerializer):
    group = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), read_only=False, required=False, allow_null=True
    )
    individual = serializers.PrimaryKeyRelatedField(
        queryset=Individual.objects.all(),
        read_only=False,
        required=False,
        allow_null=True,
    )
    interventions = serializers.PrimaryKeyRelatedField(
        queryset=Intervention.objects.all(),
        many=True,
        read_only=False,
        required=False,
        allow_null=True,
    )
    substance = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Substance.objects.all(),
        read_only=False,
        required=False,
        allow_null=True,
    )

    source = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )
    figure = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )

    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    # internal data
    outputs = OutputSerializer(
        many=True, write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = OutputEx
        fields = (
            EXTERN_FILE_FIELDS
            + OUTPUT_FIELDS
            + OUTPUT_MAP_FIELDS
            + VALUE_FIELDS
            + VALUE_MAP_FIELDS
            + ["group", "individual", "interventions"]
            + [
                "group_map",
                "individual_map",
                "interventions_map",
                "outputs",
                "comments",
            ]
        )

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
        self.validate_wrong_keys(data)



        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def validate(self, attrs):
        try:
            validate_categorials(data=attrs, category_class="intervention")
        except ValueError as err:
            raise serializers.ValidationError(err)

        return super().validate(attrs)

    def validate_figure(self, value):
        self._validate_figure(value)
        return value


class TimecourseSerializer(BaseOutputExSerializer):
    group = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), read_only=False, required=False, allow_null=True
    )
    individual = serializers.PrimaryKeyRelatedField(
        queryset=Individual.objects.all(),
        read_only=False,
        required=False,
        allow_null=False,
    )
    interventions = serializers.PrimaryKeyRelatedField(
        queryset=Intervention.objects.all(),
        many=True,
        read_only=False,
        required=False,
    )
    substance = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Substance.objects.all(),
        read_only=False,
        required=True,
    )

    class Meta:
        model = Timecourse
        fields = OUTPUT_FIELDS + VALUE_FIELDS + ["group", "individual", "interventions"]

    def to_internal_value(self, data):
        data.pop("comments", None)
        data = self.to_internal_related_fields(data)
        self.validate_wrong_keys(data)
        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def validate(self, attrs):
        self._validate_group_output(attrs)
        self._validate_individual_output(attrs)
        self._validate_pktype(attrs)
        self._validate_time_unit(attrs)
        self._validate_requried_key(attrs,"substance")
        self._validate_requried_key(attrs,"interventions")
        self._validate_requried_key(attrs,"tissue")
        self._validate_requried_key(attrs,"time")

        return super().validate(attrs)




class TimecourseExSerializer(BaseOutputExSerializer):
    group = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), read_only=False, required=False, allow_null=True
    )
    individual = serializers.PrimaryKeyRelatedField(
        queryset=Individual.objects.all(),
        read_only=False,
        required=False,
        allow_null=True,
    )
    interventions = serializers.PrimaryKeyRelatedField(
        queryset=Intervention.objects.all(),
        many=True,
        read_only=False,
        required=False,
        allow_null=True,
    )
    substance = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Substance.objects.all(),
        read_only=False,
        required=False,
        allow_null=True,
    )

    source = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )
    figure = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    # internal data
    timecourses = TimecourseSerializer(
        many=True, write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = TimecourseEx
        fields = (
            EXTERN_FILE_FIELDS
            + OUTPUT_FIELDS
            + OUTPUT_MAP_FIELDS
            + VALUE_FIELDS
            + VALUE_MAP_FIELDS
            + ["group", "individual", "interventions"]
            + ["group_map", "individual_map", "interventions_map"]
            + ["timecourses", "comments"]
        )

    def to_internal_value(self, data):
        # ----------------------------------
        # decompress external format
        # ----------------------------------
        temp_timecourses = self.split_entry(data)
        timecourses = []

        for timecourse in temp_timecourses:
            timecourses_from_file = self.array_from_file(timecourse)
            timecourses.extend(timecourses_from_file)
        # ----------------------------------
        # finished
        # ----------------------------------
        data = self.transform_map_fields(data)

        data["timecourses"] = timecourses
        data = self.to_internal_related_fields(data)
        self.validate_wrong_keys(data)
        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def validate_figure(self, value):
        self._validate_figure(value)
        return value



class OutputSetSerializer(ExSerializer):
    """
    OutputSet
    """

    output_exs = OutputExSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    timecourse_exs = TimecourseExSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    class Meta:
        model = OutputSet
        fields = ["descriptions", "timecourse_exs", "output_exs", "comments"]

    def validate_output_exs(self, attrs):
        for output in attrs:
            self.validate_group_individual_output(output)
            self._validate_individual_output(output)
            self._validate_group_output(output)

        return attrs

    def validate_timcourse_exs(self, attrs):
        for timecourse in attrs:
            self.validate_group_individual_output(timecourse)
            self._validate_individual_output(timecourse)
            self._validate_group_output(timecourse)

        return attrs

    def to_internal_value(self, data):

        start_time = time.time()
        data = super().to_internal_value(data)
        self.validate_wrong_keys(data)
        outputset_upload_time = time.time() - start_time
        outputset_upload_time = timedelta(seconds=outputset_upload_time).total_seconds()
        print(f"--- {outputset_upload_time} outputset to internal value time in seconds ---")
        return data

    def validate(self, attrs):
        return super().validate(attrs)


###############################################################################################
# Elastic Serializer
###############################################################################################


class InterventionSetElasticSmallSerializer(serializers.HyperlinkedModelSerializer):
    descriptions = DescriptionElasticSerializer(many=True, read_only=True)
    comments = CommentElasticSerializer(many=True, read_only=True)
    interventions = serializers.SerializerMethodField()

    class Meta:
        model = InterventionSet
        fields = ["pk","descriptions", "interventions","comments"]

    def get_interventions(self,obj):

        return list_of_pk("interventions",obj)


# Intervention related Serializer
class InterventionSmallElasticSerializer(serializers.HyperlinkedModelSerializer):
    # url = serializers.HyperlinkedIdentityField(read_only=True,view_name="groups_read-detail")
    class Meta:
        model = Intervention
        fields = ["pk", 'name']  # , 'url']


class InterventionElasticSerializer(serializers.ModelSerializer):
    substance = serializers.SerializerMethodField()

    value = serializers.FloatField(allow_null=True)
    mean = serializers.FloatField(allow_null=True)
    median = serializers.FloatField(allow_null=True)
    min = serializers.FloatField(allow_null=True)
    max = serializers.FloatField(allow_null=True)
    sd = serializers.FloatField(allow_null=True)
    se = serializers.FloatField(allow_null=True)
    cv = serializers.FloatField(allow_null=True)
    class Meta:
        model = Intervention
        fields = ["pk","study", "final"] + VALUE_FIELDS + INTERVENTION_FIELDS

    def get_substance(self, obj):
        if obj.substance:
            try:
                return obj.substance.to_dict()
            except AttributeError:
                return obj.substance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        for field in VALUE_FIELDS_NO_UNIT + ["time"]:
                try:
                    rep[field] = '{:.2e}'.format(rep[field])
                except (ValueError, TypeError):
                    pass
        return rep




class OutputSetElasticSmallSerializer(serializers.HyperlinkedModelSerializer):
    descriptions = DescriptionElasticSerializer(many=True, read_only=True)
    comments = CommentElasticSerializer(many=True, read_only=True)
    outputs = serializers.SerializerMethodField()
    timecourses = serializers.SerializerMethodField()

    class Meta:
        model = OutputSet
        fields = ["pk","descriptions", "outputs","timecourses","comments"]

    def get_outputs(self,obj):
        return list_of_pk("outputs",obj)

    def get_timecourses(self,obj):
        return list_of_pk("timecourses",obj)


class OutputElasticSerializer(serializers.HyperlinkedModelSerializer):
    group = GroupSmallElasticSerializer()
    individual = IndividualSmallElasticSerializer()
    interventions = InterventionSmallElasticSerializer(many=True)
    substance = serializers.SerializerMethodField()

    value = serializers.FloatField(allow_null=True)
    mean = serializers.FloatField(allow_null=True)
    median = serializers.FloatField(allow_null=True)
    min = serializers.FloatField(allow_null=True)
    max = serializers.FloatField(allow_null=True)
    sd = serializers.FloatField(allow_null=True)
    se = serializers.FloatField(allow_null=True)
    cv = serializers.FloatField(allow_null=True)

    class Meta:
            model = Output
            fields = (
                ["pk","study"]
                + OUTPUT_FIELDS
                + VALUE_FIELDS
                + ["group", "individual", "final","interventions"])

    def get_substance(self,obj):
        if obj.substance:
            try:
                return obj.substance.to_dict()
            except AttributeError:
                return obj.substance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        for field in VALUE_FIELDS_NO_UNIT:
                try:
                    rep[field] = '{:.2e}'.format(rep[field])
                except (ValueError, TypeError):
                    pass
        return rep



class TimecourseElasticSerializer(serializers.HyperlinkedModelSerializer):
    group = GroupSmallElasticSerializer()
    individual =  IndividualSmallElasticSerializer()
    interventions =  InterventionSmallElasticSerializer(many=True)
    substance = serializers.SerializerMethodField()



    class Meta:
            model = Timecourse
            fields = (
                ["pk","study"]
                + OUTPUT_FIELDS
                + VALUE_FIELDS
                + ["group", "individual", "final","interventions","figure","auc_end","kel"])

    def get_substance(self,obj):
        if obj.substance:
            try:
                return obj.substance.to_dict()
            except AttributeError:
                return obj.substance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        for field in VALUE_FIELDS_NO_UNIT + ['time']:
            try:
                result = []
                for x in rep[field]:
                    try:
                        result.append('{:.2e}'.format(x))
                    except (ValueError, TypeError):
                        result.append(x)
                rep[field] = result
            except TypeError:
                pass
        return rep



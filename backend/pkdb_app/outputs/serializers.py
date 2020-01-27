"""
Serializers for interventions.
"""
import numpy as np
from rest_framework import serializers

from pkdb_app import utils
from pkdb_app.behaviours import MEASUREMENTTYPE_FIELDS, EX_MEASUREMENTTYPE_FIELDS, VALUE_FIELDS, \
    VALUE_FIELDS_NO_UNIT, map_field
from pkdb_app.info_nodes.models import InfoNode
from pkdb_app.info_nodes.serializers import MeasurementTypeableSerializer
from pkdb_app.interventions.serializers import InterventionSmallElasticSerializer
from .models import (
    Output,
    OutputSet,
    Timecourse,
    OutputEx,
    TimecourseEx, OutputIntervention, TimecourseIntervention)
from ..comments.serializers import DescriptionSerializer, CommentSerializer, DescriptionElasticSerializer, \
    CommentElasticSerializer
from ..interventions.models import Intervention
from ..serializers import (
    ExSerializer, PkSerializer, StudySmallElasticSerializer)
from ..subjects.models import Group, DataFile, Individual
from ..subjects.serializers import (
    EXTERN_FILE_FIELDS, GroupSmallElasticSerializer, IndividualSmallElasticSerializer)
# ----------------------------------
# Serializer FIELDS
# ----------------------------------
from ..utils import list_of_pk, _validate_requried_key

TISSUE_FIELD = ["tissue"]
TIME_FIELDS = ["time", "time_unit"]
OUTPUT_FIELDS = TISSUE_FIELD + TIME_FIELDS

OUTPUT_MAP_FIELDS = map_field(OUTPUT_FIELDS)


# ----------------------------------
# Outputs
# ----------------------------------


class OutputSerializer(MeasurementTypeableSerializer):
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
    tissue = utils.SlugRelatedField(
        slug_field="name",
        queryset=InfoNode.objects.filter(ntype=InfoNode.NTypes.Tissue),
        read_only=False,
        required=False
    )

    class Meta:
        model = Output
        fields = OUTPUT_FIELDS + MEASUREMENTTYPE_FIELDS + ["group", "individual", "interventions"]

    def to_internal_value(self, data):
        data.pop("comments", None)
        data.pop("descriptions", None)

        data = self.retransform_map_fields(data)
        data = self.to_internal_related_fields(data)
        self.validate_wrong_keys(data)
        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def validate(self, attrs):
        self._validate_individual_output(attrs)
        self._validate_group_output(attrs)
        self.validate_group_individual_output(attrs)

        _validate_requried_key(attrs, "measurement_type")
        _validate_requried_key(attrs, "substance")
        _validate_requried_key(attrs, "tissue")
        _validate_requried_key(attrs, "interventions")

        try:
            # perform via dedicated function on categorials
            attrs['measurement_type'] = attrs['measurement_type'].measurement_type
            if 'substance' in attrs:
                if attrs['substance'] is not None:
                    attrs['substance'] = attrs['substance'].substance
            if 'tissue' in attrs:
                if attrs['tissue'] is not None:
                    attrs['tissue'] = attrs['tissue'].tissue

            attrs["measurement_type"].validate_complete(data=attrs)
        except ValueError as err:
            raise serializers.ValidationError(err)

        return super().validate(attrs)


class BaseOutputExSerializer(ExSerializer):
    def to_representation(self, instance):

        rep = super().to_representation(instance)

        if "group" in rep:
            if rep["group"]:
                if instance.group:
                    rep["group"] = instance.group.name
                if instance.group_map:
                    rep["group"] = instance.group_map

        if "interventions" in rep:
            rep["interventions"] = [
                intervention.name for intervention in instance.interventions.all()
            ]

        return rep


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

    source = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )
    figure = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )

    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    descriptions = DescriptionSerializer(
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
                + EX_MEASUREMENTTYPE_FIELDS
                + ["group", "individual", "interventions"]
                + [
                    "group_map",
                    "individual_map",
                    "interventions_map",
                    "outputs",
                    "comments",
                    "descriptions"

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
    substance = utils.SlugRelatedField(
        slug_field="name",
        queryset=InfoNode.objects.filter(ntype=InfoNode.NTypes.Substance),
        read_only=False,
        required=False,
        allow_null=True,
    )

    measurement_type = utils.SlugRelatedField(
        slug_field="name",
        queryset=InfoNode.objects.filter(ntype=InfoNode.NTypes.MeasurementType),
        read_only=False,
        required=False
    )
    tissue = utils.SlugRelatedField(
        slug_field="name",
        queryset=InfoNode.objects.filter(ntype=InfoNode.NTypes.Tissue),
        read_only=False,
        required=False
    )

    class Meta:
        model = Timecourse
        fields = OUTPUT_FIELDS + MEASUREMENTTYPE_FIELDS + ["group", "individual", "interventions"]

    def to_internal_value(self, data):
        data.pop("comments", None)
        data.pop("descriptions", None)
        data = self.to_internal_related_fields(data)
        self.validate_wrong_keys(data)
        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def validate(self, attrs):
        self._validate_individual_output(attrs)
        self._validate_group_output(attrs)
        self.validate_group_individual_output(attrs)

        _validate_requried_key(attrs, "substance")
        _validate_requried_key(attrs, "interventions")
        _validate_requried_key(attrs, "tissue")
        _validate_requried_key(attrs, "time")
        _validate_requried_key(attrs, "measurement_type")

        self._validate_time_unit(attrs)
        self._validate_time(attrs["time"])

        try:
            # perform via dedicated function on categorials

            attrs['measurement_type'] = attrs['measurement_type'].measurement_type
            if 'substance' in attrs:
                    if attrs['substance'] is not None:
                        attrs['substance'] = attrs['substance'].substance
            if 'tissue' in attrs:
                if attrs['tissue'] is not None:
                    attrs['tissue'] = attrs['tissue'].tissue

            attrs["measurement_type"].validate_complete(data=attrs)
        except ValueError as err:
            raise serializers.ValidationError(err)

        return super().validate(attrs)

    def _validate_time(self, time):
        if any(np.isnan(np.array(time))):
            raise serializers.ValidationError({"time": "no timepoints are allowed to be nan", "detail": time})


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

    source = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )
    figure = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    descriptions = DescriptionSerializer(
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
                + EX_MEASUREMENTTYPE_FIELDS
                + ["group", "individual", "interventions"]
                + ["group_map", "individual_map", "interventions_map"]
                + ["timecourses", "comments", "descriptions"]
        )

    def to_internal_value(self, data):
        # ----------------------------------
        # decompress external format
        # ----------------------------------
        if not isinstance(data, dict):
            raise serializers.ValidationError(f"each timecourse has to be a dict and not <{data}>")
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

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        self.validate_wrong_keys(data)
        return data


###############################################################################################
# Elastic Serializer
###############################################################################################

class OutputSetElasticSmallSerializer(serializers.ModelSerializer):
    descriptions = DescriptionElasticSerializer(many=True, read_only=True)
    comments = CommentElasticSerializer(many=True, read_only=True)
    outputs = serializers.SerializerMethodField()
    timecourses = serializers.SerializerMethodField()

    class Meta:
        model = OutputSet
        fields = ["pk", "descriptions", "comments", "outputs", "timecourses", ]

    def get_outputs(self, obj):
        return list_of_pk("outputs", obj)

    def get_timecourses(self, obj):
        return list_of_pk("timecourses", obj)


class OutputInterventionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutputIntervention
        fields = ["study_sid", "study_name", "output_pk", "intervention_pk", "group_pk", "individual_pk", "normed",
                  "calculated"] + OUTPUT_FIELDS + MEASUREMENTTYPE_FIELDS


class TimecourseInterventionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimecourseIntervention
        fields = ["study_sid", "study_name", "timecourse_pk", "intervention_pk", "group_pk", "individual_pk",
                  "normed"] + OUTPUT_FIELDS + MEASUREMENTTYPE_FIELDS

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


class OutputElasticSerializer(serializers.ModelSerializer):
    study = StudySmallElasticSerializer(read_only=True)
    group = GroupSmallElasticSerializer()
    individual = IndividualSmallElasticSerializer()
    interventions = InterventionSmallElasticSerializer(many=True)
    substance = serializers.CharField()
    measurement_type = serializers.CharField()
    tissue = serializers.CharField()

    value = serializers.FloatField(allow_null=True)
    mean = serializers.FloatField(allow_null=True)
    median = serializers.FloatField(allow_null=True)
    min = serializers.FloatField(allow_null=True)
    max = serializers.FloatField(allow_null=True)
    sd = serializers.FloatField(allow_null=True)
    se = serializers.FloatField(allow_null=True)
    cv = serializers.FloatField(allow_null=True)

    timecourse = PkSerializer()

    class Meta:
        model = Output
        fields = (
                ["pk", "normed", "calculated", "timecourse"]
                + TISSUE_FIELD
                + ["study"]
                + ["group", "individual", "interventions"]
                + MEASUREMENTTYPE_FIELDS
                + TIME_FIELDS
                + VALUE_FIELDS
        )


class TimecourseElasticSerializer(serializers.ModelSerializer):
    study = StudySmallElasticSerializer(read_only=True)
    group = GroupSmallElasticSerializer()
    individual = IndividualSmallElasticSerializer()
    interventions = InterventionSmallElasticSerializer(many=True)
    measurement_type = serializers.CharField()
    tissue = serializers.CharField()

    outputs = PkSerializer(many=True)
    substance = serializers.CharField()

    class Meta:
        model = Timecourse
        fields = (
                ["pk", "normed", "outputs"]
                + TISSUE_FIELD
                + ["study"]
                + ["group", "individual", "interventions"]
                + MEASUREMENTTYPE_FIELDS
                + TIME_FIELDS
                + VALUE_FIELDS
        )

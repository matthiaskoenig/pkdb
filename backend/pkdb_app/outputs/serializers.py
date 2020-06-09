"""
Serializers for interventions.
"""


import warnings
import traceback

import numpy as np

from django.apps import apps
from rest_framework import serializers

from pkdb_app import utils
from pkdb_app.behaviours import MEASUREMENTTYPE_FIELDS, EX_MEASUREMENTTYPE_FIELDS, VALUE_FIELDS, \
    VALUE_FIELDS_NO_UNIT, map_field
from pkdb_app.info_nodes.models import InfoNode
from pkdb_app.info_nodes.serializers import MeasurementTypeableSerializer
from pkdb_app.interventions.serializers import InterventionSmallElasticSerializer
from pkdb_app.outputs.pk_calculation import pkoutputs_from_timecourse
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
    ExSerializer, PkSerializer, StudySmallElasticSerializer, SidNameSerializer)
from ..subjects.models import Group, DataFile, Individual
from ..subjects.serializers import (
    EXTERN_FILE_FIELDS, GroupSmallElasticSerializer, IndividualSmallElasticSerializer)
# ----------------------------------
# Serializer FIELDS
# ----------------------------------
from ..utils import list_of_pk, _validate_requried_key, create_multiple, _create, create_multiple_bulk_normalized, \
    create_multiple_bulk

EXTRA_FIELDS = ["tissue", "method"]
TIME_FIELDS = ["time", "time_unit"]
OUTPUT_FIELDS = EXTRA_FIELDS + TIME_FIELDS

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

    method = utils.SlugRelatedField(
        slug_field="name",
        queryset=InfoNode.objects.filter(ntype=InfoNode.NTypes.Method),
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
        data = self.to_internal_related_fields(data) # fixme
        self.validate_wrong_keys(data, additional_fields=OutputExSerializer.Meta.fields)
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
            attrs['measurement_type'] = attrs['measurement_type'].measurement_type

            for key in ['substance', 'tissue', 'method']:
                if key in attrs:
                    if attrs[key] is not None:
                        attrs[key] = getattr(attrs[key], key)


            attrs["choice"] = attrs["measurement_type"].validate_complete(data=attrs)["choice"]

        except ValueError as err:
            raise serializers.ValidationError(err)

        return super().validate(attrs)



class OutputExSerializer(ExSerializer):

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
                EXTERN_FILE_FIELDS + [
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

        # here I am
        drop_fields = OUTPUT_FIELDS + \
                      OUTPUT_MAP_FIELDS + \
                      EX_MEASUREMENTTYPE_FIELDS+ \
                      ["group", "individual", "interventions"] + \
                      ["group_map","individual_map", "interventions_map"]
        [data.pop(field, None) for field in drop_fields]
        data["outputs"] = outputs

        data = self.transform_map_fields(data)


        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def validate_figure(self, value):
        self._validate_figure(value)
        return value

    def create(self, validated_data):
        output_ex, poped_data = _create(model_manager=self.Meta.model.objects,
                               validated_data=validated_data,
                               create_multiple_keys=['comments', 'descriptions'],
                               pop=['outputs'])

        outputs = poped_data["outputs"]
        outputs_interventions = []
        for output in outputs:
            output["study"] = self.context["study"]
            outputs_interventions.append(output.pop('interventions', []))

        outputs_dj = create_multiple_bulk(output_ex, 'ex', outputs, Output)
        for output, intervetions  in zip(outputs_dj, outputs_interventions):
            output._interventions.add(*intervetions)

        outputs_normed = create_multiple_bulk_normalized(outputs_dj, Output)
        for output in outputs_normed:
            output._interventions.add(*output.interventions.all())
        return output_ex


class TimecourseSerializer(MeasurementTypeableSerializer):
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

    method = utils.SlugRelatedField(
        slug_field="name",
        queryset=InfoNode.objects.filter(ntype=InfoNode.NTypes.Method),
        read_only=False,
        required=False
    )
    outputs = OutputSerializer(many=True, read_only=True)

    class Meta:
        model = Timecourse
        fields = OUTPUT_FIELDS + MEASUREMENTTYPE_FIELDS + ["group", "individual", "interventions"] +["outputs"]

    def to_internal_value(self, data):
        data.pop("comments", None)
        data.pop("descriptions", None)
        data = self.to_internal_related_fields(data)
        self.validate_wrong_keys(data, additional_fields=TimecourseExSerializer.Meta.fields)
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

            for key in ['substance', 'tissue', 'method']:
                if key in attrs:
                    if attrs[key] is not None:
                        attrs[key] = getattr(attrs[key], key)


            attrs["choice"] = attrs["measurement_type"].validate_complete(data=attrs)["choice"]

        except ValueError as err:
            raise serializers.ValidationError(err)

        return super().validate(attrs)

    def _validate_time(self, time):
        if any(np.isnan(np.array(time))):
            raise serializers.ValidationError({"time": "no time points are allowed to be nan", "detail": time})


class TimecourseExSerializer(ExSerializer):

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
        drop_fields = OUTPUT_FIELDS + \
                      OUTPUT_MAP_FIELDS + \
                      EX_MEASUREMENTTYPE_FIELDS + \
                      ["group", "individual", "interventions"] + \
                      ["group_map", "individual_map", "interventions_map"]
        [data.pop(field, None) for field in drop_fields]

        data = self.transform_map_fields(data)
        data["timecourses"] = timecourses


        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def validate_figure(self, value):
        self._validate_figure(value)
        return value

    def create(self, validated_data):
        timecourse_ex, poped_data = _create(
            model_manager=self.Meta.model.objects,
            validated_data=validated_data,
            create_multiple_keys=['comments', 'descriptions'],
            pop=['timecourses']
        )

        timecourses = poped_data["timecourses"]
        for timecourse in timecourses:
            timecourse["study"] = self.context["study"]
        create_multiple(timecourse_ex, timecourses, 'timecourses')

        timecourses_normed = create_multiple_bulk_normalized(timecourse_ex.timecourses.all(), Timecourse)
        if timecourses_normed is not None:
            for timecourse in timecourses_normed:
                timecourse._interventions.add(*timecourse.interventions.all())

                # calculate pharmacokinetics outputs
                outputs = []
                try:
                    outputs = pkoutputs_from_timecourse(timecourse)
                except Exception as e:
                    raise serializers.ValidationError(
                        {"pharmacokinetics exception": traceback.format_exc()}
                    )

                errors = []
                for output in outputs:
                    try:
                        output["measurement_type"].validate_complete(output)
                    except ValueError as err:
                        errors.append(err)
                if errors:
                    raise serializers.ValidationError(
                        {"calculated outputs": errors}
                    )

                outputs_dj = create_multiple_bulk(timecourse, "timecourse", outputs, Output)
                if outputs_dj:
                    outputs_normed = create_multiple_bulk_normalized(outputs_dj, Output)
                    for output in outputs_normed:
                        output._interventions.add(*output.interventions.all())

        timecourse_ex.save()
        return timecourse_ex


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

    def create(self, validated_data):
        pop_keys = ["output_exs", "timecourse_exs"]
        outputset, poped_data = _create(
            model_manager=self.Meta.model.objects,
            validated_data=validated_data,
            create_multiple_keys=['descriptions', 'comments'],
            pop=["output_exs", "timecourse_exs"]
        )

        for k in pop_keys:
            for external_data in poped_data[k]:
                external_data["outputset"] = outputset

        with warnings.catch_warnings(record=True) as ws:
            # warnings come from pharmacokinetics and error_measures
            outputs_exs = []
            for output_ex in poped_data["output_exs"]:
                output_ex_instance, _ = _create(
                    model_serializer=OutputExSerializer(context=self.context),
                    validated_data=output_ex,
                )
                outputs_exs.append(output_ex_instance)
            outputset.output_exs.add(*outputs_exs)
            timecourse_exs = []

            for timecourse_ex in poped_data["timecourse_exs"]:
                timecourse_ex_instance, _ = _create(
                    model_serializer=TimecourseExSerializer(context=self.context),
                    validated_data=timecourse_ex,
                )
                timecourse_exs.append(timecourse_ex_instance)

            outputset.timecourse_exs.add(*timecourse_exs)
            outputset.save()

            # create warning messages
            if len(ws) > 0:

                create_multiple(self.context["study"], [
                    {
                        "text": f"{w.filename}: '{w.message}'"
                    } for w in ws], 'warnings')
        return outputset


# -----------------------
# Elastic Serializer
# -----------------------
class OutputSetElasticSmallSerializer(serializers.ModelSerializer):
    descriptions = DescriptionElasticSerializer(many=True, read_only=True)
    comments = CommentElasticSerializer(many=True, read_only=True)
    outputs = serializers.SerializerMethodField()
    timecourses = serializers.SerializerMethodField()

    class Meta:
        model = OutputSet
        fields = ["pk", "descriptions", "comments", "outputs", "timecourses", ]

        read_only_fields = fields


    def get_outputs(self, obj):
        return list_of_pk("outputs", obj)

    def get_timecourses(self, obj):
        return list_of_pk("timecourses", obj)


class OutputInterventionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutputIntervention
        fields = ["study_sid", "study_name", "output_pk", "intervention_pk", "group_pk", "individual_pk", "normed",
                  "calculated"] + OUTPUT_FIELDS + MEASUREMENTTYPE_FIELDS

        read_only_fields = fields


class TimecourseInterventionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimecourseIntervention
        fields = ["study_sid", "study_name", "timecourse_pk", "intervention_pk", "group_pk", "individual_pk",
                  "normed"] + OUTPUT_FIELDS + MEASUREMENTTYPE_FIELDS
        read_only_fields = fields


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
    study = StudySmallElasticSerializer()

    group = GroupSmallElasticSerializer()
    individual = IndividualSmallElasticSerializer()
    interventions = InterventionSmallElasticSerializer(many=True)

    substance = SidNameSerializer( allow_null=True)
    measurement_type = SidNameSerializer( allow_null=True)
    tissue = SidNameSerializer( allow_null=True)
    method = SidNameSerializer( allow_null=True)
    choice = SidNameSerializer( allow_null=True)

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
                + EXTRA_FIELDS
                + ["study"]
                + ["group", "individual", "interventions"]
                + MEASUREMENTTYPE_FIELDS
                + TIME_FIELDS
                + VALUE_FIELDS
        )
        read_only_fields = fields



class TimecourseElasticSerializer(serializers.ModelSerializer):
    study = StudySmallElasticSerializer()
    group = GroupSmallElasticSerializer()
    individual = IndividualSmallElasticSerializer()
    interventions = InterventionSmallElasticSerializer(many=True)

    outputs = PkSerializer(many=True)

    substance = SidNameSerializer( allow_null=True)
    measurement_type = SidNameSerializer( allow_null=True)
    tissue = SidNameSerializer( allow_null=True)
    method = SidNameSerializer( allow_null=True)
    choice = SidNameSerializer(allow_null=True)

    class Meta:
        model = Timecourse
        fields = (
                ["pk", "normed", "outputs"]
                + EXTRA_FIELDS
                + ["study"]
                + ["group", "individual", "interventions"]
                + MEASUREMENTTYPE_FIELDS
                + TIME_FIELDS
                + VALUE_FIELDS
        )
        read_only_fields = fields


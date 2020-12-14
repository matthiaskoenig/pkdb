"""
Serializers for outputs.
"""

import warnings

from rest_framework import serializers

from pkdb_app import utils
from pkdb_app.behaviours import MEASUREMENTTYPE_FIELDS, EX_MEASUREMENTTYPE_FIELDS, VALUE_FIELDS, map_field
from pkdb_app.info_nodes.models import InfoNode
from pkdb_app.info_nodes.serializers import MeasurementTypeableSerializer
from pkdb_app.interventions.serializers import InterventionSmallElasticSerializer
from .models import (
    Output,
    OutputSet,
    OutputEx)
from ..comments.serializers import DescriptionSerializer, CommentSerializer, DescriptionElasticSerializer, \
    CommentElasticSerializer
from ..interventions.models import Intervention
from ..serializers import (
    ExSerializer, StudySmallElasticSerializer, SidNameLabelSerializer)
from ..subjects.models import Group, DataFile, Individual
from ..subjects.serializers import (
    EXTERN_FILE_FIELDS, GroupSmallElasticSerializer, IndividualSmallElasticSerializer)
# ----------------------------------
# Serializer FIELDS
# ----------------------------------
from ..utils import list_of_pk, _validate_required_key, create_multiple, _create, create_multiple_bulk_normalized, \
    create_multiple_bulk

EXTRA_FIELDS = ["tissue", "method", "label", "output_type"]
TIME_FIELDS = ["time", "time_unit"]
OUTPUT_FIELDS = EXTRA_FIELDS + TIME_FIELDS

OUTPUT_MAP_FIELDS = map_field(OUTPUT_FIELDS)
OUTPUT_FOREIGN_KEYS = [
            'measurement_type',
            'substance',
            'choice',
            'raw',
            'group',
            'individual',
            'tissue',
            'method',
            'ex',
            'study'
        ]

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
        required=False,
        allow_null=True,
    )

    method = utils.SlugRelatedField(
        slug_field="name",
        queryset=InfoNode.objects.filter(ntype=InfoNode.NTypes.Method),
        read_only=False,
        required=False
    )

    class Meta:
        model = Output
        fields = OUTPUT_FIELDS + ['label'] + MEASUREMENTTYPE_FIELDS + ["group", "individual", "interventions"]

    def to_internal_value(self, data):
        data.pop("comments", None)
        data.pop("descriptions", None)

        data = self.retransform_map_fields(data)
        data = self.to_internal_related_fields(data)
        self.validate_wrong_keys(data, additional_fields=OutputExSerializer.Meta.fields)
        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def validate(self, attrs):
        self._validate_individual_output(attrs)
        self._validate_group_output(attrs)
        self.validate_group_individual_output(attrs)

        _validate_required_key(attrs, "measurement_type")

        _validate_required_key(attrs, "substance")
        _validate_required_key(attrs, "tissue")
        _validate_required_key(attrs, "interventions")
        _validate_required_key(attrs, "output_type")
        self._validate_timecourse(attrs)



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

    def _validate_timecourse(self, attrs):
        if attrs["output_type"] == Output.OutputTypes.Timecourse:
            _validate_required_key(attrs, "label")
            if not attrs.get("label",None):
                msg = "Label is required on on output_type=timecourse"
                raise serializers.ValidationError(msg)


class OutputExSerializer(ExSerializer):

    source = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )

    image = serializers.PrimaryKeyRelatedField(
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

        drop_fields = OUTPUT_FIELDS + \
                      OUTPUT_MAP_FIELDS + \
                      EX_MEASUREMENTTYPE_FIELDS+ \
                      ["group", "individual", "interventions"] + \
                      ["group_map", "individual_map", "interventions_map"]

        # label validation
        label = data.pop("label", None)
        self.validate_label_map(label)

        [data.pop(field, None) for field in drop_fields]
        data["outputs"] = outputs
        data = self.transform_map_fields(data)
        self.validate_wrong_keys(data, OutputSerializer.Meta.fields)
        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def validate_label_map(self, value) -> None:
        """Validate the label key."""
        if isinstance(value, str):
            if not value.startswith("col==") and "||" not in value:
                msg = f"The 'label' must be a mapping start with 'col==' or contain a split '||', but label is '{value}'"
                raise serializers.ValidationError(msg)

    def validate_image(self, value):
        self._validate_image(value)
        return value

    def create(self, validated_data):
        output_ex, poped_data = _create(
            model_manager=self.Meta.model.objects,
            validated_data=validated_data,
            create_multiple_keys=['comments', 'descriptions'],
            pop=['outputs']
        )

        outputs = poped_data["outputs"]
        outputs_interventions = []
        for output in outputs:
            output["study"] = self.context["study"]
            outputs_interventions.append(output.pop('interventions', []))

        outputs_dj = create_multiple_bulk(output_ex, 'ex', outputs, Output)
        for output, interventions in zip(outputs_dj, outputs_interventions):
            output.interventions.add(*interventions)

        outputs_normed = create_multiple_bulk_normalized(outputs_dj, Output)
        for output in outputs_normed:
            output.interventions.add(*output.raw.interventions.all())

        return output_ex


class OutputSetSerializer(ExSerializer):
    """
    OutputSet
    """
    output_exs = OutputExSerializer(
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
        fields = ["descriptions", "comments", "output_exs"]

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        self.validate_wrong_keys(data)
        return data

    def create(self, validated_data):
        pop_keys = ["output_exs"]
        outputset, poped_data = _create(
            model_manager=self.Meta.model.objects,
            validated_data=validated_data,
            create_multiple_keys=['descriptions', 'comments'],
            pop=pop_keys
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

    class Meta:
        model = OutputSet
        fields = ["pk", "descriptions", "comments", "outputs"]

        read_only_fields = fields

    def get_outputs(self, obj):
        return list_of_pk("outputs", obj)


class OutputInterventionSerializer(serializers.Serializer):
    study_sid = serializers.CharField()
    study_name = serializers.CharField()
    output_pk = serializers.IntegerField()
    intervention_pk = serializers.IntegerField()
    group_pk = serializers.IntegerField()
    individual_pk = serializers.IntegerField()
    normed = serializers.BooleanField()
    calculated = serializers.BooleanField()

    tissue = serializers.CharField()
    tissue_label = serializers.CharField()

    method = serializers.CharField()
    method_label = serializers.CharField()

    label = serializers.CharField()
    output_type = serializers.CharField()

    time = serializers.FloatField()
    time_unit = serializers.CharField()

    measurement_type = serializers.CharField()
    measurement_type_label = serializers.CharField()

    choice = serializers.CharField()
    choice_label = serializers.CharField()

    substance = serializers.CharField()
    substance_label = serializers.CharField()


    value = serializers.FloatField()
    mean = serializers.FloatField()
    median = serializers.FloatField()
    min = serializers.FloatField()
    max = serializers.FloatField()
    sd = serializers.FloatField()
    se = serializers.FloatField()
    cv = serializers.FloatField()
    unit = serializers.CharField()


    class Meta:
        fields = ["study_sid", "study_name", "output_pk", "intervention_pk", "group_pk", "individual_pk", "normed",
                  "calculated"] + OUTPUT_FIELDS + MEASUREMENTTYPE_FIELDS


class SmallOutputSerializer(serializers.ModelSerializer):
    group = GroupSmallElasticSerializer()
    individual = IndividualSmallElasticSerializer()
    interventions = InterventionSmallElasticSerializer(many=True)

    substance = SidNameLabelSerializer(allow_null=True)
    measurement_type = SidNameLabelSerializer(allow_null=True)
    tissue = SidNameLabelSerializer(allow_null=True)
    method = SidNameLabelSerializer(allow_null=True)
    choice = SidNameLabelSerializer(allow_null=True)

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
                ["pk", "normed"]
                + EXTRA_FIELDS
                + ["group", "individual", "interventions"]
                + MEASUREMENTTYPE_FIELDS
                + TIME_FIELDS
                + VALUE_FIELDS
        )
        read_only_fields = fields


class OutputElasticSerializer(serializers.ModelSerializer):
    """Main serializer for outputs."""
    study = StudySmallElasticSerializer()

    group = GroupSmallElasticSerializer()
    individual = IndividualSmallElasticSerializer()
    interventions = InterventionSmallElasticSerializer(many=True)

    substance = SidNameLabelSerializer(allow_null=True)
    measurement_type = SidNameLabelSerializer(allow_null=True)
    tissue = SidNameLabelSerializer(allow_null=True)
    method = SidNameLabelSerializer(allow_null=True)
    choice = SidNameLabelSerializer(allow_null=True)

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
                ["pk", "normed", "calculated"]
                + EXTRA_FIELDS
                + ["study"]
                + ["group", "individual", "interventions"]
                + MEASUREMENTTYPE_FIELDS
                + TIME_FIELDS
                + VALUE_FIELDS
        )
        read_only_fields = fields


"""
Serializers for interventions.
"""
import pandas as pd

import numpy as np
from rest_framework import serializers

from pkdb_app.comments.serializers import DescriptionSerializer, CommentSerializer
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
)

from pkdb_app.subjects.models import Group, DataFile, Individual
from pkdb_app.categoricals import validate_categorials

from pkdb_app.subjects.serializers import (
    VALUE_MAP_FIELDS,
    VALUE_FIELDS,
    EXTERN_FILE_FIELDS,
)

# ----------------------------------
# Serializer FIELDS
# ----------------------------------
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

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        self.validate_wrong_keys(data)
        return data


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
        temp_interventions = self.split_entry(data)
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
        self._validate_requried_key(attrs,"tissue")

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
            timecourses.append(timecourses_from_file)
        # ----------------------------------
        # finished
        # ----------------------------------
        data = self.transform_map_fields(data)

        data["timecourses"] = timecourses
        data = self.to_internal_related_fields(data)
        self.validate_wrong_keys(data)
        return super(serializers.ModelSerializer, self).to_internal_value(data)


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
        data = super().to_internal_value(data)
        self.validate_wrong_keys(data)
        return data

    def validate(self, attrs):
        return super().validate(attrs)


###############################################################################################
# Read Serializer
###############################################################################################
class InterventionSetReadSerializer(serializers.HyperlinkedModelSerializer):
    """ InterventionSet. """

    study = serializers.HyperlinkedRelatedField(
        lookup_field="sid", read_only=True, view_name="studies_read-detail"
    )
    descriptions = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="descriptions_read-detail"
    )
    interventions = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="interventions_read-detail"
    )
    intervention_exs = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="interventionexs_read-detail"
    )
    comments = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="comments_read-detail"
    )


    class Meta:
        model = InterventionSet
        fields = ["pk", "study", "descriptions","comments", "interventions", "intervention_exs"]

class InterventionExReadSerializer(ExSerializer,serializers.HyperlinkedModelSerializer):
    interventionset = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="interventionsets_read-detail"
    )
    substance = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="substances_read-detail"
    )

    source = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="datafiles_read-detail"
    )

    figure = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="datafiles_read-detail"
    )
    comments = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="comments_read-detail"
    )

    interventions = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True, view_name="interventions_read-detail"
    )

    class Meta:
        model = InterventionEx
        fields = (
            ["pk", "interventionset"] +
            EXTERN_FILE_FIELDS
            + VALUE_MAP_FIELDS
            + VALUE_FIELDS
            + INTERVENTION_FIELDS
            + INTERVENTION_MAP_FIELDS
            + ["interventions", "comments"]
        )
    def to_representation(self, instance):
        rep =  super(serializers.HyperlinkedModelSerializer,self).to_representation(instance)
        #rep = self.retransform_map_fields(rep)
        return rep



class InterventionReadSerializer(serializers.HyperlinkedModelSerializer):
    """ Intervention. """

    interventionset = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="interventionsets_read-detail"
    )
    substance = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="substances_read-detail"
    )
    ex = serializers.HyperlinkedRelatedField(read_only=True, view_name="interventionexs_read-detail"
                                             )

    class Meta:
        model = Intervention
        fields = ["pk", "interventionset","ex"] + VALUE_FIELDS + INTERVENTION_FIELDS


class OutputSetReadSerializer(serializers.HyperlinkedModelSerializer):
    """ OuputSet. """

    study = serializers.HyperlinkedRelatedField(
        lookup_field="sid", read_only=True, view_name="studies_read-detail"
    )
    descriptions = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="descriptions_read-detail"
    )
    outputs = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="outputs_read-detail"
    )
    output_exs = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="outputexs_read-detail"
    )
    timecourses = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="timecourses_read-detail"
    )
    timecourse_exs = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="timecourseexs_read-detail"
    )
    comments = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="comments_read-detail"
    )

    class Meta:
        model = OutputSet
        fields = ["pk", "study", "descriptions","comments", "outputs","output_exs", "timecourses","timecourse_exs"]


class OutputReadSerializer(serializers.HyperlinkedModelSerializer):
    """ Output. """

    outputset = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="outputsets_read-detail"
    )
    group = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="groups_read-detail"
    )
    ex = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="outputexs_read-detail"
    )
    individual = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="individuals_read-detail"
    )
    interventions = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="interventions_read-detail"
    )
    substance = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="substances_read-detail"
    )

    class Meta:
        model = Output
        fields = (
            ["pk", "outputset","ex"]
            + OUTPUT_FIELDS
            + VALUE_FIELDS
            + ["group", "individual", "interventions"]
        )
class OutputExReadSerializer(OutputReadSerializer):
    """ Output. """
    outputs = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="outputs_read-detail"
    )
    source = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="datafiles_read-detail"
    )

    figure = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="datafiles_read-detail"
    )
    comments = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="comments_read-detail"
    )
    class Meta:
        model = OutputEx
        fields = (
            ["pk", "outputset"]
            + EXTERN_FILE_FIELDS
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

class TimecourseReadSerializer(serializers.HyperlinkedModelSerializer):
    """ Timecourse. """
    ex = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="timecourseexs_read-detail"
    )
    outputset = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="outputsets_read-detail"
    )
    group = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="groups_read-detail"
    )
    individual = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="individuals_read-detail"
    )
    interventions = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="interventions_read-detail"
    )
    substance = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="substances_read-detail"
    )

    class Meta:
        model = Timecourse
        fields = (
            ["pk", "outputset","ex"]
            + OUTPUT_FIELDS
            + VALUE_FIELDS
            + ["group", "individual", "interventions"]
        )

    def _any_not_json(self, value):
        return any([np.isnan(value), np.isinf(value), np.isneginf(value)])

    def to_representation(self, instance):
        array_fields = [
            "value",
            "mean",
            "median",
            "min",
            "max",
            "sd",
            "se",
            "cv",
            "time",
        ]
        for field in array_fields:
            array = getattr(instance, field, None)
            if array:
                null_array = [ None if self._any_not_json(value) else value for value in array ]
                setattr(instance, field, null_array)
        return super().to_representation(instance)

class TimecourseExReadSerializer(TimecourseReadSerializer):
    timecourses = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="timecourses_read-detail"
    )

    source = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="datafiles_read-detail"
    )

    figure = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="datafiles_read-detail"
    )
    comments = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="comments_read-detail"
    )

    class Meta:
        model = TimecourseEx
        fields = (
            ["pk", "outputset"]
            + EXTERN_FILE_FIELDS
            + OUTPUT_FIELDS
            + OUTPUT_MAP_FIELDS
            + VALUE_FIELDS
            + VALUE_MAP_FIELDS
            + ["group", "individual", "interventions"]
            + [
                "group_map",
                "individual_map",
                "interventions_map",
                "timecourses",
                "comments",
            ]
        )
    def to_representation(self, instance):
        return super(serializers.HyperlinkedModelSerializer,self).to_representation(instance)


class SubstanceReadSerializer(serializers.HyperlinkedModelSerializer):
    """ Substance. """

    class Meta:
        model = Substance
        fields = ["pk", "name"]

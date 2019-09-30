"""
Serializers for interventions.
"""
import numpy as np

from pkdb_app import utils
from pkdb_app.categorials.behaviours import MEASUREMENTTYPE_FIELDS, EX_MEASUREMENTTYPE_FIELDS, VALUE_FIELDS, \
    VALUE_FIELDS_NO_UNIT, map_field
from pkdb_app.categorials.serializers import MeasurementTypeableSerializer
from pkdb_app.interventions.serializers import InterventionSmallElasticSerializer
from rest_framework import serializers

from pkdb_app.categorials.models import MeasurementType

from pkdb_app.users.serializers import UserElasticSerializer
from ..comments.serializers import DescriptionSerializer, CommentSerializer, DescriptionElasticSerializer, \
    CommentElasticSerializer

from ..interventions.models import Intervention
from ..substances.models import Substance
from ..subjects.models import Group, DataFile, Individual


from .models import (
    Output,
    OutputSet,
    Timecourse,
    OutputEx,
    TimecourseEx)

from ..serializers import (
    ExSerializer, PkSerializer)

from ..subjects.serializers import (
    EXTERN_FILE_FIELDS, GroupSmallElasticSerializer, IndividualSmallElasticSerializer)

# ----------------------------------
# Serializer FIELDS
# ----------------------------------
from ..utils import list_of_pk, _validate_requried_key



OUTPUT_FIELDS = ["tissue",  "time", "time_unit"]

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



    class Meta:
        model = Output
        fields = OUTPUT_FIELDS + MEASUREMENTTYPE_FIELDS + ["group", "individual", "interventions"]

    def to_internal_value(self, data):
        data.pop("comments", None)
        data = self.retransform_map_fields(data)
        data = self.to_internal_related_fields(data)
        self.validate_wrong_keys(data)
        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def validate(self, attrs):
        self._validate_individual_output(attrs)
        self._validate_group_output(attrs)
        self.validate_group_individual_output(attrs)

        _validate_requried_key(attrs,"measurement_type")
        _validate_requried_key(attrs, "substance")
        _validate_requried_key(attrs, "tissue")
        _validate_requried_key(attrs, "interventions")

        try:
            # perform via dedicated function on categorials
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
        queryset=Substance.objects.all(),
        read_only=False,
        required=False,
        allow_null=True,
    )

    measurement_type = utils.SlugRelatedField(
        slug_field="name",
        queryset=MeasurementType.objects.all(),
        read_only=False,
        required=False
    )


    class Meta:
        model = Timecourse
        fields = OUTPUT_FIELDS + MEASUREMENTTYPE_FIELDS + ["group", "individual", "interventions"]

    def to_internal_value(self, data):
        data.pop("comments", None)
        data = self.to_internal_related_fields(data)
        self.validate_wrong_keys(data)
        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def validate(self, attrs):
        self._validate_individual_output(attrs)
        self._validate_group_output(attrs)
        self.validate_group_individual_output(attrs)

        _validate_requried_key(attrs,"substance")
        _validate_requried_key(attrs,"interventions")
        _validate_requried_key(attrs,"tissue")
        _validate_requried_key(attrs,"time")
        _validate_requried_key(attrs,"measurement_type")

        self._validate_time_unit(attrs)
        self._validate_time(attrs["time"])

        try:
            # perform via dedicated function on categorials
            attrs["measurement_type"].validate_complete(data=attrs)
        except ValueError as err:
            raise serializers.ValidationError(err)

        return super().validate(attrs)

    def _validate_time(self,time):
        if any(np.isnan(np.array(time))):
            raise serializers.ValidationError({"time":"no timepoints are allowed to be nan", "detail":time})




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
            + ["timecourses", "comments"]
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
    substance = serializers.CharField()
    measurement_type = serializers.CharField()

    value = serializers.FloatField(allow_null=True)
    mean = serializers.FloatField(allow_null=True)
    median = serializers.FloatField(allow_null=True)
    min = serializers.FloatField(allow_null=True)
    max = serializers.FloatField(allow_null=True)
    sd = serializers.FloatField(allow_null=True)
    se = serializers.FloatField(allow_null=True)
    cv = serializers.FloatField(allow_null=True)

    raw = PkSerializer()
    timecourse = PkSerializer()
    allowed_users = UserElasticSerializer(many=True, read_only=True)


    class Meta:
            model = Output
            fields = (
                ["pk","study"]
                + OUTPUT_FIELDS
                + VALUE_FIELDS
                + MEASUREMENTTYPE_FIELDS
                + ["access", "allowed_users"]
                + ["group", "individual", "normed", "raw", "calculated", "timecourse", "interventions"])



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
    measurement_type = serializers.CharField()
    raw = PkSerializer()
    pharmacokinetics = PkSerializer(many=True)
    substance = serializers.CharField()

    allowed_users = UserElasticSerializer(many=True, read_only=True)

    class Meta:
            model = Timecourse
            fields = (
                ["pk","study"]
                + MEASUREMENTTYPE_FIELDS
                + OUTPUT_FIELDS
                + VALUE_FIELDS
                +["access","allowed_users"]
                + ["group", "individual", "normed","raw","pharmacokinetics", "interventions","figure"])


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

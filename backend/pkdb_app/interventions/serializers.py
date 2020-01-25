"""
Serializers for interventions.
"""
import itertools

from rest_framework import serializers

from pkdb_app import utils
from pkdb_app.behaviours import VALUE_FIELDS_NO_UNIT, \
    MEASUREMENTTYPE_FIELDS, map_field, EX_MEASUREMENTTYPE_FIELDS
from pkdb_app.info_nodes.models import InfoNode
from pkdb_app.info_nodes.serializers import MeasurementTypeableSerializer, EXMeasurementTypeableSerializer
from pkdb_app.subjects.serializers import EXTERN_FILE_FIELDS
from ..comments.serializers import DescriptionSerializer, CommentSerializer, DescriptionElasticSerializer, \
    CommentElasticSerializer
from ..interventions.models import (
    InterventionSet,
    Intervention,
    InterventionEx)
from ..serializers import (
    ExSerializer,
    NA_VALUES, StudySmallElasticSerializer)
from ..subjects.models import DataFile
# ----------------------------------
# Serializer FIELDS
# ----------------------------------
from ..utils import list_of_pk, list_duplicates, _validate_requried_key

MEDICATION = "medication"
DOSING = "dosing"

INTERVENTION_FIELDS = [
    "name",
    "route",
    "form",
    "application",
    "time",
    "time_end",
    "time_unit",
]

INTERVENTION_MAP_FIELDS = map_field(INTERVENTION_FIELDS)

OUTPUT_FIELDS = ["tissue", "time", "time_unit"]

OUTPUT_MAP_FIELDS = map_field(OUTPUT_FIELDS)


# ----------------------------------
# Interventions
# ----------------------------------


class InterventionSerializer(MeasurementTypeableSerializer):
    route = utils.SlugRelatedField(
        slug_field="name",
        required=False,
        queryset=InfoNode.objects.filter(ntype=InfoNode.NTypes.Route))

    application = utils.SlugRelatedField(
        slug_field="name",
        required=False,
        queryset=InfoNode.objects.filter(ntype=InfoNode.NTypes.Application))

    form = utils.SlugRelatedField(
        slug_field="name",
        required=False,
        queryset=InfoNode.objects.filter(ntype=InfoNode.NTypes.Form))

    class Meta:
        model = Intervention
        fields = INTERVENTION_FIELDS + MEASUREMENTTYPE_FIELDS

    def to_internal_value(self, data):
        data.pop("comments", None)
        data.pop("descriptions", None)

        data = self.retransform_map_fields(data)
        data = self.retransform_ex_fields(data)
        self.validate_wrong_keys(data)

        _validate_requried_key(data, "measurement_type")
        measurement_type = data.get("measurement_type")

        if any([measurement_type == MEDICATION, measurement_type == DOSING]):
            _validate_requried_key(data, "substance")
            _validate_requried_key(data, "route")
            _validate_requried_key(data, "value")
            _validate_requried_key(data, "unit")

            if measurement_type == DOSING:
                _validate_requried_key(data, "form")
                _validate_requried_key(data, "application")
                _validate_requried_key(data, "time")
                _validate_requried_key(data, "time_unit")
                application = data["application"]
                allowed_applications = ["constant infusion", "single dose"]
                if not application in allowed_applications:
                    raise serializers.ValidationError(
                        f"Allowed applications for measurement_type <{DOSING}> are <{allowed_applications}>.You might want to select the measurement_type: qualitative dosing. With no requirements.")

        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def validate(self, attrs):
        try:
            # perform via dedicated function on categorials
            for info_node in ['substance', 'measurement_type', 'form', 'application', 'route']:
                if info_node in attrs:
                    attrs[info_node] = getattr(attrs[info_node],info_node )

            attrs["measurement_type"].validate_complete(data=attrs)

        except ValueError as err:
            raise serializers.ValidationError(err)

        return super().validate(attrs)


class InterventionExSerializer(EXMeasurementTypeableSerializer):
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
    descriptions = DescriptionSerializer(
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
                + INTERVENTION_FIELDS
                + INTERVENTION_MAP_FIELDS
                + EX_MEASUREMENTTYPE_FIELDS
                + ["interventions", "comments", "descriptions"]
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

    def validate(self, attrs):
        intervention_exs = attrs.get("intervention_exs")
        all_interventions = list(
            itertools.chain(*[intervention_ex.get("interventions") for intervention_ex in intervention_exs]))
        all_intervention_names = [intervention["name"] for intervention in all_interventions]

        duplicated_intervention_names = list_duplicates(all_intervention_names)
        if duplicated_intervention_names:
            raise serializers.ValidationError(
                {
                    "intervention_set": "Itervention names are required to be unique within a study.",
                    "duplicated intervention names": duplicated_intervention_names
                })

        return super().validate(attrs)


###############################################################################################
# Elastic Serializer
###############################################################################################


class InterventionSetElasticSmallSerializer(serializers.ModelSerializer):
    descriptions = DescriptionElasticSerializer(many=True, read_only=True)
    comments = CommentElasticSerializer(many=True, read_only=True)
    interventions = serializers.SerializerMethodField()

    class Meta:
        model = InterventionSet
        fields = ["pk", "descriptions", "comments", "interventions", ]

    def get_interventions(self, obj):
        return list_of_pk("interventions", obj)


# Intervention related Serializer
class InterventionSmallElasticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Intervention
        fields = ["pk", 'name']  # , 'url']


class InterventionElasticSerializer(serializers.ModelSerializer):
    pk = serializers.IntegerField()
    study = StudySmallElasticSerializer(read_only=True)
    measurement_type = serializers.CharField()
    route = serializers.CharField()
    application = serializers.CharField()
    form = serializers.CharField()
    value = serializers.FloatField(allow_null=True)
    mean = serializers.FloatField(allow_null=True)
    median = serializers.FloatField(allow_null=True)
    min = serializers.FloatField(allow_null=True)
    max = serializers.FloatField(allow_null=True)
    sd = serializers.FloatField(allow_null=True)
    se = serializers.FloatField(allow_null=True)
    cv = serializers.FloatField(allow_null=True)
    substance = serializers.CharField(allow_null=True)

    class Meta:
        model = Intervention
        fields = ["pk", "normed"] + INTERVENTION_FIELDS + ["study"] + MEASUREMENTTYPE_FIELDS


class InterventionElasticSerializerAnalysis(serializers.ModelSerializer):
    intervention_pk = serializers.IntegerField(source="pk")
    substance = serializers.CharField(allow_null=True)
    measurement_type = serializers.CharField()
    route = serializers.CharField()
    application = serializers.CharField()
    form = serializers.CharField()
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
        fields = ["study_sid", "study_name", "intervention_pk", "raw_pk",
                  "normed"] + INTERVENTION_FIELDS + MEASUREMENTTYPE_FIELDS

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        for field in VALUE_FIELDS_NO_UNIT + ["time"]:
            try:
                rep[field] = '{:.2e}'.format(rep[field])
            except (ValueError, TypeError):
                pass
        return rep

"""
Serializers for interventions.
"""

from rest_framework import serializers

from ..comments.serializers import DescriptionSerializer, CommentSerializer, DescriptionElasticSerializer, \
    CommentElasticSerializer


from ..interventions.models import (
    Substance,
    InterventionSet,
    Intervention,
    InterventionEx)

from ..serializers import (
    ExSerializer,
    NA_VALUES, PkSerializer)

from ..subjects.models import  DataFile
from pkdb_app.categorials.models import validate_categorials, InterventionType

from ..subjects.serializers import (
    VALUE_MAP_FIELDS,
    VALUE_FIELDS,
    EXTERN_FILE_FIELDS, VALUE_FIELDS_NO_UNIT)





# ----------------------------------
# Serializer FIELDS
# ----------------------------------
from ..utils import list_of_pk

MEDICATION = "medication"
DOSING = "dosing"


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
# Interventions
# ----------------------------------
class InterventionSerializer(ExSerializer):
    category = serializers.SlugRelatedField(slug_field="key", queryset=InterventionType.objects.all())

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

        if any([category == MEDICATION,category == DOSING]):
            self._validate_requried_key(data,"substance")
            self._validate_requried_key(data,"route")
            self._validate_requried_key(data,"value")
            self._validate_requried_key(data,"unit")

            if category == DOSING:
                self._validate_requried_key(data, "form")
                self._validate_requried_key(data, "application")
                self._validate_requried_key(data,"time")
                self._validate_requried_key(data,"time_unit")
                application = data["application"]
                allowed_applications = ["constant infusion","single dose"]
                if not application in allowed_applications:
                    raise serializers.ValidationError(f"Allowed applications for category <{DOSING}> are <{allowed_applications}>.You might want to select the category: qualitative dosing. With no requirements.")

        return super(serializers.ModelSerializer, self).to_internal_value(data)

    def validate(self, attrs):
        try:
            # perform via dedicated function on categorials
            validate_categorials(data=attrs)
        except ValueError as err:
            raise serializers.ValidationError(err)

        return super().validate(attrs)


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
    raw = PkSerializer()
    class Meta:
        model = Intervention
        fields = ["pk","study", "normed", "raw"] + VALUE_FIELDS + INTERVENTION_FIELDS

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

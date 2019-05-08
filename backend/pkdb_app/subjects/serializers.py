from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from pkdb_app.categorials.models import validate_categorials, CharacteristicType
from rest_framework import serializers
from ..comments.serializers import DescriptionSerializer, CommentSerializer, DescriptionElasticSerializer, \
    CommentElasticSerializer
from ..studies.models import Study
from operator import itemgetter
from django.shortcuts import get_object_or_404
from ..utils import list_of_pk

from .models import (
    Group,
    GroupSet,
    IndividualEx,
    IndividualSet,
    Characteristica,
    DataFile,
    Individual,
    CharacteristicaEx,
    GroupEx,
)
from ..serializers import WrongKeyValidationSerializer, MappingSerializer, ExSerializer, ReadSerializer

EXTERN_FILE_FIELDS = ["source", "format", "subset_map","groupby", "figure"]
VALUE_FIELDS_NO_UNIT = ["value", "mean", "median", "min", "max", "sd", "se", "cv"]
VALUE_FIELDS = VALUE_FIELDS_NO_UNIT +  ["unit"]

VALUE_MAP_FIELDS = [
    "value_map",
    "mean_map",
    "median_map",
    "min_map",
    "max_map",
    "sd_map",
    "se_map",
    "cv_map",
    "unit_map",
]
CHARACTERISTISTA_FIELDS = ["count", "category", "choice"]
CHARACTERISTISTA_MAP_FIELDS = ["count_map", "choice_map"]
GROUP_FIELDS = ["name", "count"]
GROUP_MAP_FIELDS = ["name_map", "count_map"]


# ----------------------------------
# DataFile
# ----------------------------------
class DataFileSerializer(WrongKeyValidationSerializer):
    class Meta:
        model = DataFile
        fields = ["file", "filetype", "id"]
        extra_kwargs = {"id": {"allow_null": False}}

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        self.validate_wrong_keys(data)
        return data


# ----------------------------------
# Characteristica
# ----------------------------------
class CharacteristicaExSerializer(MappingSerializer):
    count = serializers.IntegerField(required=False)
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )


    class Meta:
        model = CharacteristicaEx
        fields = (
            CHARACTERISTISTA_FIELDS
            + CHARACTERISTISTA_MAP_FIELDS
            + VALUE_FIELDS
            + VALUE_MAP_FIELDS
            + ["comments"]
        )


    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        self.validate_wrong_keys(data)
        return data


class CharacteristicaSerializer(ExSerializer):
    count = serializers.IntegerField(required=False)
    category = serializers.SlugRelatedField(slug_field="key", queryset=CharacteristicType.objects.all())

    class Meta:
        model = Characteristica
        fields = CHARACTERISTISTA_FIELDS + VALUE_FIELDS

    def to_internal_value(self, data):
        data.pop("comments", None)
        self._is_required(data,"category")
        data.get("category")
        self.validate_wrong_keys(data)
        return super(serializers.ModelSerializer,self).to_internal_value(data)

    def validate(self, attr):
        try:
            # perform via dedicated function on categorials
            validate_categorials(data=attr)
        except ValueError as err:
            raise serializers.ValidationError(err)

        return super().validate(attr)


# ----------------------------------
# Group
# ----------------------------------
class GroupSerializer(ExSerializer):
    characteristica = CharacteristicaSerializer(
        many=True, read_only=False, required=False
    )
    parent = serializers.CharField()

    class Meta:
        model = Group
        fields = GROUP_FIELDS + ["parent", "characteristica"]

    def to_internal_value(self, data):
        data.pop("comments", None)
        data = self.retransform_map_fields(data)
        data = self.retransform_ex_fields(data)
        self.validate_wrong_keys(data)

        for characteristica_single in data.get("characteristica",[]):
            disabled = ["value"]
            self._validate_disabled_data(characteristica_single, disabled)

        return super(serializers.ModelSerializer, self).to_internal_value(data)


class GroupExSerializer(ExSerializer):
    characteristica_ex = CharacteristicaExSerializer(
        many=True, read_only=False, required=False
    )
    source = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )
    figure = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )
    parent_ex = serializers.CharField()
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    # internal data
    groups = GroupSerializer(
        many=True, write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = GroupEx
        fields = (
            EXTERN_FILE_FIELDS
            + GROUP_FIELDS
            + GROUP_MAP_FIELDS
            + ["parent_ex", "characteristica_ex", "groups", "comments"]
        )

    def to_internal_value(self, data):

        # ----------------------------------
        # decompress external format
        # ----------------------------------
        temp_groups = self.split_entry(data)
        groups = []
        for group in temp_groups:
            characteristica = group.get("characteristica")
            if characteristica:
                temp_characteristica = []
                for characteristica_single in characteristica:
                    temp_characteristica.extend(
                        self.split_entry(characteristica_single)
                    )
                group["characteristica"] = temp_characteristica

            groups_from_file = self.entries_from_file(group)
            groups.extend(groups_from_file)

        data = self.transform_ex_fields(data)
        data = self.transform_map_fields(data)

        data["groups"] = groups

        # ----------------------------------
        # finished
        # ----------------------------------

        self.validate_wrong_keys(data)
        return super(WrongKeyValidationSerializer, self).to_internal_value(data)


class GroupSetSerializer(ExSerializer):
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    group_exs = GroupExSerializer(many=True, read_only=False)
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    class Meta:
        model = GroupSet
        fields = ["descriptions", "group_exs", "comments"]

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        self.validate_wrong_keys(data)
        return data


# ----------------------------------
# Individual
# ----------------------------------
class IndividualSerializer(ExSerializer):
    name = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all())
    characteristica = CharacteristicaSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    class Meta:
        model = Individual
        fields = ["name", "group", "characteristica"]

    @staticmethod
    def group_to_internal_value(group, study_sid):
        if group:
            try:
                group = Group.objects.get(
                    Q(ex__groupset__study__sid=study_sid) & Q(name=group)
                ).pk
            except ObjectDoesNotExist:
                msg = f"group: {group} in study: {study_sid} does not exist"
                raise serializers.ValidationError(msg)
        else:
            msg = {"group": f"group is required on individual", "detail": group}
            raise serializers.ValidationError(msg)
        return group

    def to_internal_value(self, data):
        data.pop("comments", None)
        study_sid = self.context["request"].path.split("/")[-2]
        if "group" in data:
            data["group"] = self.group_to_internal_value(data["group"], study_sid)

        data = self.retransform_map_fields(data)
        data = self.retransform_ex_fields(data)
        self.validate_wrong_keys(data)

        for characteristica_single in data.get("characteristica",[]):
            disabled = ["mean", "median", "sd", "se", "cv"]
            self._validate_disabled_data(characteristica_single, disabled)


        return super(serializers.ModelSerializer, self).to_internal_value(data)


class IndividualExSerializer(ExSerializer):
    characteristica_ex = CharacteristicaExSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    group = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), required=False, allow_null=True
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
    individuals = IndividualSerializer(
        many=True, write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = IndividualEx
        fields = EXTERN_FILE_FIELDS + [
            "name",
            "name_map",
            "group",
            "group_map",
            "characteristica_ex",
            "individuals",
            "comments",
        ]

    @staticmethod
    def group_to_internal_value(group, study_sid):
        if group:
            try:
                group = Group.objects.get(
                    Q(ex__groupset__study__sid=study_sid) & Q(name=group)
                ).pk
            except ObjectDoesNotExist:
                msg = f"group: {group} in study: {study_sid} does not exist"
                raise serializers.ValidationError(msg)
        return group

    def to_internal_value(self, data):

        # ----------------------------------
        # decompress external format
        # ----------------------------------

        temp_individuals = self.split_entry(data)
        individuals = []
        for individual in temp_individuals:
            characteristica = individual.get("characteristica")
            if characteristica:
                temp_characteristica = []
                for characteristica_single in characteristica:
                    temp_characteristica.extend(
                        self.split_entry(characteristica_single)
                    )
                individual["characteristica"] = temp_characteristica

            individuals_from_file = self.entries_from_file(individual)
            individuals.extend(individuals_from_file)

        # ----------------------------------
        # finished external format
        # ----------------------------------
        data = self.transform_ex_fields(data)
        data = self.transform_map_fields(data)

        data["individuals"] = individuals
        study_sid = self.context["request"].path.split("/")[-2]

        if "group" in data:
            data["group"] = self.group_to_internal_value(data.get("group"), study_sid)

        self.validate_wrong_keys(data)
        return super(WrongKeyValidationSerializer, self).to_internal_value(data)

    def validate_characteristica_ex(self, attrs):
        for characteristica in attrs:
            self._validate_individual_characteristica(characteristica)
        return attrs

    def to_representation(self, instance):

        rep = super().to_representation(instance)

        if "group" in rep:
            if rep["group"]:
                if instance.group:
                    rep["group"] = instance.group.name
                if instance.group_map:
                    rep["group"] = instance.group_map
        return rep


class IndividualSetSerializer(ExSerializer):

    individual_exs = IndividualExSerializer(many=True, read_only=False, required=False)
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    class Meta:
        model = IndividualSet
        fields = ["descriptions", "individual_exs", "comments"]

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        self.validate_wrong_keys(data)
        return data


###############################################################################################
# Read Serializer
###############################################################################################
class CharacteristicaReadSerializer(ReadSerializer):

    class Meta:
        model = Characteristica
        fields = ["pk"] + CHARACTERISTISTA_FIELDS +  ["normed"] + VALUE_FIELDS + ["group_pk","group_name"] +["individual_pk","individual_name", "all_group_pks"]


###############################################################################################
# Elastic Search Serializer
###############################################################################################
#maybe depreciated
class DataFileElasticSerializer(serializers.HyperlinkedModelSerializer):
    file = serializers.CharField()
    timecourses = serializers.SerializerMethodField()
    class Meta:
        model = DataFile
        fields = ["pk", "name","file", "timecourses"]

    def get_timecourses(self, obj):
        return list_of_pk("timecourses", obj)

    #def get_object(self):
    #    obj = get_object_or_404(self.get_queryset())
    #
    #    return obj
    #    self.check_object_permissions(self.request, obj)
    #    return obj


class CharacteristicaElasticSerializer(serializers.HyperlinkedModelSerializer):
    value = serializers.FloatField(allow_null=True)
    mean = serializers.FloatField(allow_null=True)
    median = serializers.FloatField(allow_null=True)
    min = serializers.FloatField(allow_null=True)
    max = serializers.FloatField(allow_null=True)
    sd = serializers.FloatField(allow_null=True)
    se = serializers.FloatField(allow_null=True)
    cv = serializers.FloatField(allow_null=True)
    category = serializers.CharField()
    class Meta:
        model = Characteristica
        fields = ["pk"] + CHARACTERISTISTA_FIELDS  + VALUE_FIELDS + ["normed"]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        for field in VALUE_FIELDS_NO_UNIT:
                try:
                    rep[field] = '{:.2e}'.format(rep[field])
                except (ValueError, TypeError):
                    pass
        return rep


class StudySmallElasticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Study
        fields = ["pk",'name']#,'url']


# Group related Serializer
class GroupSetElasticSmallSerializer(serializers.ModelSerializer):
    descriptions = DescriptionElasticSerializer(many=True, read_only=True)
    comments = CommentElasticSerializer(many=True, read_only=True)
    groups = serializers.SerializerMethodField()

    class Meta:
        model = GroupSet
        fields = ["pk", "descriptions", "groups", "comments"]

    def get_groups(self, obj):
        return list_of_pk("groups", obj)


class GroupSmallElasticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["pk", 'name', "count"]


class GroupElasticSerializer(serializers.ModelSerializer):
    study = StudySmallElasticSerializer(read_only=True)
    parent = GroupSmallElasticSerializer(read_only=True)
    characteristica_all_normed = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = (
            'pk',
            'parent',
            'count',
            'name',
            'study',
            'characteristica_all_normed',
        )

    def get_characteristica_all_normed(self, instance):
        if instance.characteristica_all_normed:
            characteristica = sorted(instance.characteristica_all_normed, key=itemgetter('count'))
            return CharacteristicaElasticSerializer(characteristica, many=True, read_only=True).data
        else:
            return []


# Individual related Serializer
class IndividualSmallElasticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Individual
        fields = ["pk", 'name']

class IndividualSetElasticSmallSerializer(serializers.HyperlinkedModelSerializer):
    descriptions = DescriptionElasticSerializer(many=True, read_only=True)
    comments = CommentElasticSerializer(many=True, read_only=True)
    individuals = serializers.SerializerMethodField()

    class Meta:
        model = IndividualSet
        fields = ["pk","descriptions", "individuals","comments"]

    def get_individuals(self,obj):
        return list_of_pk("individuals", obj)


class IndividualElasticSerializer(serializers.HyperlinkedModelSerializer):
    study = StudySmallElasticSerializer(read_only=True)
    group = GroupSmallElasticSerializer(read_only=True)
    characteristica_all_normed = CharacteristicaElasticSerializer(many=True, read_only=True)
    class Meta:
        model = Individual
        fields = (
            'pk',
            'group',
            'name',
            'study',
            'characteristica_all_normed',
        )

    def get_characteristica_all_normed(self, instance):
        characteristica = sorted(instance.characteristica_all_normed, key=itemgetter('count'))
        return CharacteristicaElasticSerializer(characteristica,many=True, read_only=True).data


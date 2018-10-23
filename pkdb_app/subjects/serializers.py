
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from rest_framework import serializers
from pkdb_app.categoricals import validate_categorials, CHARACTERISTIC_DICT, CHARACTERISTICA_TYPES
from pkdb_app.comments.serializers import DescriptionSerializer, CommentSerializer, DescriptionElasticSerializer, \
    CommentElasticSerializer
from pkdb_app.studies.models import Study
from operator import itemgetter

from pkdb_app.utils import list_of_pk
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
VALUE_FIELDS = ["value", "mean", "median", "min", "max", "sd", "se", "cv", "unit"]
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
CHARACTERISTISTA_FIELDS = ["count", "category", "choice", "ctype"]
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

    def validate(self, attrs):
        self.validate_wrong_keys(attrs)
        return super().validate(attrs)

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        self.validate_wrong_keys(data)
        return data


class CharacteristicaSerializer(ExSerializer):
    count = serializers.IntegerField(required=False)

    class Meta:
        model = Characteristica
        fields = CHARACTERISTISTA_FIELDS + VALUE_FIELDS

    def to_internal_value(self, data):
        data.pop("comments", None)
        self._is_required(data,"category")
        self.validate_wrong_keys(data)
        return super(WrongKeyValidationSerializer,self).to_internal_value(data)

    def validate(self, attr):
        try:
            # perform via dedicated function on categorials
            validate_categorials(data=attr, category_class="characteristica")
        except ValueError as err:
            raise serializers.ValidationError(err)
        #validate_categorials(attr, "characteristica")
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
        fields = ["pk"] + CHARACTERISTISTA_FIELDS +  ["final"] + VALUE_FIELDS + ["group_pk","group_name"] +["individual_pk","individual_name", "all_group_pks"]

###############################################################################################
# Elastic Search Serializer
###############################################################################################
#maybe depreciated

class DataFileElasticSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = DataFile
        fields = ["pk", "name"]

class CharacteristicaElasticSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Characteristica
        fields = ["pk"] + CHARACTERISTISTA_FIELDS  + VALUE_FIELDS



class StudySmallElasticSerializer(serializers.HyperlinkedModelSerializer):
    #url = serializers.HyperlinkedIdentityField(read_only=True,lookup_field="sid",view_name="studies_read-detail")
    class Meta:
        model = Study
        fields = ["pk",'name']#,'url']


# Group related Serializer
class GroupSetElasticSmallSerializer(serializers.HyperlinkedModelSerializer):
    descriptions = DescriptionElasticSerializer(many=True, read_only=True)
    comments = CommentElasticSerializer(many=True, read_only=True)
    groups = serializers.SerializerMethodField()

    class Meta:
        model = GroupSet
        fields = ["pk", "descriptions", "groups", "comments", "count"]

    def get_groups(self, obj):
        list_of_pk("groups", obj)
        return list_of_pk("groups", obj)


class GroupSmallElasticSerializer(serializers.HyperlinkedModelSerializer):
    # url = serializers.HyperlinkedIdentityField(read_only=True,view_name="groups_read-detail")
    class Meta:
        model = Group
        fields = ["pk", 'name']  # , 'url']


class GroupElasticSerializer(serializers.HyperlinkedModelSerializer):
    study = StudySmallElasticSerializer(read_only=True)
    parent = GroupSmallElasticSerializer(read_only=True)
    characteristica_all_final = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = (
            'pk',
            'parent',
            'count',
            'name',
            'study',
            'characteristica_all_final',
        )

    def get_characteristica_all_final(self, instance):
        characteristica = sorted(instance.characteristica_all_final, key=itemgetter('count'))
        return CharacteristicaElasticSerializer(characteristica, many=True, read_only=True).data


# Individual related Serializer
class IndividualSmallElasticSerializer(serializers.HyperlinkedModelSerializer):
    # url = serializers.HyperlinkedIdentityField(read_only=True,view_name="groups_read-detail")
    class Meta:
        model = Individual
        fields = ["pk", 'name']  # , 'url']

class IndividualSetElasticSmallSerializer(serializers.HyperlinkedModelSerializer):
    descriptions = DescriptionElasticSerializer(many=True, read_only=True)
    comments = CommentElasticSerializer(many=True, read_only=True)
    individuals = serializers.SerializerMethodField()

    class Meta:
        model = IndividualSet
        fields = ["pk","descriptions", "individuals","comments","count"]

    def get_individuals(self,obj):
        return list_of_pk("individuals", obj)


class IndividualElasticSerializer(serializers.HyperlinkedModelSerializer):
    study = StudySmallElasticSerializer(read_only=True)
    group = GroupSmallElasticSerializer(read_only=True)
    characteristica_all_final = serializers.SerializerMethodField()
    class Meta:
        model = Individual
        fields = (
            'pk',
            'group',
            'name',
            'study',
            'characteristica_all_final',
        )

    def get_characteristica_all_final(self, instance):
        characteristica = sorted(instance.characteristica_all_final, key=itemgetter('count'))
        return CharacteristicaElasticSerializer(characteristica,many=True, read_only=True).data


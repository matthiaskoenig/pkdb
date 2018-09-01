import pandas as pd
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from rest_framework import serializers
from pkdb_app.categoricals import FORMAT_MAPPING
from pkdb_app.comments.serializers import DescriptionSerializer, CommentSerializer
from pkdb_app.utils import recursive_iter, set_keys
from pkdb_app.utils import validate_categorials
from .models import Group, GroupSet, IndividualEx, IndividualSet, Characteristica, DataFile, Individual, \
    CharacteristicaEx, GroupEx
from ..serializers import WrongKeyValidationSerializer, MappingSerializer, ExSerializer

EXTERN_FILE_FIELDS = ["source", "format", "subset_map", "figure"]
VALUE_FIELDS =  ["value", "mean", "median", "min", "max", "sd", "se", "cv", "unit"]
VALUE_MAP_FIELDS = ["value_map", "mean_map", "median_map", "min_map", "max_map", "sd_map", "se_map","cv_map", "unit_map"]
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
        fields = ["file","filetype","id"]
        extra_kwargs = {'id': {'allow_null': False}}


# ----------------------------------
# Characteristica
# ----------------------------------
class CharacteristicaExSerializer(MappingSerializer):
    count = serializers.IntegerField(required=False)
    comments = CommentSerializer(many=True, read_only=False, required=False, allow_null=True)

    class Meta:
        model = CharacteristicaEx
        fields = CHARACTERISTISTA_FIELDS + CHARACTERISTISTA_MAP_FIELDS + VALUE_FIELDS + VALUE_MAP_FIELDS + ["comments"]


class CharacteristicaSerializer(serializers.ModelSerializer):
    count = serializers.IntegerField(required=False)

    class Meta:
        model = Characteristica
        fields = CHARACTERISTISTA_FIELDS + VALUE_FIELDS

    def to_internal_value(self, data):
        data.pop("comments",None)
        self.validate_wrong_keys(data)
        return super().to_internal_value(data)

    def validate(self,attr):
        validate_categorials(attr, "characteristica")
        return super().validate(attr)


# ----------------------------------
# Group
# ----------------------------------

class GroupSerializer(ExSerializer):
    characteristica = CharacteristicaSerializer(many=True, read_only=False, required=False)
    parent = serializers.CharField()

    class Meta:
            model = Group
            fields = GROUP_FIELDS + ["parent", "characteristica"]

    def to_internal_value(self, data):
        data.pop("comments",None)
        data = self.retransform_map_fields(data)
        data = self.retransform_ex_fields(data)
        self.validate_wrong_keys(data)
        return super(serializers.ModelSerializer, self).to_internal_value(data)



class GroupExSerializer(ExSerializer):
    characteristica_ex = CharacteristicaExSerializer(many=True, read_only=False, required=False)
    source = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)
    figure = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)
    parent_ex = serializers.CharField()
    comments = CommentSerializer(many=True, read_only=False, required=False, allow_null=True)


    # internal data
    groups = GroupSerializer(many=True, write_only=True, required=False, allow_null=True)

    class Meta:
        model = GroupEx
        fields = EXTERN_FILE_FIELDS + GROUP_FIELDS + GROUP_MAP_FIELDS + ["parent_ex", "characteristica_ex", "groups","comments"]

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
                    temp_characteristica.extend(self.split_entry(characteristica_single))
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
    descriptions = DescriptionSerializer(many=True, read_only=False, required=False, allow_null=True)
    group_exs = GroupExSerializer(many=True, read_only=False)
    comments = CommentSerializer(many=True, read_only=False, required=False, allow_null=True)

    class Meta:
        model = GroupSet
        fields = ["descriptions","group_exs","comments"]

# ----------------------------------
# Individual
# ----------------------------------
class IndividualSerializer(ExSerializer):
    name = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all())
    characteristica = CharacteristicaSerializer(many=True, read_only=False, required=False, allow_null=True)

    class Meta:
        model = Individual
        fields = ["name", "group", "characteristica"]

    @staticmethod
    def group_to_internal_value(group, study_sid):
        if group:
            try:
                group = Group.objects.get(Q(ex__groupset__study__sid=study_sid) & Q(name=group)).pk
            except ObjectDoesNotExist:
                msg = f'group: {group} in study: {study_sid} does not exist'
                raise serializers.ValidationError(msg)
        else:
            msg = {"group": f'group is required on individual',"detail":group}
            raise serializers.ValidationError(msg)
        return group

    def to_internal_value(self, data):
        data.pop("comments",None)
        study_sid = self.context['request'].path.split("/")[-2]
        if "group" in data:
            data["group"] = self.group_to_internal_value(data["group"], study_sid)

        data = self.retransform_map_fields(data)
        data = self.retransform_ex_fields(data)
        self.validate_wrong_keys(data)
        return super(serializers.ModelSerializer,self).to_internal_value(data)


class IndividualExSerializer(ExSerializer):

    characteristica_ex = CharacteristicaExSerializer(many=True, read_only=False, required=False, allow_null=True)
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), required=False, allow_null=True)
    source = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)
    figure = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)

    comments = CommentSerializer(many=True, read_only=False, required=False, allow_null=True)

    # internal data
    individuals = IndividualSerializer(many=True, write_only=True, required=False, allow_null=True)

    class Meta:
        model = IndividualEx
        fields = EXTERN_FILE_FIELDS + ["name", "name_map", "group", "group_map", "characteristica_ex","individuals","comments"]

    @staticmethod
    def group_to_internal_value(group, study_sid):
        if group:
            try:
                group = Group.objects.get(Q(ex__groupset__study__sid=study_sid) & Q(name=group)).pk
            except ObjectDoesNotExist:
                msg = f'group: {group} in study: {study_sid} does not exist'
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
                    temp_characteristica.extend(self.split_entry(characteristica_single))
                individual["characteristica"] = temp_characteristica

            individuals_from_file = self.entries_from_file(individual)
            individuals.extend(individuals_from_file)

        # ----------------------------------
        # finished external format
        # ----------------------------------
        data = self.transform_ex_fields(data)
        data = self.transform_map_fields(data)

        data["individuals"] = individuals
        study_sid = self.context['request'].path.split("/")[-2]

        if "group" in data:
            data["group"] = self.group_to_internal_value(data.get("group"), study_sid)
        self.validate_wrong_keys(data)
        return super(WrongKeyValidationSerializer,self).to_internal_value(data)

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

    individual_exs = IndividualExSerializer(many=True, read_only=False, required=False )
    descriptions = DescriptionSerializer(many=True, read_only=False, required=False, allow_null=True)
    comments = CommentSerializer(many=True, read_only=False, required=False, allow_null=True)

    class Meta:
        model = IndividualSet
        fields = ["descriptions", "individual_exs", "comments"]


###############################################################################################
# Read Serializer
###############################################################################################


class GroupSetReadSerializer(serializers.HyperlinkedModelSerializer):
    study = serializers.HyperlinkedRelatedField(lookup_field="sid", read_only=True, view_name="studies_read-detail")
    descriptions = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name="descriptions_read-detail")
    groups = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name="groups_read-detail")

    class Meta:
        model = GroupSet
        fields = ["pk", "study","descriptions","groups"]


class IndividualSetReadSerializer(serializers.HyperlinkedModelSerializer):
    study = serializers.HyperlinkedRelatedField(lookup_field="sid", read_only=True, view_name="studies_read-detail")
    individuals = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name="individuals_read-detail")
    descriptions = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name="descriptions_read-detail")

    class Meta:
        model = IndividualSet
        fields = ["pk","study","descriptions", "individuals"]


class GroupReadSerializer(serializers.HyperlinkedModelSerializer):
    groupset = serializers.HyperlinkedRelatedField(read_only=True, view_name="groupsets_read-detail")
    characteristica = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name="characteristica_read-detail")
    characteristica_all = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name="characteristica_read-detail")

    parent = serializers.HyperlinkedRelatedField(read_only=True, view_name="groups_read-detail")

    class Meta:
            model = Group
            fields = ["pk", "groupset"] + GROUP_FIELDS + ["parent", "characteristica", "characteristica_all"]



class IndividualReadSerializer(serializers.HyperlinkedModelSerializer):

    individualset = serializers.HyperlinkedRelatedField(read_only=True, view_name="individualsets_read-detail")
    group = serializers.HyperlinkedRelatedField(read_only=True, view_name="groups_read-detail")
    characteristica = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name="characteristica_read-detail")

    class Meta:
        model = Individual
        fields =["pk"] + ["individualset"] + ["name", "group", "characteristica"]


class CharacteristicaReadSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Characteristica
        fields = ["pk"]+CHARACTERISTISTA_FIELDS + VALUE_FIELDS


class DataFileReadSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = DataFile
        fields = ["pk","file","filetype","id"]
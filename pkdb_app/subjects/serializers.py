import pandas as pd
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from rest_framework import serializers
from pkdb_app.categoricals import FORMAT_MAPPING
from pkdb_app.comments.serializers import DescriptionsSerializer
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

    class Meta:
        model = CharacteristicaEx
        fields = CHARACTERISTISTA_FIELDS + CHARACTERISTISTA_MAP_FIELDS + VALUE_FIELDS + VALUE_MAP_FIELDS


class CharacteristicaSerializer(serializers.ModelSerializer):
    count = serializers.IntegerField(required=False)

    class Meta:
        model = Characteristica
        fields = CHARACTERISTISTA_FIELDS + VALUE_FIELDS

    def to_internal_value(self, data):

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
        data = self.retransform_map_fields(data)
        data = self.retransform_ex_fields(data)
        return super(serializers.ModelSerializer, self).to_internal_value(data)



class GroupExSerializer(ExSerializer):
    characteristica_ex = CharacteristicaExSerializer(many=True, read_only=False, required=False)
    source = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)
    figure = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)
    parent_ex = serializers.CharField()

    # internal data
    groups = GroupSerializer(many=True, write_only=True, required=False, allow_null=True)

    class Meta:
        model = GroupEx
        fields = EXTERN_FILE_FIELDS + GROUP_FIELDS + GROUP_MAP_FIELDS + ["parent_ex", "characteristica_ex", "groups"]

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

        return super(WrongKeyValidationSerializer, self).to_internal_value(data)

class GroupSetSerializer(ExSerializer):
    descriptions = DescriptionsSerializer(many=True,read_only=False,required=False, allow_null=True)
    group_exs = GroupExSerializer(many=True, read_only=False)

    class Meta:
        model = GroupSet
        fields = ["descriptions","group_exs"]

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
        return group

    def to_internal_value(self, data):
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

    # internal data
    individuals = IndividualSerializer(many=True, write_only=True, required=False, allow_null=True)

    class Meta:
        model = IndividualEx
        fields = EXTERN_FILE_FIELDS + ["name", "name_map", "group", "group_map", "characteristica_ex","individuals"]

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

        data = self.transform_map_fields(data)

        data["individuals"] = individuals


        study_sid = self.context['request'].path.split("/")[-2]

        if "group" in data:
            data["group"] = self.group_to_internal_value(data.get("group"), study_sid)

        return super(WrongKeyValidationSerializer,self).to_internal_value(data)

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
    descriptions = DescriptionsSerializer(many=True,read_only=False,required=False, allow_null=True )

    class Meta:
        model = IndividualSet
        fields = ["descriptions", "individual_exs"]


'''


class CharacteristicaSerializer(ParserSerializer):
    count = serializers.IntegerField(required=False)

    class Meta:
        model = Characteristica
        fields = ["category", "category_map","choice_map","choice", "ctype","ctype_map", "count", "value", "mean", "median", "min", "max", "sd", "se", "cv",
                  "unit", "count_map", "value_map", "mean_map", "median_map", "min_map", "max_map", "sd_map", "se_map",
                  "cv_map", "unit_map"]

    def to_representation(self, instance):
        result = super().to_representation(instance)
        if result["ctype"] == "group":
            result.pop("ctype")
        return unmap_keys(result)

    def to_internal_value(self, data):
        data = self.split_to_map(data)
        return super().to_internal_value(data)

    def validate(self, data):
        validated_data = super().validate(data)
        validated_data = validate_categorials(validated_data, "characteristica")

        return validated_data


class GroupSerializer(ParserSerializer):
    """ Group."""
    characteristica = CharacteristicaSerializer(many=True, read_only=False, required=False)
    parent = serializers.CharField()

    class Meta:
        model = Group
        fields = ["name","parent", "count", "characteristica",]

    def to_internal_value(self, data):
        data = self.split_entries_for_key(data, "characteristica")
        return super(GroupSerializer, self).to_internal_value(data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if "parent" in rep:
            rep["parent"] = instance.parent.name
        return rep

    def validate(self, data):
        validated_data = super().validate(data)
        return validated_data


class GroupSetSerializer(ParserSerializer):
    #characteristica = CharacteristicaSerializer(many=True, read_only=False, required=False)
    groups = GroupSerializer(many=True, read_only=False)
    descriptions = DescriptionsSerializer(many=True,read_only=False,required=False, allow_null=True )

    class Meta:
        model = GroupSet
        fields = ["descriptions","groups"]

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        return super(GroupSetSerializer, self).to_internal_value(data)


class CleanIndividualSerializer(ParserSerializer):
    """ Individual """
    characteristica = CharacteristicaSerializer(many=True, read_only=False, required=False, allow_null=True)
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), required=False, allow_null=True)
    source = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)
    figure = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)


    class Meta:
        model = Individual
        fields = ["name", "group", "characteristica", "source","figure","format"]

    @staticmethod
    def group_to_internal_value(group,study_sid):

        if group:
            try:
                group = Group.objects.get(Q(groupset__study__sid=study_sid) & Q(name=group)).pk
            except ObjectDoesNotExist:
                msg = f'group: {group} in study: {study_sid} does not exist'
                raise ValidationError(msg)
        return group

    def to_internal_value(self, data):
        study_sid = self.context['request'].path.split("/")[-2]
        if "group" in data :
            data["group"] = self.group_to_internal_value(data["group"],study_sid)
        return super().to_internal_value(data)



class IndividualSerializer(CleanIndividualSerializer):
    cleaned = CleanIndividualSerializer(many=True, write_only=True, required=False, allow_null=True)


    class Meta:

        model = IndividualEx
        fields =  ["name", "name_map", "group_map", "group", "characteristica",  "source","cleaned"]

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        data = self.split_entries_for_key(data, "characteristica")
        initial_data = deepcopy(data)
        data = self.split_to_map(data)
        study_sid = self.context['request'].path.split("/")[-2]
        if "group" in data :
            data["group"] = self.group_to_internal_value(data["group"], study_sid)

        #---------------------------------------
        # add cleaned individuals
        # ---------------------------------------
        cleaned_individuals = []
        recursive_individual_dict = list(recursive_iter(initial_data))


        #check if any mapping
        is_mapping = any("map" in field for field in data.keys())
        characteristica_data = initial_data.get("characteristica")
        if characteristica_data:
            is_mapping = is_mapping or any("map" in field for field in characteristica_data.keys())


        if is_mapping:

            source = initial_data.get("source")
            delimiter = FORMAT_MAPPING[initial_data.pop("format")].delimiter
            src = DataFile.objects.get(pk = source)
            #initial_data.pop("figure")
            try:
                individuals_data = pd.read_csv(src.file, delimiter=delimiter, keep_default_na=False)
            except:
                raise serializers.ValidationError(["cannot read csv"],data)


            for individual in individuals_data.itertuples():

                individual_dict = initial_data.copy()

                for keys,value in recursive_individual_dict:

                    if isinstance(value, str):
                        if "==" in value:
                            values = value.split("==")
                            values = [v.strip() for v in values]

                            if len(values) != 2 or values[0]!="col":
                                raise serializers.ValidationError(["field has wrong pattern col=='col_value'",data])
                            try:
                                 individual_value = getattr(individual, values[1])

                            except AttributeError:
                                raise serializers.ValidationError([f"key <{values[1]}> is missing in file <{source}> ", data])

                            set_keys(individual_dict,individual_value,*keys)



                cleaned_individuals.append(deepcopy(individual_dict))

        else:
            cleaned_individuals.append(initial_data)

        data["cleaned"] = cleaned_individuals
        # finish clean individuals
        #-------------------------------------------

        return super(IndividualSerializer, self).to_internal_value(data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if "group" in rep:
            rep["group"] = instance.group.name

        for file in ["source", "figure"]:
            if file in rep:
                current_site = f'http://{get_current_site(self.context["request"]).domain}'
                rep[file] = current_site+ getattr(instance,file).file.url
        return unmap_keys(rep)

    def validate(self, data):
        validated_data = super().validate(data)

        # individuals require group
        if not validated_data.get("group") and not validated_data.get("group_map"):
            raise serializers.ValidationError(
                ["individuals require group.",
                validated_data
            ])
        return validated_data


class IndividualSetSerializer(ParserSerializer):

    characteristica = CharacteristicaSerializer(many=True, read_only=False, required=False)
    individuals = IndividualSerializer(many=True, read_only=False, required=False )
    descriptions = DescriptionsSerializer(many=True,read_only=False,required=False, allow_null=True )

    class Meta:
        model = IndividualSet
        fields = ["descriptions", "individuals", "characteristica"]

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        data = self.split_entries_for_key(data, "characteristica")
        return super(IndividualSetSerializer, self).to_internal_value(data)

    def to_representation(self, instance):

        return unmap_keys(super().to_representation(instance))

'''

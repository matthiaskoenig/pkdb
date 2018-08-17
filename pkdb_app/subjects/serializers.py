from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from rest_framework import serializers
from pkdb_app.behaviours import Sourceable
from pkdb_app.utils import un_map, validate_input
from .models import Group, GroupSet, Individual, IndividualSet, Characteristica, DataFile
from ..serializers import ParserSerializer, WrongKeySerializer


class DataFileSerializer(WrongKeySerializer):
    class Meta:
        model = DataFile
        fields = ["file","filetype","id"]
        extra_kwargs = {'id': {'allow_null': False}}


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
        return un_map(result)

    def to_internal_value(self, data):
        data = self.split_to_map(data)
        return super().to_internal_value(data)

    def validate(self,data):
        validated_data = super().validate(data)
        return validate_input(validated_data,"characteristica")


class GroupSerializer(ParserSerializer):
    characteristica = CharacteristicaSerializer(many=True, read_only=False, required=False)
    parent = serializers.CharField()

    class Meta:
        model = Group
        fields = ["name", "count", "characteristica","parent"]

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        data = self.generic_parser(data, "characteristica")
        return super(GroupSerializer, self).to_internal_value(data)


class GroupSetSerializer(ParserSerializer):
    characteristica = CharacteristicaSerializer(many=True, read_only=False, required=False)
    groups = GroupSerializer(many=True, read_only=False)

    class Meta:
        model = GroupSet
        fields = ["description", "characteristica", "groups"]

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        data = self.generic_parser(data, "characteristica")
        return super(GroupSetSerializer, self).to_internal_value(data)



class IndividualSerializer(ParserSerializer):
    characteristica = CharacteristicaSerializer(many=True, read_only=False, required=False, allow_null=True)
    group =serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), required=False, allow_null=True)
    source = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)
    figure = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True)

    class Meta:
            model = Individual
            fields = Sourceable.fields() + ["name", "name_map",  "group_map", "characteristica", "group","source"]

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        data = self.generic_parser(data, "characteristica")
        data = self.split_to_map(data)
        return super(IndividualSerializer, self).to_internal_value(data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if "group" in rep:
            rep["group"] = instance.group.name

        for file in ["source", "figure"]:
            if file in rep:
                current_site = f'http://{get_current_site(self.context["request"]).domain}'
                rep[file] = current_site+ getattr(instance,file).file.url
        return un_map(rep)

    '''
    def parse_individuals(self,data):
    """
    later for parsing individuals from a dataset
    """
    try:
        individuals = data
        unpacked_individuals = []
        for individual in individuals:
            src =  individual.pop("source")  # todo: upload data first and then have the data saved here not the path.
            characteristica_mapping =  individual.pop("characteristica")

            delimiter = FORMAT_MAPPING[ individual.pop("format")].delimiter
            individual_mapping =  individual
            table = pd.read_csv(src, delimiter=delimiter, keep_default_na=False)
            characteristica_table = self.mapping_parser(characteristica_mapping,table)
            individuals_table = self.mapping_parser(individual_mapping,table)
            individuals_table["characteristica"] = characteristica_table.to_dict('records')
            unpacked_individuals += individuals_table.to_dict('recods')

        data = unpacked_individuals

    except KeyError:
        pass
    return data
    '''


class IndividualSetSerializer(ParserSerializer):

    characteristica = CharacteristicaSerializer(many=True, read_only=False, required=False)
    individuals = IndividualSerializer(many=True, read_only=False, required=False)

    class Meta:
        model = IndividualSet
        fields = ["description", "individuals", "characteristica"]

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        data = self.generic_parser(data, "characteristica")
        return super(IndividualSetSerializer, self).to_internal_value(data)

    def to_representation(self, instance):
        return un_map(super().to_representation(instance))
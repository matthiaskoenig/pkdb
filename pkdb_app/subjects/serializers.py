from rest_framework import serializers
from pkdb_app.behaviours import Sourceable
from pkdb_app.utils import un_map, validate_input
from .models import Group, GroupSet, Individual, IndividualSet, Characteristica
from ..serializers import ParserSerializer


class CharacteristicaSerializer(ParserSerializer):
    count = serializers.IntegerField(required=False)

    class Meta:
        model = Characteristica
        fields = ["category", "choice", "ctype", "count", "value", "mean", "median", "min", "max", "sd", "se", "cv",
                  "unit", "count_map", "value_map", "mean_map", "median_map", "min_map", "max_map", "sd_map", "se_map",
                  "cv_map", "unit_map"]

    def to_representation(self, instance):
        result = super().to_representation(instance)
        if result["ctype"] == "group":
            result.pop("ctype")
        return un_map(result)

    def to_internal_value(self, data):
        data = self.split_to_map(data)
        return super(CharacteristicaSerializer, self).to_internal_value(data)

    def validate(self, attrs):
        data = super().validate(attrs)
        return validate_input(data, "characteristica")


class GroupSerializer(ParserSerializer):
    characteristica = CharacteristicaSerializer(many=True, read_only=False, required=False)

    class Meta:
        model = Group
        fields = ["name", "count", "characteristica"]

    def to_internal_value(self, data):
        data = self.generic_parser(data, "characteristica")
        return super(GroupSerializer, self).to_internal_value(data)


class GroupSetSerializer(ParserSerializer):
    characteristica = CharacteristicaSerializer(many=True, read_only=False, required=False)
    groups = GroupSerializer(many=True, read_only=False)

    class Meta:
        model = GroupSet
        fields = ["description", "characteristica", "groups"]

    def to_internal_value(self, data):
        data = self.generic_parser(data, "characteristica")
        return super(GroupSetSerializer, self).to_internal_value(data)


class GroupSRField(serializers.SlugRelatedField):
    def get_queryset(self):
        study = self.context["study"]
        queryset = Group.objects.filter(groupset__study__sid=study)
        return queryset


class IndividualSerializer(ParserSerializer):
    characteristica = CharacteristicaSerializer(many=True, read_only=False, required=False, allow_null=True)
    group = GroupSRField(slug_field='name', read_only=False, required=False, allow_null=True)

    class Meta:
            model = Individual
            fields = Sourceable.fields() + ["name", "name_map",  "group_map", "characteristica", "group"]

    def to_internal_value(self, data):
        data = self.generic_parser(data, "characteristica")
        data = self.split_to_map(data)
        return super(IndividualSerializer, self).to_internal_value(data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if "group" in rep:
            rep["group"] = instance.group.name
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
        data = self.generic_parser(data, "characteristica")
        return super(IndividualSetSerializer, self).to_internal_value(data)

    def to_representation(self, instance):
        return un_map(super().to_representation(instance))
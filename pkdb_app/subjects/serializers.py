import pandas as pd
from django.core.exceptions import ValidationError
from rest_framework import serializers

from pkdb_app.behaviours import Sourceable
from pkdb_app.categoricals import FORMAT_MAPPING, CHARACTERISTIC_DICT, CATEGORIAL_TYPE, NUMERIC_TYPE, BOOLEAN_TYPE
from .models import Group, GroupSet,Individual,IndividualSet,Characteristica
from ..serializers import ParserSerializer

BASE_FIELDS = ()
from collections import OrderedDict



class CharacteristicaSerializer(ParserSerializer):

    count = serializers.IntegerField(required=False)

    class Meta:
        model = Characteristica
        fields = ["category","choice","ctype","count","value","mean","median","min","max","sd","se","cv","unit",
                  "count_map","value_map","mean_map","median_map","min_map","max_map","sd_map","se_map","cv_map","unit_map"]


    def to_representation(self, instance):
        result = super().to_representation(instance)
        return OrderedDict([(key, result[key]) for key in result if result[key] is not None])

    def to_internal_value(self, data):
        """

        :param data:
        :return:
        """
        data = self.split_to_map(data)
        characteristic = CHARACTERISTIC_DICT[data.get("category")]
        choice = data.get("choice",None)
        unit = data.get("unit",None)

        fields_require_unit = ["value","mean","median","min","max","sd","se","cv","value_map","mean_map","median_map","min_map","max_map","sd_map","se_map","cv_map"]

        if choice:
            if (characteristic.dtype == CATEGORIAL_TYPE or characteristic.dtype == BOOLEAN_TYPE):
                if not choice in characteristic.choices:
                    msg = f"{choice} is not part of {characteristic.choices} for {characteristic.value}"
                    raise ValidationError(msg)

        #if any(k in fields_require_unit for k in data.keys()):
        elif characteristic.dtype == NUMERIC_TYPE:
            if not unit in characteristic.units:
                msg = f"{unit} is not allowed but required. For {characteristic.value} allowed units are {characteristic.units}"
                raise ValidationError(msg)




        return super(CharacteristicaSerializer, self).to_internal_value(data)


class GroupSerializer(ParserSerializer):
    characteristica = CharacteristicaSerializer(many=True,read_only=False, required=False)

    class Meta:
        model = Group
        fields = ["name","count","characteristica"]


    def to_internal_value(self, data):
        """

        :param data:
        :return:
        """
        data = self.generic_parser(data,"characteristica")
        return super(GroupSerializer, self).to_internal_value(data)


class GroupSetSerializer(ParserSerializer):
    characteristica = CharacteristicaSerializer(many=True,read_only=False, required=False)
    groups = GroupSerializer(many=True, read_only=False)

    class Meta:
        model = GroupSet
        fields = ["description","characteristica","groups"]

    def to_internal_value(self, data):
        """

        :param data:
        :return:
        """
        data = self.generic_parser(data,"characteristica")
        return super(GroupSetSerializer, self).to_internal_value(data)


class GroupSRField(serializers.SlugRelatedField):
    def get_queryset(self):
        study = self.context["study"]
        queryset = Group.objects.filter(groupset__study__sid = study)
        return queryset

class IndividualSerializer(ParserSerializer):

    characteristica = CharacteristicaSerializer(many=True, read_only=False, required=False,allow_null=True)
    group = GroupSRField( slug_field='name',read_only=False,required=False, allow_null=True) #todo: filter for only this study

    #todo:add figure


    class Meta:
            model = Individual
            fields = Sourceable.fields() + ["name","name_map",  "group_map", "characteristica","group"]

    def to_internal_value(self, data):
        """

        :param data:
        :return:
        """
        data = self.generic_parser(data, "characteristica")
        data = self.split_to_map(data)
        #data = self.parse_individuals(data) #todo: this has to be done on CleanIndividual

        return super(IndividualSerializer, self).to_internal_value(data)

    def to_representation(self, instance):
        rep =  super().to_representation(instance)
        if "group" in rep:
            rep["group"] = instance.group.name

        return rep

    def parse_individuals(self,data):
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


class IndividualSetSerializer(ParserSerializer):
    characteristica = CharacteristicaSerializer(many=True,read_only=False, required=False)
    individuals = IndividualSerializer(many=True,read_only=False, required=False)


    class Meta:
        model = IndividualSet
        fields = ["description", "individuals", "characteristica"]

    def to_internal_value(self, data):
        """

        :param data:
        :return:
        """
        data = self.generic_parser(data,"characteristica")

        return super(IndividualSetSerializer, self).to_internal_value(data)



from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Q
from rest_framework import serializers

from pkdb_app.behaviours import Sourceable, Valueable, ValueableMap
from pkdb_app.interventions.models import Substance, InterventionSet, Intervention, Output, OutputSet
from pkdb_app.serializers import ParserSerializer
from pkdb_app.subjects.models import IndividualSet, Individual, Group
from pkdb_app.subjects.serializers import GroupSRField


class SubstanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Substance
        fields = ["name"]

    def create(self, validated_data):
        substance, created = Substance.objects.update_or_create(**validated_data)
        return substance


class InterventionSerializer(ParserSerializer):

    class Meta:
        model = Intervention
        fields = ["name","route","form","application","application_time","time_unit"]

    def to_internal_value(self, data):
        """

        :param data:
        :return:
        """

        data = self.split_to_map(data)
        data = self.drop_blank(data)
        data = self.strip(data)
        return super().to_internal_value(data)


class InterventionSetSerializer(ParserSerializer):

    interventions = InterventionSerializer(many=True , read_only=False,required=False, allow_null=True)

    class Meta:
        model = InterventionSet
        fields = ["description","interventions"]

    def to_internal_value(self, data):
        """

        :param data:
        :return:
        """
        #data = self.generic_parser(data,"interventions")
        #data = self.split_to_map(data)
        #data = self.drop_blank(data)
        #data = self.strip(data)
        return super(InterventionSetSerializer, self).to_internal_value(data)



class OutputSerializer(ParserSerializer):

    group =serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), read_only=False,required=False, allow_null=True)
    individual = serializers.PrimaryKeyRelatedField(queryset=Individual.objects.all(), read_only=False,required=False, allow_null=True)
    intervention = serializers.PrimaryKeyRelatedField(queryset=Intervention.objects.all(),read_only=False,required=False, allow_null=True)
    substance = serializers.SlugRelatedField(slug_field="name",queryset=Substance.objects.all(),read_only=False,required=False, allow_null=True)

    class Meta:
        model = Output
        fields = ["source","figure","format"] + \
                 ["value",  "mean",  "median",  "min", "max", "sd",  "se",  "cv",  "unit", ] \
                 +["value_map", "mean_map", "median_map",  "min_map", "max_map","sd_map", "se_map", "cv_map", "unit_map" ]\
                 + ["pktype", "pktype_map", "time",
                  "time_map","group", "group_map", "individual", "individual_map", "intervention", "intervention_map",
                   "substance","substance_map","tissue", "tissue_map"]

    def to_internal_value(self, data):
        """

        :param data:
        :return:
        """


        #data = self.strip(data)
        #data = self.generic_parser(data, "outputs")
        study_sid = self.context['request'].path.split("/")[-2]

        if "group" in data :
            if data["group"]:
                try:
                    data["group"] = Group.objects.get(Q(groupset__study__sid=study_sid) & Q(name=data.get("group"))).pk
                except ObjectDoesNotExist:
                    msg = f'group: {data.get("group")} in study: {study_sid} does not exist'
                    raise ValidationError(msg)
        if "individual" in data:
            if data["individual"]:
                try:
                    data["individual"] = Individual.objects.get(Q(individualset__study__sid=study_sid) & Q(name=data.get("individual"))).pk
                except ObjectDoesNotExist:
                    msg = f'individual: {data.get("individual")} in study: {study_sid} does not exist'
                    raise ValidationError(msg)
        if "intervention" in data:
            if data["intervention"]:
                try:
                    data["intervention"] = Intervention.objects.get(Q(interventionset__study__sid=study_sid) & Q(name=data.get("intervention"))).pk
                except ObjectDoesNotExist:
                    msg = f'intervention: {data.get("intervention")} in study: {study_sid} does not exist'
                    raise ValidationError(msg)

        data = self.split_to_map(data)
        #data = self.drop_empty(data)
        data = self.strip(data)
        data = self.drop_blank(data)
        print(data["value"])

        return super().to_internal_value(data)



class OutputSetSerializer(ParserSerializer):
    outputs = OutputSerializer(many=True, read_only=False, required=False, allow_null=True)


    class Meta:
        model = OutputSet
        fields = ["outputs","description"]

    def to_internal_value(self, data):
        """

        :param data:
        :return:
        """
        data = self.generic_parser(data, "outputs")
        data = self.split_to_map(data)

        return super().to_internal_value(data)

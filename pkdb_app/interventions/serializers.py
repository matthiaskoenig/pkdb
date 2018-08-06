from rest_framework import serializers

from pkdb_app.behaviours import Sourceable, Valueable, ValueableMap
from pkdb_app.interventions.models import Substance, InterventionSet, Intervention, Output, OutputSet
from pkdb_app.serializers import ParserSerializer
from pkdb_app.subjects.models import IndividualSet, Individual, Group


class SubstanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Substance
        fields = ["name"]

    def create(self, validated_data):
        substance, created = Substance.objects.update_or_create(**validated_data)
        return substance


class InterventionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Intervention
        fields = ["name","route","form","application","application_time","time_unit"]


class InterventionSetSerializer(ParserSerializer):

    interventions = InterventionSerializer(many=True , read_only=False)

    class Meta:
        model = InterventionSet
        fields = ["description","interventions"]

    def to_internal_value(self, data):
        """

        :param data:
        :return:
        """
        data = self.generic_parser(data,"interventions")
        return super(InterventionSetSerializer, self).to_internal_value(data)


class OutputSerializer(serializers.ModelSerializer):
    group = serializers.SlugRelatedField(queryset=Group.objects.all(), slug_field='name', read_only=False,
                                         required=False, allow_null=True)
    individual = serializers.SlugRelatedField(queryset=Individual.objects.all(), slug_field='name', read_only=False,
                                         required=False, allow_null=True)
    intervention =  serializers.SlugRelatedField(queryset=Intervention.objects.all(), slug_field='name',read_only=False,required=False, allow_null=True)
    substance = serializers.SlugRelatedField(queryset=Substance.objects.all(), slug_field='name',read_only=False,required=False, allow_null=True)

    class Meta:
        model = Output
        fields =  Sourceable.fields() + Valueable.fields() + ValueableMap.fields() + ["pktype", "pktype_map", "time",
                  "time_map","group", "group_map", "individual", "individual_map", "intervention", "intervention_map",
                   "substance","substance_map","tissue", "tissue_map"]


class OutputSetSerializer(ParserSerializer):
    outputs = OutputSerializer(many=True, read_only=False)


    class Meta:
        model = OutputSet
        fields = ["outputs","description"]

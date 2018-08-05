from rest_framework import serializers

from pkdb_app.interventions.models import Substance, InterventionSet, Intervention
from pkdb_app.serializers import ParserSerializer


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



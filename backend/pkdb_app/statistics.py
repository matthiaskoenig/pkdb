"""Basic information and statistics about database content."""

from django.db.models import Count, F, Q
from rest_framework import serializers, viewsets
from rest_framework.response import Response

from pkdb_app import __version__
from pkdb_app.data.models import Data, SubSet
from pkdb_app.info_nodes.models import Substance
from pkdb_app.interventions.models import Intervention
from pkdb_app.outputs.models import Output
from pkdb_app.studies.models import Reference, Study
from pkdb_app.subjects.models import Group, Individual


class SubstanceStatisticsViewSet(viewsets.ViewSet):
    """Endpoint listing the count of normed interventions and outputs.

    The counts are listed per substance.
    """

    def list(self, request):
        """Return one row per substance with its intervention and output counts."""
        substances_interventions = Substance.objects.annotate(
            label=F("info_node__label"),
            intervention_count=Count(
                "intervention", filter=Q(intervention__normed=True)
            ),
        ).order_by("info_node__label")
        substances_outputs = Substance.objects.annotate(
            label=F("info_node__label"),
            output_count=Count("output", filter=Q(output__normed=True)),
        ).order_by("info_node__label")

        data = zip(
            substances_outputs.values("info_node__label"),
            substances_outputs.values("output_count"),
            substances_interventions.values("intervention_count"),
        )

        result = []
        for x in data:
            res = {}
            for v in x:
                res = {**res, **v}
            result.append(res)

        return Response(result)


class SubstanceStatisticsSerializer(serializers.Serializer):
    """Serialize the per substance intervention and output counts."""

    label = serializers.CharField()
    intervention_count = serializers.IntegerField(allow_null=True)
    output_count = serializers.IntegerField(allow_null=True)


class Statistics:
    """Basic database statistics."""

    def __init__(self):
        """Compute the current counts of the database content.

        The counted content is studies, subjects, interventions and outputs.
        """
        self.version = __version__
        self.study_count = Study.objects.count()
        self.reference_count = Reference.objects.count()
        self.group_count = Group.objects.count()
        self.individual_count = Individual.objects.count()
        self.intervention_count = Intervention.objects.filter(normed=True).count()
        self.output_count = Output.objects.filter(normed=True).count()
        self.output_calculated_count = Output.objects.filter(
            normed=True, calculated=True
        ).count()
        self.timecourse_count = SubSet.objects.filter(
            data__data_type=Data.DataTypes.Timecourse
        ).count()
        self.scatter_count = SubSet.objects.filter(
            data__data_type=Data.DataTypes.Scatter
        ).count()


class StatisticsViewSet(viewsets.ViewSet):
    """ViewSet backing the `/api/v1/statistics/` endpoint, see `list`."""

    def list(self, request):
        """Endpoint to query PK-DB statistics.

        Get database statistics consisting of count and version information.
        """
        instance = Statistics()
        serializer = StatisticsSerializer(instance)
        return Response(serializer.data)


class StatisticsSerializer(serializers.BaseSerializer):
    """Serializer for database statistics."""

    def to_representation(self, instance):
        """Return the count and version attributes of the given Statistics instance."""
        return {
            key: getattr(instance, key)
            for key in [
                "version",
                "study_count",
                "reference_count",
                "group_count",
                "individual_count",
                "intervention_count",
                "output_count",
                "output_calculated_count",
                "timecourse_count",
                "scatter_count",
            ]
        }

from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from ..documents import string_field, elastic_settings, study_field, info_node
from ..interventions.models import Intervention


# ------------------------------------
# Elastic Intervention Document
# ------------------------------------
@registry.register_document
class InterventionDocument(Document):
    pk = fields.IntegerField("pk")
    measurement_type = info_node("i_measurement_type")
    calculation_type = info_node("i_calculation_type")

    form = info_node("i_form")
    route = info_node("i_route")
    application = info_node("i_application")
    choice = info_node("i_choice")
    substance = info_node("i_substance")

    time_unit = string_field('time_unit')
    time = string_field('time')
    time_end = fields.FloatField()

    measurement_type_name = fields.TextField(
        attr='measurement_type_name',
        fields={
            'raw': fields.TextField(analyzer='keyword'),
        }
    )
    calculation_type_name = string_field('calculation_type_name')

    form_name = string_field('form_name')
    route_name = string_field('route_name')
    application_name = string_field('application_name')
    choice_name = string_field('choice_name')
    substance_name = string_field('substance_name')  #FIXME: Remove
    study = study_field
    study_name = string_field('study_name')  # FIXME: Remove
    study_sid = string_field('study_sid')  # FIXME: Remove

    name = string_field('name')
    normed = fields.BooleanField()
    raw_pk = string_field('raw_pk')
    value = fields.FloatField()
    mean = fields.FloatField()
    median = fields.FloatField()
    min = fields.FloatField()
    max = fields.FloatField()
    se = fields.FloatField()
    sd = fields.FloatField()
    cv = fields.FloatField()
    unit = string_field('unit')
    access = string_field('access')
    allowed_users = fields.ObjectField(
        attr="allowed_users",
        properties={
            'username': string_field("username")
        },
        multi=True
    )

    class Django:
        model = Intervention
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False

    class Index:
        name = 'interventions'
        settings = elastic_settings

    def get_queryset(self):
        """Not mandatory but to improve performance we can select related in one sql request"""
        return super(InterventionDocument, self).get_queryset().select_related('study')

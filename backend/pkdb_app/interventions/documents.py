from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from ..documents import string_field, elastic_settings, ObjectField
from ..interventions.models import Intervention


# ------------------------------------
# Elastic Intervention Document
# ------------------------------------
@registry.register_document
class InterventionDocument(Document):
    pk = fields.IntegerField()
    measurement_type = fields.StringField(
        attr='measurement_type_name',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )

    form = fields.StringField(
        attr='form_name',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )
    route = fields.StringField(
        attr='route_name',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )
    application = fields.StringField(
        attr='application_name',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )
    choice = string_field('choice')
    time_unit = string_field('time_unit')
    time = fields.FloatField()
    time_end = fields.FloatField()

    substance = string_field('substance_name')
    study_name = string_field('study_name')
    study_sid = string_field('study_sid')

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
        return super(InterventionDocument, self).get_queryset().select_related(
            'ex__interventionset__study')

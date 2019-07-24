from django_elasticsearch_dsl import DocType, fields
from django_elasticsearch_dsl.registries import registry
from ..documents import string_field, elastic_settings, ObjectField
from ..interventions.models import Intervention

# ------------------------------------
# Elastic Intervention Document
# ------------------------------------
@registry.register_document
class InterventionDocument(DocType):
    pk = fields.IntegerField()
    measurement_type = fields.StringField(
        attr='measurement_type_name',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )
    choice = string_field('choice')
    application = string_field('application')
    time_unit = string_field('time_unit')
    time = fields.FloatField()
    substance = string_field('substance_name')
    study = string_field('study_name')
    route = string_field('route')
    form = string_field('form')
    name = string_field('name')
    normed = fields.BooleanField()
    raw = ObjectField(properties={
        'pk': fields.IntegerField()
    })
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
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False

    class Index:
        name = 'interventions'
        settings = elastic_settings

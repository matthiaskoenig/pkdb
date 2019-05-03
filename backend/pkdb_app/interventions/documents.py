from django_elasticsearch_dsl import DocType, Index, fields
from ..documents import string_field, elastic_settings, ObjectField
from ..interventions.models import Intervention



intervention_index = Index("interventions")
intervention_index.settings(**elastic_settings)

@intervention_index.doc_type
class InterventionDocument(DocType):
    pk = fields.IntegerField()
    #category =  string_field('category_key')

    category = fields.StringField(
        attr='category_key',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )

    choice = string_field('choice')
    application = string_field('application')
    time_unit = string_field('time_unit')
    time = fields.FloatField()
    substance = ObjectField(properties={
        'name': string_field('name')}
        )
    study = string_field('study')
    route = string_field('route')
    form = string_field('form')
    name = string_field('name')
    normed = fields.BooleanField()
    raw = ObjectField(properties={
        'pk': fields.IntegerField()}
        )
    value = fields.FloatField()
    mean = fields.FloatField()
    median = fields.FloatField()
    min = fields.FloatField()
    max = fields.FloatField()
    se = fields.FloatField()
    sd = fields.FloatField()
    cv = fields.FloatField()
    unit = string_field('unit')

    class Meta(object):
        model = Intervention
        # Ignore auto updating of Elasticsearch when a model is saved
        # or deleted:
        ignore_signals = True
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False
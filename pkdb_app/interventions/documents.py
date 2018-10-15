from django_elasticsearch_dsl import DocType, Index, fields
from elasticsearch_dsl import analyzer

from pkdb_app.interventions.models import Substance, Intervention, Output
from pkdb_app.studies.documents import autocomplete, autocomplete_search
substance_index = Index("substances")
substance_index.settings(number_of_shards=1,
               number_of_replicas=1,)

def string_field(attr):
    return fields.StringField(
        attr=attr,
        fielddata=True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields={'raw': fields.KeywordField()}
        )


@substance_index.doc_type
class SubstanceDocument(DocType):
    pk = fields.IntegerField()
    name = string_field('name')
    class Meta(object):
        model = Substance

intervention_index = Index("interventions")
intervention_index.settings(number_of_shards=1,
               number_of_replicas=1,)


@intervention_index.doc_type
class InterventionDocument(DocType):
    pk = fields.IntegerField()
    category =  string_field('category')
    choice = string_field('choice')
    application = string_field('application')
    time_unit = string_field('time_unit')
    time = fields.FloatField()
    substance = fields.ObjectField(properties={
        'name': string_field('name')}
        )
    route = string_field('route')
    form = string_field('form')
    name = string_field('name')
    final = fields.BooleanField()
    value = fields.FloatField()
    mean = fields.FloatField()
    median = fields.FloatField()
    min = fields.FloatField()
    max = fields.FloatField()
    se = fields.FloatField()
    sd = fields.FloatField()
    cv = fields.FloatField()

    class Meta(object):
        model = Intervention


output_index = Index("outputs")
output_index.settings(number_of_shards=1,
               number_of_replicas=1,)


@output_index.doc_type
class OutputDocument(DocType):
    pk = fields.IntegerField('pk')
    class Meta(object):
            model = Output


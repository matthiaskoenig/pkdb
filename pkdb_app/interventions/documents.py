from django_elasticsearch_dsl import DocType, Index, fields
from elasticsearch_dsl import analyzer

from pkdb_app.interventions.models import Substance, Intervention
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

BOOLEAN_FIELD = fields.BooleanField()

INTEGER_FIELD = fields.IntegerField()

FLOAT_FIELD = fields.FloatField()

@substance_index.doc_type
class SubstanceDocument(DocType):
    pk = INTEGER_FIELD
    name = string_field('name')
    class Meta(object):
        model = Substance

intervention_index = Index("interventions")
intervention_index.settings(number_of_shards=1,
               number_of_replicas=1,)


@intervention_index.doc_type
class InterventionDocument(DocType):
    pk = INTEGER_FIELD
    category =  string_field('category')
    choice = string_field('choice')
    application = string_field('application')
    time_unit = string_field('time_unit')
    substance = fields.ObjectField(properties={
        'name': string_field('name')}
        )
    route = string_field('route')
    name = string_field('name')
    final = BOOLEAN_FIELD
    count = INTEGER_FIELD
    value = FLOAT_FIELD
    mean = FLOAT_FIELD
    median = FLOAT_FIELD
    min = FLOAT_FIELD
    max = FLOAT_FIELD
    se = FLOAT_FIELD
    sd = FLOAT_FIELD
    cv = FLOAT_FIELD

    class Meta(object):
        model = Intervention



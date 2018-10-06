from elasticsearch_dsl import analyzer
from django_elasticsearch_dsl import DocType, Index, fields
from pkdb_app.subjects.models import Individual, Characteristica

# Name of the Elasticsearch index
individuals_index = Index("individuals")

# See Elasticsearch Indices API reference for available settings
individuals_index.settings(
    number_of_shards=1,
    number_of_replicas=1
)

html_strip = analyzer(
    'html_strip',
    tokenizer="standard",
    filter=["standard", "lowercase", "stop", "snowball"],
    char_filter=["html_strip"]
)

@individuals_index.doc_type
class IndividualDocument(DocType):
    """Individual elastic search document"""
    id = fields.IntegerField(attr='id')
    name = fields.StringField(
        fields={
            'raw': fields.StringField(analyzer='keyword'),
            'suggest': fields.CompletionField(),

        }
    )

    group = fields.StringField(
        attr='group_indexing',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )

    study = fields.StringField(
        attr='study_indexing',
        fields={
            'raw': fields.StringField(analyzer='keyword'),

        }
    )

    class Meta:
        model=Individual


# Name of the Elasticsearch index
characteristica_index = Index("characteristica")

# See Elasticsearch Indices API reference for available settings
characteristica_index.settings(
    number_of_shards=1,
    number_of_replicas=1
)

@characteristica_index.doc_type
class CharacteristicaDocument(DocType):
    """Characteristica elastic search document"""
    id = fields.IntegerField(attr='id')
    final = fields.BooleanField()

    group_name = fields.StringField(
        attr='group_name',
        fields={
            'raw': fields.StringField(analyzer='keyword'),

        }
    )

    group_pk = fields.IntegerField(attr='group_id')

    individual_name = fields.StringField(
        attr='individual_name',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )
    individual_pk = fields.IntegerField(attr='individual_id')

    category = fields.StringField(
        fields={
            'raw': fields.StringField(analyzer='keyword'),
            'suggest': fields.CompletionField(),
        }
    )

    choice = fields.StringField(
        fields={
            'raw': fields.StringField(analyzer='keyword'),

        }
    )
    ctype = fields.StringField(
        fields={
            'raw': fields.StringField(analyzer='keyword'),
            'suggest': fields.CompletionField(),
        }
    )
    unit = fields.StringField(
        fields={
            'raw': fields.StringField(analyzer='keyword'),

        }
    )

    count = fields.IntegerField()
    value = fields.FloatField(attr='value')
    mean = fields.FloatField(attr='mean')
    median = fields.FloatField(attr='median')
    min = fields.FloatField(attr='min')
    max = fields.FloatField(attr='max')
    se = fields.FloatField(attr='se')
    sd = fields.FloatField(attr='sd')
    cv = fields.FloatField(attr='cv')


    class Meta:
        model=Characteristica
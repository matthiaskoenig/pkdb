from elasticsearch_dsl import analyzer
from django_elasticsearch_dsl import DocType, Index, fields
from django.conf import settings
from pkdb_app.subjects.models import Individual, Characteristica

# Name of the Elasticsearch index
INDEX = Index("subjects")

# See Elasticsearch Indices API reference for available settings
INDEX.settings(
    number_of_shards=1,
    number_of_replicas=1
)

html_strip = analyzer(
    'html_strip',
    tokenizer="standard",
    filter=["standard", "lowercase", "stop", "snowball"],
    char_filter=["html_strip"]
)

@INDEX.doc_type
class IndividualDocument(DocType):
    """Individual elastic search document"""
    id = fields.IntegerField(attr='id')
    name = fields.StringField(
        analyzer=html_strip,
        fields={
            'raw': fields.StringField(analyzer='keyword'),
            'suggest': fields.CompletionField(),

        }
    )

    group = fields.StringField(
        attr='group_indexing',
        analyzer=html_strip,
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )

    study = fields.StringField(
        attr='study_indexing',
        analyzer=html_strip,
        fields={
            'raw': fields.StringField(analyzer='keyword'),

        }
    )


    """
       categories = fields.StringField(
        attr='characteristica_categories',
        analyzer=html_strip,
        fields={
            'raw': fields.StringField(analyzer='keyword', multi=True),
        }
    )


    choices = fields.StringField(
        attr='characteristica_choices',
        analyzer=html_strip,
        fields={
            'raw': fields.StringField(analyzer='keyword', multi=True),
            'suggest': fields.CompletionField(multi=True),

        }
    )
    """



    class Meta:
        model=Individual




@INDEX.doc_type
class CharacteristicaDocument(DocType):
    """Characteristica elastic search document"""
    id = fields.IntegerField(attr='id')

    group_name = fields.StringField(
        attr='group_name',
        analyzer=html_strip,
        fields={
            'raw': fields.StringField(analyzer='keyword'),
            #'suggest': fields.CompletionField(),

        }
    )
    group_pk = fields.IntegerField(attr='group_id')
    individual_name = fields.StringField(
        attr='individual_name',
        analyzer=html_strip,
        fields={
            'raw': fields.StringField(analyzer='keyword'),
            #'suggest': fields.CompletionField(),

        }
    )
    individual_pk = fields.IntegerField(attr='individual_id')

    category = fields.StringField(
        analyzer=html_strip,
        fields={
            'raw': fields.StringField(analyzer='keyword'),
            'suggest': fields.CompletionField(),
        }
    )

    choice = fields.StringField(
        analyzer=html_strip,
        fields={
            'raw': fields.StringField(analyzer='keyword'),
            #'suggest': fields.CompletionField(),

        }
    )
    ctype = fields.StringField(
        analyzer=html_strip,
        fields={
            'raw': fields.StringField(analyzer='keyword'),
            'suggest': fields.CompletionField(),

        }
    )
    unit = fields.StringField(
        analyzer=html_strip,
        fields={
            'raw': fields.StringField(analyzer='keyword'),
            #'suggest': fields.CompletionField(),

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

    """
       categories = fields.StringField(
        attr='characteristica_categories',
        analyzer=html_strip,
        fields={
            'raw': fields.StringField(analyzer='keyword', multi=True),
        }
    )


    choices = fields.StringField(
        attr='characteristica_choices',
        analyzer=html_strip,
        fields={
            'raw': fields.StringField(analyzer='keyword', multi=True),
            'suggest': fields.CompletionField(multi=True),

        }
    )
    """



    class Meta:
        model=Characteristica
from elasticsearch_dsl import analyzer
from django_elasticsearch_dsl import DocType, Index, fields
from django.conf import settings
from pkdb_app.subjects.models import Individual

# Name of the Elasticsearch index
INDEX = Index("individuals")

# See Elasticsearch Indices API reference for available settings
INDEX.settings(
    number_of_shards=1,
    number_of_replicas=0
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
            'suggest': fields.CompletionField(),

        }
    )

    study = fields.StringField(
        attr='study_indexing',
        analyzer=html_strip,
        fields={
            'raw': fields.StringField(analyzer='keyword'),
            'suggest': fields.CompletionField(),

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
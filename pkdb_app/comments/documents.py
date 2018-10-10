from elasticsearch_dsl import analyzer
from django_elasticsearch_dsl import DocType, Index, fields

# Name of the Elasticsearch index
from pkdb_app.comments.models import Comment, Description

common_settings = {'number_of_shards':1,'number_of_replicas':1}
comments_index = Index("comments")
descriptions_index = Index("descriptions")

comments_index.settings(**common_settings)
descriptions_index.settings(**common_settings)

html_strip = analyzer(
    'html_strip',
    tokenizer="standard",
    filter=["standard", "lowercase", "stop", "snowball"],
    char_filter=["html_strip"]
)


@comments_index.doc_type
class CommentDocument(DocType):
    pk = fields.IntegerField(attr='pk')
    user = fields.ObjectField(
        properties={
        'first_name': fields.StringField(
            analyzer=html_strip,
            fields={
                'raw': fields.KeywordField(),
                'suggest': fields.CompletionField(),
            },),
        'last_name': fields.StringField(
            analyzer=html_strip,
            fields={
            'raw': fields.KeywordField(),
            'suggest': fields.CompletionField(),},)
        })

    text = fields.StringField(
        analyzer=html_strip,
        fields={'raw': fields.KeywordField(),
                'suggest': fields.CompletionField(),
                })

    date_time = fields.DateField()

    class Meta(object):
        model = Comment


@descriptions_index.doc_type
class DescriptionDocument(DocType):
    pk = fields.IntegerField(attr='pk')

    text = fields.StringField(
        analyzer=html_strip,
        fields={'raw': fields.KeywordField(),
                'suggest': fields.CompletionField(),
                })

    class Meta(object):
        model = Description

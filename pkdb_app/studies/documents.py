from django_elasticsearch_dsl import DocType, Index, fields
from elasticsearch_dsl import analyzer, tokenizer, token_filter
from pkdb_app.studies.models import Reference

INDEX = Index("references")
INDEX.settings(number_of_shards=1,
               number_of_replicas=1,)

html_strip = analyzer(
    'html_strip',
    tokenizer="standard",
    filter=["standard", "lowercase", "stop", "snowball"],
    char_filter=["html_strip"]
)
my_analyzer = analyzer('my_analyzer',
    tokenizer=tokenizer('trigram', 'edge_ngram', min_gram=1, max_gram=20),
                       filter=["standard", "lowercase", "stop", "snowball"],
                       char_filter=["html_strip"])

edge_ngram_analyzer = analyzer(
    'edge_ngram_analyzer',
    type='custom',
    tokenizer='standard',
    filter=[
        'lowercase',
        token_filter(
            'edge_ngram_filter', type='edgeNGram',
            min_gram=1, max_gram=20
        )
    ]
)

@INDEX.doc_type
class ReferenceDocument(DocType):
    pk = fields.IntegerField(attr='pk')
    pmid = fields.StringField(attr='pmid',fielddata=True)
    sid = fields.StringField(attr='sid',fielddata=True)
    study_name = fields.StringField(fielddata=True)
    study_pk = fields.StringField(fielddata=True)

    name = fields.StringField(
        fielddata = True,
        analyzer=html_strip,
        fields = {'raw': fields.KeywordField(),
                  'suggest':fields.CompletionField(),
                  })

    doi = fields.StringField(attr='doi',fielddata=True)

    title = fields.TextField(
        fielddata = True,
        analyzer=html_strip,
        fields = {'raw': fields.KeywordField(),
                  'suggest':fields.CompletionField(),
                  })
    abstract = fields.TextField(
        fielddata = True,
        analyzer=html_strip,
        fields={'raw': fields.KeywordField(),
                })

    journal = fields.TextField(
        fielddata = True,
        analyzer=html_strip,
        fields={'raw': fields.KeywordField(),
                'suggest': fields.CompletionField(),
                })
    date = fields.DateField()
    pdf = fields.FileField(fielddata=True)
    authors = fields.ObjectField(properties={
        'first_name': fields.StringField(
            analyzer=html_strip,
            fields={
                'raw': fields.KeywordField(),
            },),
        'last_name': fields.StringField(
            fielddata = True,
            analyzer=html_strip,
            fields={
            'raw': fields.KeywordField(),
        }),
        'pk' : fields.IntegerField(),

    })

    class Meta(object):
        model = Reference

from django_elasticsearch_dsl import DocType, Index, fields
from elasticsearch_dsl import analyzer, token_filter
from pkdb_app.studies.models import Reference

INDEX = Index("references")
INDEX.settings(number_of_shards=1,
               number_of_replicas=1,)



edge_ngram_filter =  token_filter(
            'edge_ngram_filter',
            type="edge_ngram",
            min_gram=1, max_gram=20)


autocomplete_search = analyzer(
    'autocomplete_search',
    tokenizer="standard",
    filter=["lowercase"],
)


autocomplete = analyzer('autocomplete',
    tokenizer="standard",
    filter=[ "lowercase",edge_ngram_filter],
    char_filter=["html_strip"],
    chars=["letter"],
    token_chars=["letter"])





@INDEX.doc_type
class ReferenceDocument(DocType):
    pk = fields.IntegerField(attr='pk')
    pmid = fields.StringField(attr='pmid',fielddata=True)
    sid = fields.StringField(attr='sid',fielddata=True)
    study_name = fields.StringField(fielddata=True)
    study_pk = fields.StringField(fielddata=True)

    name = fields.StringField(
        fielddata = True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields = {'raw': fields.KeywordField(),
                  'suggest':fields.CompletionField(),
                  }
        )


    doi = fields.StringField(attr='doi',fielddata=True)

    title = fields.TextField(
        fielddata = True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields = {'raw': fields.KeywordField(),
                  'suggest':fields.CompletionField(),
                  })
    abstract = fields.TextField(
        fielddata = True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields={'raw': fields.KeywordField(),
                })

    journal = fields.TextField(
        fielddata = True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields={'raw': fields.KeywordField(),
                'suggest': fields.CompletionField(),
                })
    date = fields.DateField(
    )
    pdf = fields.FileField(fielddata=True)
    authors = fields.ObjectField(properties={
        'first_name': fields.StringField(
            analyzer=autocomplete,
            fields={
                'raw': fields.KeywordField(),
            },),
        'last_name': fields.StringField(
            fielddata = True,
            analyzer=autocomplete,
            fields={
            'raw': fields.KeywordField(),
        }),
        'pk' : fields.IntegerField(),

    })

    class Meta(object):
        model = Reference

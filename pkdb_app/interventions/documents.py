from django_elasticsearch_dsl import DocType, Index, fields
from elasticsearch_dsl import analyzer

from pkdb_app.interventions.models import Substance

INDEX = Index("substances")
INDEX.settings(number_of_shards=1,
               number_of_replicas=1,)

html_strip = analyzer(
    'html_strip',
    tokenizer="standard",
    filter=["standard", "lowercase", "stop", "snowball"],
    char_filter=["html_strip"]
)

@INDEX.doc_type
class SubstanceDocument(DocType):
    pk = fields.IntegerField(attr='pk')
    name = fields.StringField(
        #analyzer=html_strip,
        fields = {'raw': fields.KeywordField(),
                  'suggest':fields.CompletionField(),
                  })
    class Meta(object):
        model = Substance
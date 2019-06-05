from django_elasticsearch_dsl import DocType, Index, fields
from ..documents import string_field, elastic_settings, ObjectField, text_field
from .models import Substance
substance_index = Index("substances")
substance_index.settings(**elastic_settings)

@substance_index.doc_type
class SubstanceDocument(DocType):
    sid = string_field('sid')
    url_slug = string_field('url_slug')
    creator = string_field('creator_username')

    name = string_field('name')
    mass = fields.FloatField()
    charge = fields.FloatField()
    formula = string_field('formula')
    derived = fields.BooleanField()
    description = text_field('description')
    parents = ObjectField(properties={
        'sid': string_field('sid'),
        'url_slug': string_field('url_slug')
    }, multi=True)

    class Meta(object):
        model = Substance
        # Ignore auto updating of Elasticsearch when a model is saved
        # or deleted:
        ignore_signals = False
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False


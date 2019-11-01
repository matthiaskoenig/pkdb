from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from ..documents import string_field, elastic_settings, ObjectField, text_field
from .models import Substance


# ------------------------------------
# Elastic Substance Document
# ------------------------------------
@registry.register_document
class SubstanceDocument(Document):
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
    annotations = ObjectField(
        attr="annotations",
        multi=True,
        properties={
            "term": string_field("term"),
            "relation": string_field("relation"),
            "collection": string_field("collection"),
            "description": string_field("description"),
            "label": string_field("label")
        }
    )

    class Django:
        model = Substance
        # Ignore auto updating of Elasticsearch when a model is saved
        # or deleted:
        ignore_signals = False
        # Don't perform an index refresh after every update
        auto_refresh = False

    class Index:
        name = "substances"
        settings = elastic_settings

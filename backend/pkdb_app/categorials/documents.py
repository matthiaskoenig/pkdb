from django_elasticsearch_dsl import DocType, fields
from django_elasticsearch_dsl.registries import registry
from ..documents import string_field, elastic_settings, ObjectField
from .models import MeasurementType


# ------------------------------------
# Elastic Measurement Document
# ------------------------------------
@registry.register_document
class MeasurementTypeDocument(DocType):
    pk = fields.IntegerField()
    name = string_field('name')
    url_slug = string_field('url_slug')
    dtype = string_field('dtype')

    units = interventions = ObjectField(properties={
        'name': string_field('name')
        }, multi=True)

    choices = ObjectField(
        attr="choices",
        multi=True,
        properties={
            "name": string_field("name"),
            "description": string_field('description'),
            "annotations": ObjectField(
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
        }
    )
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
    creator = string_field("creator_username")
    description = string_field('description')

    class Django:
        model = MeasurementType
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = False
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False

    class Index:
        name = 'measurement_types'
        settings = elastic_settings

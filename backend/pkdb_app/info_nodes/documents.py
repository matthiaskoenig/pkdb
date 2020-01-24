from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from ..documents import string_field, elastic_settings, ObjectField, text_field
from .models import InfoNode

annotation_field = ObjectField(
                attr="annotations",
                multi=True,
                properties={
                    "term": string_field("term"),
                    "relation": string_field("relation"),
                    "collection": string_field("collection"),
                    "description": text_field("description"),
                    "label": string_field("label")
                }
            )

@registry.register_document
class InfoNodeDocument(Document):
    # pk = fields.IntegerField() not sure, maybe needed
    sid = string_field('sid')
    name = string_field('name')
    url_slug = string_field('url_slug')
    description = string_field('description')
    creator = string_field("creator_username")
    annotations = annotation_field
    synonyms = string_field('synonym_names', multi=True) #todo: this might be wrong
    parents = ObjectField(properties={
        'sid': string_field('sid'),
        'url_slug': string_field('url_slug')
    }, multi=True)
    ntype = string_field('ntype')

    #measurement type
    measurement_type = ObjectField(
        properties={
            "choices": ObjectField(
                attr="choices",
                multi=True,
                properties={
                    "name": string_field("name"),
                    "description": text_field('description'),
                    "annotations": annotation_field
                }
            ),
            "units":ObjectField(
                attr="units",
                multi=True,
                properties={
                    "name": string_field("name"), #todo:this tooo
                })
        }
    )
    #substance
    substance =  ObjectField(
        properties={

            "chebi": string_field('chebi'),
            "mass": string_field('mass'),
            "charge": string_field('charge'),
            "formula": string_field('formula'),

        })


    class Django:
        model = InfoNode
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False

    class Index:
        name = 'info_node'
        settings = elastic_settings

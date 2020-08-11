from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from .models import InfoNode
from ..documents import string_field, elastic_settings, ObjectField, text_field, basic_object

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

small_info_node_properties = {
    'sid': string_field('sid'),
    'label': string_field('label'),
    'name': string_field('name'),
    "description": text_field('description'),
    "annotations": annotation_field,
}


@registry.register_document
class InfoNodeDocument(Document):
    sid = string_field('sid')
    name = string_field('name')
    label = string_field('label')
    deprecated = fields.BooleanField()
    url_slug = string_field('url_slug')
    description = string_field('description')
    annotations = annotation_field
    synonyms = basic_object("synonyms", multi=True)
    #synonyms = string_field('synonym_names', multi=True)  # todo: this might be wrong
    parents = ObjectField(properties=small_info_node_properties, multi=True)
    ntype = string_field('ntype')
    dtype = string_field('dtype')
    xrefs = ObjectField(
        properties=
                          {
                              "name": string_field("name"),
                              "accession":string_field("accession"),
                              "url":string_field("url")

                          }, multi=True)


    # measurement type
    measurement_type = ObjectField(
        properties={
            "choices": ObjectField(
                attr="choices",
                multi=True,
                properties=small_info_node_properties
            ),
            "units": basic_object("units", multi=True)
        }
    )
    # substance
    substance = ObjectField(
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

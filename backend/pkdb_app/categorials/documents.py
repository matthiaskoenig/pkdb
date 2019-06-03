from django_elasticsearch_dsl import DocType, Index, fields
from ..documents import string_field, elastic_settings, ObjectField
from .models import MeasurementType



measurement_type_index = Index("measurement_types")
measurement_type_index.settings(**elastic_settings)

@measurement_type_index.doc_type
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
            "name":string_field("name"),
            "annotations":ObjectField(
                attr="annotations",
                multi=True,
                properties={
                    "name":string_field("name"),
                    "relation":string_field("relation"),
                    "collection": string_field("collection")

                }
                )
        }
    )
    annotations = ObjectField(
        attr="annotations",
        multi=True,
        properties={
            "name": string_field("name"),
            "relation": string_field("relation"),
            "collection": string_field("collection")

        }
    )
    creator = string_field("creator_username")
    description = string_field('description')


    class Meta(object):
        model = MeasurementType
        # Ignore auto updating of Elasticsearch when a model is saved
        # or deleted:
        ignore_signals = True
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False
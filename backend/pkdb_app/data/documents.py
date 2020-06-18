from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from pkdb_app.data.models import Dimension

from ..documents import string_field, elastic_settings


# ------------------------------------
# Elastic Output Document
# ------------------------------------


@registry.register_document
class DataAnalysisDocument(Document):
    study_sid = string_field('study_sid')
    study_name = string_field('study_name')

    data_pk = fields.IntegerField('data_pk')
    data_name = string_field('data_name')
    data_type = string_field('data_type')

    subset_pk = fields.IntegerField('subset_pk')
    subset_name = string_field('subset_name')

    data_point_pk = fields.IntegerField('data_point_pk')
    output_pk = fields.IntegerField('output_pk')
    dimension = fields.IntegerField('dimension')

    # for permissions
    access = string_field('access')
    allowed_users = fields.ObjectField(
        attr="allowed_users",
        properties={
            'username': string_field("username")
        },
        multi=True
    )

    class Django:
        model = Dimension
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False

    class Index:
        name = 'data_analysis'
        settings = elastic_settings
        settings['number_of_shards'] = 5
        settings['number_of_replicas'] = 1
        settings['max_result_window'] = 100000


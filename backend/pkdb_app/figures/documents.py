from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from pkdb_app.figures.models import Dimension

from ..documents import string_field, elastic_settings


# ------------------------------------
# Elastic Output Document
# ------------------------------------
"""
@registry.register_document
class FigureDocument(Document):
    pk = fields.IntegerField('pk')
    study = study_field
    datasets = fields.ObjectField(
        attr="allowed_users",
        properties={
            'username': string_field("username")
        },
        multi=True
    )
    
    allowed_users = fields.ObjectField(
        attr="allowed_users",
        properties={
            'username': string_field("username")
        },
        multi=True
    )

    class Django:
        model = Figure
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False


    class Index:
        name = 'figures'
        settings = elastic_settings
        settings['number_of_shards'] = 5
        settings['number_of_replicas'] = 1
        settings['max_result_window'] = 100000
"""

@registry.register_document
class FigureAnalysisDocument(Document):
    study_sid = string_field('study_sid')
    study_name = string_field('study_name')
    output_pk = fields.IntegerField('output_pk')
    figure_pk = fields.IntegerField('figure_pk')
    figure_name = string_field('figure_name')
    dataset_pk = fields.IntegerField('dataset_pk')
    dataset_name = string_field('dataset_name')
    dataset_point_pk = fields.IntegerField('dataset_point_pk')
    d_type = string_field('d_type')
    f_type = string_field('f_type')

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
        name = 'figure_analysis'
        settings = elastic_settings
        settings['number_of_shards'] = 5
        settings['number_of_replicas'] = 1
        settings['max_result_window'] = 100000


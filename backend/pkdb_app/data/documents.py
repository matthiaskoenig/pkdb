from django_elasticsearch_dsl import Document, fields, ObjectField
from django_elasticsearch_dsl.registries import registry
from pkdb_app.data.models import Dimension, SubSet, Data

from ..documents import string_field, elastic_settings, info_node, study_field


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


output_field = dict(
    pk = fields.IntegerField(),
    group = ObjectField(properties={
        'pk': fields.IntegerField(),
        'name': string_field('name'),
        'count': fields.IntegerField(),
    }),
    individual=ObjectField(properties={
        'pk': fields.IntegerField(),
        'name': string_field('name')}),
    interventions=ObjectField(properties={
        'pk': fields.IntegerField(),
        'name': string_field('name') }, multi=True),

    ex=ObjectField(properties={'pk': string_field('pk')}),
    normed=fields.BooleanField(),
    value=fields.FloatField('null_value'),
    mean=fields.FloatField('null_mean'),
    median=fields.FloatField('null_median'),
    min=fields.FloatField('null_min'),
    max=fields.FloatField('null_max'),
    se=fields.FloatField('null_se'),
    sd=fields.FloatField('null_sd'),
    cv=fields.FloatField('null_cv'),
    unit=string_field('unit'),
    time_unit=string_field('time_unit'),
    time=fields.FloatField('null_time'),
    tissue=info_node('i_tissue'),
    method=info_node('i_method'),
    measurement_type=info_node('i_measurement_type'),
    substance=info_node('i_substance'),
    choice=info_node('i_choice'),
    label=string_field('label'))

@registry.register_document
class SubSetDocument(Document):
    pk = fields.IntegerField()
    array = fields.ObjectField(
        attr="data_points",
        properties={
            'point': fields.ObjectField(attr="outputs", properties=output_field)},
        multi=True)
    data_type = string_field('data_type')
    name = string_field('name')
    study = study_field
    study_sid = string_field('study_sid')
    study_name = string_field('study_name')
    access = string_field('access')
    allowed_users = fields.ObjectField(
        attr="allowed_users",

        properties={
            'username': string_field("username")
        },
        multi=True
    )
    def get_queryset(self):
        """Not mandatory but to improve performance we can select related in one sql request"""
        return super(SubSetDocument, self).get_queryset().prefetch_related("data_points__outputs")

    class Django:
        model = SubSet
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False

    class Index:
        name = 'subset'
        settings = elastic_settings
        settings['number_of_shards'] = 5
        settings['number_of_replicas'] = 1
        settings['max_result_window'] = 100000


'''
@registry.register_document
class TimeCourseDocument(Document):
    study_sid = string_field('study_sid')
    study_name = string_field('study_name')
    outputs_pk = fields.ListField('timecourse')
    
    # for permissions
    access = string_field('access')
    allowed_users = fields.ObjectField(
        attr="allowed_users",
        properties={
            'username': string_field("username")
        },
        multi=True
    )

    def get_queryset(self):
        """Not mandatory but to improve performance we can select related in one sql request"""
        return super(TimeCourseDocument, self).get_queryset().filter(data__data_type=Data.DataTypes.Timecourse)  # .prefetch_related("interventions").


    class Django:
        model = SubSet
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False

    class Index:
        name = 'subset'
        settings = elastic_settings
        settings['number_of_shards'] = 5
        settings['number_of_replicas'] = 1
        settings['max_result_window'] = 100000

'''
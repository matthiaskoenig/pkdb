from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from .models import Output, OutputIntervention
from ..documents import string_field, elastic_settings, ObjectField, study_field, info_node


# ------------------------------------
# Elastic Output Document
# ------------------------------------
@registry.register_document
class OutputDocument(Document):
    pk = fields.IntegerField()
    study = study_field
    group = ObjectField(properties={
        'pk': fields.IntegerField(),
        'name': string_field('name'),
        'count': fields.IntegerField(),
    })
    individual = ObjectField(properties={
        'pk': fields.IntegerField(),
        'name': string_field('name')})
    interventions = ObjectField(properties={
        'pk': fields.IntegerField(),
        'name': string_field('name')
    }, multi=True)
    ex = ObjectField(properties={
        'pk': string_field('pk')}
    )
    normed = fields.BooleanField()
    calculated = fields.BooleanField()
    raw = ObjectField(properties={
        'pk': fields.IntegerField()}
    )
    value = fields.FloatField('null_value')
    mean = fields.FloatField('null_mean')
    median = fields.FloatField('null_median')
    min = fields.FloatField('null_min')
    max = fields.FloatField('null_max')
    se = fields.FloatField('null_se')
    sd = fields.FloatField('null_sd')
    cv = fields.FloatField('null_cv')
    unit = string_field('unit')
    time_unit = string_field('time_unit')
    time = fields.FloatField('null_time')
    tissue = info_node('i_tissue')
    method = info_node('i_method')
    measurement_type = info_node('i_measurement_type')
    substance = info_node('i_substance')
    choice = info_node('i_choice')
    label = string_field('label')
    output_type = string_field('output_type')
    access = string_field('access')
    allowed_users = fields.ObjectField(
        attr="allowed_users",
        properties={
            'username': string_field("username")
        },
        multi=True
    )

    class Django:
        model = Output
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False

    def get_queryset(self):
        """Not mandatory but to improve performance we can select related in one sql request"""
        return super(OutputDocument, self).get_queryset()#.prefetch_related("interventions").select_related('study', 'individual__name', 'group').

    class Index:
        name = 'outputs'
        settings = elastic_settings
        settings['number_of_shards'] = 5
        settings['number_of_replicas'] = 1
        settings['max_result_window'] = 500000


@registry.register_document
class OutputInterventionDocument(Document):
    study_sid = string_field('study_sid')
    study_name = string_field('study_name')
    output_pk = fields.IntegerField('output_pk')
    intervention_pk = fields.IntegerField('intervention_pk')
    group_pk = fields.IntegerField('group_pk')
    individual_pk = fields.IntegerField('individual_pk')

    label = string_field('label')
    output_type = string_field('output_type')
    measurement_type = string_field("measurement_type")
    substance = string_field("substance")
    normed = fields.BooleanField()
    calculated = fields.BooleanField()
    method = string_field('method')
    tissue = string_field('tissue')
    time = fields.FloatField('time')
    time_unit = string_field('time_unit')
    unit = string_field('unit')
    choice = string_field('choice')

    # output fields
    value = fields.FloatField('value')
    mean = fields.FloatField('mean')
    median = fields.FloatField('median')
    min = fields.FloatField('min')
    max = fields.FloatField('max')
    se = fields.FloatField('se')
    sd = fields.FloatField('sd')
    cv = fields.FloatField('cv')

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
        model = OutputIntervention
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False

    class Index:
        name = 'outputs_interventions'
        settings = elastic_settings
        settings['number_of_shards'] = 5
        settings['number_of_replicas'] = 1
        settings['max_result_window'] = 500000


    def get_queryset(self):
        """Not mandatory but to improve performance we can select related in one sql request"""
        return super(OutputInterventionDocument, self).get_queryset().select_related('intervention', 'output')

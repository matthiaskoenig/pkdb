from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from ..documents import string_field, elastic_settings, ObjectField
from .models import Output, Timecourse

# ------------------------------------
# Elastic Output Document
# ------------------------------------
@registry.register_document
class OutputDocument(Document):
    pk = fields.IntegerField('pk')
    study = string_field('study_name')
    group = ObjectField(properties={
        'pk': fields.IntegerField(),
        'count': fields.IntegerField(),
        'name': string_field('name')})
    individual = ObjectField(properties={
        'pk': fields.IntegerField(),
        'name': string_field('name')})
    interventions = ObjectField(properties={
        'pk': fields.IntegerField(),
        'name': string_field('name')
    }, multi=True)
    substance = string_field("substance_name")
    choice = string_field("choice")
    ex = ObjectField(properties={
        'pk': string_field('pk')}
        )
    normed = fields.BooleanField()
    calculated = fields.BooleanField()
    raw = ObjectField(properties={
        'pk': fields.IntegerField()}
    )
    timecourse = ObjectField(properties={
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
    tissue = string_field('tissue')
    measurement_type = string_field("measurement_type_name")
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

    class Index:
        name = 'outputs'
        settings = {
            'number_of_shards': 5,
            'number_of_replicas': 1,
            'max_result_window': 40000
        }


# ------------------------------------
# Elastic Timecourse Document
# ------------------------------------
@registry.register_document
class TimecourseDocument(Document):
    study = string_field('study_name')
    pk = fields.IntegerField('pk')
    group = ObjectField(properties={
        'pk': fields.IntegerField(),
        'name': string_field('name'),
        'count': fields.IntegerField()
    })
    individual = ObjectField(properties={
        'pk': fields.IntegerField(),
        'name': string_field('name')})
    interventions = ObjectField(properties={
        'pk': fields.IntegerField(),
        'name': string_field('name')
    }, multi=True)
    substance = string_field("substance_name")
    ex = ObjectField(
        properties={
            'pk': string_field('pk')
        }
    )
    normed = fields.BooleanField()
    raw = ObjectField(properties={
        'pk': fields.IntegerField()}
    )
    pharmacokinetics = ObjectField(properties={
        'pk': fields.IntegerField()},
        multi=True
    )
    value = fields.FloatField('null_value',multi=True)
    mean = fields.FloatField('null_mean', multi=True)
    median = fields.FloatField('null_median', multi=True)
    min = fields.FloatField('null_min', multi=True)
    max = fields.FloatField('null_max', multi=True)
    se = fields.FloatField('null_se', multi=True)
    sd = fields.FloatField('null_sd', multi=True)
    cv = fields.FloatField('null_cv', multi=True)
    unit = string_field('unit')
    time_unit = string_field('time_unit')
    figure = string_field('figure')
    time = fields.FloatField('null_time', multi=True)
    tissue = string_field('tissue')
    measurement_type = string_field("measurement_type_name")
    access = string_field('access')
    allowed_users = fields.ObjectField(
        attr="allowed_users",
        properties={
            'username': string_field("username")
        },
        multi=True
    )

    class Django:
        model = Timecourse
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False

    class Index:
        name = 'timecourses'
        settings = elastic_settings

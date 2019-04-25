from django_elasticsearch_dsl import DocType, Index, fields
from ..documents import string_field, elastic_settings, ObjectField, text_field
from .models import Output, Timecourse

output_index = Index("outputs")
output_settings = {
    'number_of_shards':5,
    'number_of_replicas':1,
    'max_result_window':20000}

output_index.settings(**output_settings)

@output_index.doc_type
class OutputDocument(DocType):
    pk = fields.IntegerField('pk')
    study = string_field('study')
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

    substance = ObjectField(properties={
        'name': string_field('name')}
        )
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
    pktype = string_field("pktype")

    class Meta(object):
            model = Output
            # Ignore auto updating of Elasticsearch when a model is saved
            # or deleted:
            ignore_signals = True
            # Don't perform an index refresh after every update (overrides global setting):
            auto_refresh = False



timecourses_index = Index("timecourses")
timecourses_index.settings(**elastic_settings)

@timecourses_index.doc_type
class TimecourseDocument(DocType):
    study = string_field('study')
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

    substance = ObjectField(properties={
        'name': string_field('name')}
        )
    ex = ObjectField(properties={
        'pk': string_field('pk')}
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

    time = fields.FloatField('null_time',multi=True)
    tissue = string_field('tissue')
    pktype = string_field("pktype")

    #auc_end = fields.FloatField(attr='auc_end')
    #kel = fields.FloatField(attr='kel')

    class Meta(object):
            model = Timecourse
            # Ignore auto updating of Elasticsearch when a model is saved
            # or deleted:
            ignore_signals = True
            # Don't perform an index refresh after every update (overrides global setting):
            auto_refresh = False

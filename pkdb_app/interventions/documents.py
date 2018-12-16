from django_elasticsearch_dsl import DocType, Index, fields
from pkdb_app.documents import string_field, elastic_settings, ObjectField
from pkdb_app.interventions.models import Substance, Intervention, Output, Timecourse



substance_index = Index("substances")
substance_index.settings(**elastic_settings)

@substance_index.doc_type
class SubstanceDocument(DocType):
    pk = fields.IntegerField()
    name = string_field('name')
    class Meta(object):
        model = Substance
        # Ignore auto updating of Elasticsearch when a model is saved
        # or deleted:
        ignore_signals = True
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False



intervention_index = Index("interventions")
intervention_index.settings(**elastic_settings)

@intervention_index.doc_type
class InterventionDocument(DocType):
    pk = fields.IntegerField()
    category =  string_field('category')
    choice = string_field('choice')
    application = string_field('application')
    time_unit = string_field('time_unit')
    time = fields.FloatField()
    substance = ObjectField(properties={
        'name': string_field('name')}
        )
    study = string_field('study')
    route = string_field('route')
    form = string_field('form')
    name = string_field('name')
    final = fields.BooleanField()
    value = fields.FloatField()
    mean = fields.FloatField()
    median = fields.FloatField()
    min = fields.FloatField()
    max = fields.FloatField()
    se = fields.FloatField()
    sd = fields.FloatField()
    cv = fields.FloatField()
    unit = string_field('unit')

    class Meta(object):
        model = Intervention


output_index = Index("outputs")
output_index.settings(**elastic_settings)

@output_index.doc_type
class OutputDocument(DocType):
    pk = fields.IntegerField('pk')
    study = string_field('study')


    group = ObjectField(properties={
        'pk': fields.IntegerField(),
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
    final = fields.BooleanField()
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
    final = fields.BooleanField()
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

    auc_end = fields.FloatField(attr='auc_end')

    kel = fields.FloatField(attr='kel')

    class Meta(object):
            model = Timecourse
            # Ignore auto updating of Elasticsearch when a model is saved
            # or deleted:
            ignore_signals = True
            # Don't perform an index refresh after every update (overrides global setting):
            auto_refresh = False



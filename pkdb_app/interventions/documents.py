from django_elasticsearch_dsl import DocType, Index, fields, DEDField, Object, collections
from elasticsearch_dsl import analyzer

from pkdb_app.interventions.models import Substance, Intervention, Output, Timecourse
from pkdb_app.studies.documents import autocomplete, autocomplete_search
substance_index = Index("substances")
substance_index.settings(number_of_shards=1,
               number_of_replicas=1,)

def string_field(attr):
    return fields.StringField(
        attr=attr,
        fielddata=True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields={'raw': fields.KeywordField()}
        )


@substance_index.doc_type
class SubstanceDocument(DocType):
    pk = fields.IntegerField()
    name = string_field('name')
    class Meta(object):
        model = Substance

intervention_index = Index("interventions")
intervention_index.settings(number_of_shards=1,
               number_of_replicas=1,)


@intervention_index.doc_type
class InterventionDocument(DocType):
    pk = fields.IntegerField()
    category =  string_field('category')
    choice = string_field('choice')
    application = string_field('application')
    time_unit = string_field('time_unit')
    time = fields.FloatField()
    substance = fields.ObjectField(properties={
        'name': string_field('name')}
        )
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
output_index.settings(number_of_shards=1,
               number_of_replicas=1,)


class ObjectField(DEDField, Object):
    def _get_inner_field_data(self, obj, field_value_to_ignore=None):
        data = {}
        if hasattr(self, 'properties'):
            for name, field in self.properties.to_dict().items():
                if not isinstance(field, DEDField):
                    continue

                if field._path == []:
                    field._path = [name]

                data[name] = field.get_value_from_instance(
                    obj, field_value_to_ignore
                )
        else:
            for name, field in self._doc_class._doc_type.mapping.properties._params.get('properties', {}).items(): # noqa
                if not isinstance(field, DEDField):
                    continue

                if field._path == []:
                    field._path = [name]

                data[name] = field.get_value_from_instance(
                    obj, field_value_to_ignore
                )

        return data

    def get_value_from_instance(self, instance, field_value_to_ignore=None):
        objs = super(ObjectField, self).get_value_from_instance(
            instance, field_value_to_ignore
        )

        if objs is None:
            return None
        if isinstance(objs, collections.Iterable):
            return [
                self._get_inner_field_data(obj, field_value_to_ignore)
                for obj in objs if obj != field_value_to_ignore
            ]

        return self._get_inner_field_data(objs, field_value_to_ignore)


@output_index.doc_type
class OutputDocument(DocType):
    pk = fields.IntegerField('pk')

    group = ObjectField(properties={
        'pk': fields.IntegerField(),
        'name': string_field('name')})

    individual = ObjectField(properties={
        'pk': fields.IntegerField(),
        'name': string_field('name')})

    interventions = ObjectField(properties={
        'pk': fields.IntegerField()}, multi=True)

    substance = fields.ObjectField(properties={
        'name': string_field('name')}
        )
    ex = fields.ObjectField(properties={
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


timecourses_index = Index("timecourses")
timecourses_index.settings(number_of_shards=1,
               number_of_replicas=1,)




@timecourses_index.doc_type
class TimecourseDocument(DocType):
    pk = fields.IntegerField('pk')

    group = ObjectField(properties={
        'pk': fields.IntegerField(),
        'name': string_field('name')})

    individual = ObjectField(properties={
        'pk': fields.IntegerField(),
        'name': string_field('name')})

    interventions = ObjectField(properties={
        'pk': fields.IntegerField()}, multi=True)

    substance = fields.ObjectField(properties={
        'name': string_field('name')}
        )
    ex = fields.ObjectField(properties={
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
    time = fields.FloatField('null_time',multi=True)
    tissue = string_field('tissue')
    pktype = string_field("pktype")

    class Meta(object):
            model = Timecourse



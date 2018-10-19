from elasticsearch_dsl import analyzer
from django_elasticsearch_dsl import DocType, Index, fields
from pkdb_app.subjects.models import Individual, Characteristica, Group
from pkdb_app.interventions.documents import string_field, ObjectField

# Name of the Elasticsearch index
individuals_index = Index("individuals")

# See Elasticsearch Indices API reference for available settings
individuals_index.settings(
    number_of_shards=1,
    number_of_replicas=1
)

html_strip = analyzer(
    'html_strip',
    tokenizer="standard",
    filter=["standard", "lowercase", "stop", "snowball"],
    char_filter=["html_strip"]
)

@individuals_index.doc_type
class IndividualDocument(DocType):
    """Individual elastic search document"""
    pk = fields.IntegerField(attr='pk')

    name = string_field('name')
    group = ObjectField(properties={
        'name': string_field('name'),
        'pk':fields.IntegerField('pk'),
    })

    study = ObjectField(properties={
        'name': string_field('name'),
        'pk':fields.IntegerField('pk'),
        'sid': fields.IntegerField('sid')

    })
    ex = ObjectField(properties={
        'pk':fields.IntegerField('pk')
    })

    characteristica_all_final = fields.ObjectField(
        properties={
            'pk': fields.IntegerField(),
            'category': string_field('category'),
            'choice': string_field('choice'),
            'ctype' : string_field('ctype'),
            'value' : fields.FloatField(),
            'mean' : fields.FloatField(),
            'median' : fields.FloatField(),
            'min' : fields.FloatField(),
            'max' : fields.FloatField(),
            'se' : fields.FloatField(),
            'sd' : fields.FloatField(),
            'cv' : fields.FloatField(),
            'unit' : string_field('unit'),
            'count': fields.IntegerField('count'),

        },
        multi = True)

    class Meta:
        model=Individual

# Name of the Elasticsearch index
group_index = Index("groups")

# See Elasticsearch Indices API reference for available settings
group_index.settings(
    number_of_shards=1,
    number_of_replicas=1
)

@group_index.doc_type
class GroupDocument(DocType):
    """Individual elastic search document"""
    pk = fields.IntegerField(attr='pk')
    name = string_field('name')
    count = fields.IntegerField(attr='count')
    parent = ObjectField(properties={
        'name': string_field('name'),
        'pk': fields.IntegerField('pk'),
    })


    study = ObjectField(properties={
        'name': string_field('name'),
        'pk': fields.IntegerField('pk'),
        'sid': fields.IntegerField('sid')

    })
    ex = ObjectField(properties={
        'pk': fields.IntegerField('pk')
    })

    characteristica_all_final = fields.ObjectField(
        properties={
            'pk': fields.IntegerField(),
            'category': string_field('category'),
            'choice': string_field('choice'),
            'ctype': string_field('ctype'),
            'value': fields.FloatField('value'),
            'mean': fields.FloatField(),
            'median': fields.FloatField(),
            'min': fields.FloatField(),
            'max': fields.FloatField(),
            'se': fields.FloatField(),
            'sd': fields.FloatField(),
            'cv': fields.FloatField(),
            'unit': string_field('unit'),
            'count': fields.IntegerField('count'),

        },
        multi=True)


    class Meta:
        model = Group


# Name of the Elasticsearch index
characteristica_index = Index("characteristica")

# See Elasticsearch Indices API reference for available settings
characteristica_index.settings(
    number_of_shards=1,
    number_of_replicas=1
)

@characteristica_index.doc_type
class CharacteristicaDocument(DocType):
    """Characteristica elastic search document"""
    id = fields.IntegerField(attr='id')
    final = fields.BooleanField()

    group_name = fields.StringField(
        attr='group_name',
        fields={
            'raw': fields.StringField(analyzer='keyword'),

        }
    )

    group_pk = fields.IntegerField(attr='group_id')

    individual_name = fields.StringField(
        attr='individual_name',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )
    individual_pk = fields.IntegerField(attr='individual_id')

    category = fields.StringField(
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )

    choice = fields.StringField(
        fields={
            'raw': fields.StringField(analyzer='keyword'),

        }
    )
    ctype = fields.StringField(
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )
    unit = fields.StringField(
        fields={
            'raw': fields.StringField(analyzer='keyword'),

        }
    )

    count = fields.IntegerField()
    value = fields.FloatField(attr='value')
    mean = fields.FloatField(attr='mean')
    median = fields.FloatField(attr='median')
    min = fields.FloatField(attr='min')
    max = fields.FloatField(attr='max')
    se = fields.FloatField(attr='se')
    sd = fields.FloatField(attr='sd')
    cv = fields.FloatField(attr='cv')


    class Meta:
        model=Characteristica
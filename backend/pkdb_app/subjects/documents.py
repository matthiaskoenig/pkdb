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
        'count': fields.IntegerField('count')
    })

    study = ObjectField(properties={
        'name': string_field('name'),
        'pk':fields.IntegerField('pk'),
        'sid': fields.StringField('sid')

    })
    ex = ObjectField(properties={
        'pk':fields.IntegerField('pk')
    })

    characteristica_all_normed = fields.ObjectField(
        properties={
            'pk': fields.IntegerField(),
            'measurement_type':string_field('measurement_type_name'),
            'substance': string_field('substance_name'),
            'choice': string_field('choice'),
            'value' : fields.FloatField('value'),
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

    access = string_field('access')
    allowed_users = fields.ObjectField(
        attr="allowed_users",
        properties={
            # 'first_name': string_field("first_name"),
            # 'last_name': string_field("last_name"),
            # 'pk': string_field("pk"),
            'username': string_field("username")
        },
        multi=True
    )

    class Meta:
        model=Individual
        # Ignore auto updating of Elasticsearch when a model is saved
        # or deleted:
        ignore_signals = True
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False

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
        'count': fields.IntegerField('count')
    })


    study = ObjectField(properties={
        'name': string_field('name'),
        'pk': fields.IntegerField('pk'),
        'sid': fields.StringField('sid')

    })
    ex = ObjectField(properties={
        'pk': fields.IntegerField('pk')
    })

    characteristica_all_normed = fields.ObjectField(
        properties={
            'pk': fields.IntegerField(),
            'measurement_type':string_field('measurement_type_name'),
            'substance': string_field('substance_name'),
            'choice': string_field('choice'),
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

    access = string_field('access')
    allowed_users = fields.ObjectField(
        attr="allowed_users",
        properties={
            # 'first_name': string_field("first_name"),
            # 'last_name': string_field("last_name"),
            # 'pk': string_field("pk"),
            'username': string_field("username")
        },
        multi=True
    )


    class Meta:
        model = Group
        # Ignore auto updating of Elasticsearch when a model is saved
        # or deleted:
        ignore_signals = True
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False


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

    measurement_type = fields.StringField(
        attr='measurement_type_name',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )

    choice = fields.StringField(
        fields={
            'raw': fields.StringField(analyzer='keyword'),

        }
    )

    unit = fields.StringField(
        fields={
            'raw': fields.StringField(analyzer='keyword'),

        }
    )

    substance = fields.StringField(
        attr='substance_name',
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

    normed = fields.BooleanField()
    raw = ObjectField(properties={
        'pk': fields.IntegerField()}
    )

    access = string_field('access')
    allowed_users = fields.ObjectField(
        attr="allowed_users",
        properties={
            # 'first_name': string_field("first_name"),
            # 'last_name': string_field("last_name"),
            # 'pk': string_field("pk"),
            'username': string_field("username")
        },
        multi=True
    )


    class Meta:
        model=Characteristica
        # Ignore auto updating of Elasticsearch when a model is saved
        # or deleted:
        ignore_signals = True
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False
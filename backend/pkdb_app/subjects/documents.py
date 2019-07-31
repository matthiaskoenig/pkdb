from elasticsearch_dsl import analyzer
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from pkdb_app.subjects.models import Individual, Characteristica, Group
from pkdb_app.interventions.documents import string_field, ObjectField
from ..documents import elastic_settings


html_strip = analyzer(
    'html_strip',
    tokenizer="standard",
    filter=["standard", "lowercase", "stop", "snowball"],
    char_filter=["html_strip"]
)

characteristica_object_field = fields.ObjectField(
        properties={
            'pk': fields.IntegerField(),
            'measurement_type': string_field('measurement_type_name'),
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
        multi=True
    )


# ------------------------------------
# Elastic Individual Document
# ------------------------------------
@registry.register_document
class IndividualDocument(Document):
    """Individual elastic search document"""
    pk = fields.IntegerField(attr='pk')
    name = string_field('name')
    group = ObjectField(
        properties={
            'name': string_field('name'),
            'pk': fields.IntegerField('pk'),
            'count': fields.IntegerField('count')
        }
    )
    study = string_field('study_name')
    ex = ObjectField(
        properties={
            'pk': fields.IntegerField('pk')
        }
    )
    characteristica_all_normed = characteristica_object_field
    access = string_field('access')
    allowed_users = fields.ObjectField(
        attr="allowed_users",
        properties={
            'username': string_field("username")
        },
        multi=True
    )

    class Django:
        model = Individual
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False

    class Index:
        name = 'individuals'
        settings = elastic_settings


# ------------------------------------
# Elastic Group Document
# ------------------------------------
@registry.register_document
class GroupDocument(Document):
    """ Elastic Group Document """
    pk = fields.IntegerField(attr='pk')
    name = string_field('name')
    count = fields.IntegerField(attr='count')
    parent = ObjectField(properties={
        'name': string_field('name'),
        'pk': fields.IntegerField('pk'),
        'count': fields.IntegerField('count')
    })
    study = string_field('study_name')
    ex = ObjectField(properties={
        'pk': fields.IntegerField('pk')
    })
    characteristica_all_normed = characteristica_object_field
    access = string_field('access')
    allowed_users = fields.ObjectField(
        attr="allowed_users",
        properties={
            'username': string_field("username")
        },
        multi=True
    )

    class Django:
        model = Group
        # Ignore auto updating of Elasticsearch when a model is saved
        # or deleted:
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False

    class Index:
        name = 'groups'
        settings = elastic_settings


# ------------------------------------
# Elastic Characteristica Document
# ------------------------------------
@registry.register_document
class CharacteristicaDocument(Document):
    """ Characteristica elastic search document. """
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
            'username': string_field("username")
        },
        multi=True
    )

    class Django:
        model = Characteristica
        # Ignore auto updating of Elasticsearch when a model is saved/deleted:
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False

    class Index:
        name = "characteristica"
        settings = elastic_settings

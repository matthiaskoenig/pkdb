from elasticsearch_dsl import analyzer
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from pkdb_app.subjects.models import Individual, Characteristica, Group, GroupCharacteristica, IndividualCharacteristica
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

    def get_queryset(self):
        """Not mandatory but to improve performance we can select related in one sql request"""
        return super(GroupDocument, self).get_queryset().select_related(
            'ex__groupset__study','parent').prefetch_related("characteristica")


# ------------------------------------
# Elastic Characteristica Document
# ------------------------------------
@registry.register_document
class CharacteristicaDocument(Document):
    """ Characteristica elastic search document. """
    id = fields.IntegerField(attr='id')
    raw_pk = string_field('raw_pk')

    study_name = string_field('study_name')
    study_sid = string_field('study_sid')
    subject_type = string_field('subject_type')

    # group related
    group_pk = fields.IntegerField(attr='group_pk')
    group_name = fields.StringField(
        attr='group_name',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )
    group_count = fields.IntegerField(attr='group_count')
    group_parent_pk = fields.IntegerField(
        attr='group_parent_pk',
    )
    #individual_related
    individual_name = fields.StringField(
        attr='individual_name',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )
    individual_pk = fields.IntegerField(attr='individual_pk')
    individual_group_pk = fields.IntegerField(attr='individual_group_pk')
    ###

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
        settings = {**elastic_settings, 'max_result_window': 50000}


    def get_queryset(self):
        """Not mandatory but to improve performance we can select related in one sql request"""
        return super(CharacteristicaDocument, self).get_queryset().select_related(
            'group','individual')
# Elastic Characteristica Document
# ------------------------------------


@registry.register_document
class GroupCharacteristicaDocument(Document):
    """ Characteristica elastic search document. """
    study_sid = string_field('study_sid')
    study_name = string_field('study_name')


    # group related
    group_pk = fields.IntegerField(attr='group_pk')
    group_name = fields.StringField(
        attr='group_name',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )
    group_count = fields.IntegerField(attr='group_count')
    group_parent_pk = fields.IntegerField(
        attr='group_parent_pk',
    )
    characteristica_pk = fields.IntegerField(
        attr='characteristica_pk',
    )
    count = fields.IntegerField()

    measurement_type = fields.StringField(
        attr='measurement_type',
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
        attr='substance',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )
    value = fields.FloatField(attr='value')
    mean = fields.FloatField(attr='mean')
    median = fields.FloatField(attr='median')
    min = fields.FloatField(attr='min')
    max = fields.FloatField(attr='max')
    se = fields.FloatField(attr='se')
    sd = fields.FloatField(attr='sd')
    cv = fields.FloatField(attr='cv')

    access = string_field('access')
    allowed_users = fields.ObjectField(
        attr="allowed_users",
        properties={
            'username': string_field("username")
        },
        multi=True
    )

    class Django:
        model = GroupCharacteristica
        # Ignore auto updating of Elasticsearch when a model is saved/deleted:
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False

    class Index:
        name = "group_characteristica"
        settings = {**elastic_settings, 'max_result_window': 50000}


    def get_queryset(self):
        """Not mandatory but to improve performance we can select related in one sql request"""
        return super(GroupCharacteristicaDocument, self).get_queryset().select_related(
            'group','characteristica')

@registry.register_document
class IndividualCharacteristicaDocument(Document):
    """ Characteristica elastic search document. """
    study_sid = string_field('study_sid')
    study_name = string_field('study_name')


    # individual related
    individual_pk = fields.IntegerField(attr='individual_pk')
    individual_name = fields.StringField(
        attr='individual_name',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )
    individual_group_pk = fields.IntegerField(
        attr='individual_group_pk',
    )
    characteristica_pk = fields.IntegerField(
        attr='characteristica_pk',
    )
    count = fields.IntegerField()

    measurement_type = fields.StringField(
        attr='measurement_type',
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
        attr='substance',
        fields={
            'raw': fields.StringField(analyzer='keyword'),
        }
    )
    value = fields.FloatField(attr='value')
    mean = fields.FloatField(attr='mean')
    median = fields.FloatField(attr='median')
    min = fields.FloatField(attr='min')
    max = fields.FloatField(attr='max')
    se = fields.FloatField(attr='se')
    sd = fields.FloatField(attr='sd')
    cv = fields.FloatField(attr='cv')

    access = string_field('access')
    allowed_users = fields.ObjectField(
        attr="allowed_users",
        properties={
            'username': string_field("username")
        },
        multi=True
    )

    class Django:
        model = IndividualCharacteristica
        # Ignore auto updating of Elasticsearch when a model is saved/deleted:
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False

    class Index:
        name = "individual_characteristica"
        settings = {**elastic_settings, 'max_result_window': 50000}


    def get_queryset(self):
        """Not mandatory but to improve performance we can select related in one sql request"""
        return super(IndividualCharacteristicaDocument, self).get_queryset().select_related(
            'individual','characteristica')

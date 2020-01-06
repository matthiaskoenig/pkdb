from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from pkdb_app.documents import autocomplete, autocomplete_search, elastic_settings, string_field, text_field, \
    ObjectField

from pkdb_app.studies.models import Reference, Study


def common_setfields(model, attr=None):
    if attr is None:
        attr = model
    return ObjectField(
        properties={
            "descriptions": ObjectField(
                properties={
                    'text': text_field("text"),
                    'pk': fields.IntegerField()
                },
                multi=True),

            model: ObjectField(
                attr=attr,
                properties={
                    "pk": fields.FloatField(),
                }
            ),
            "comments": fields.ObjectField(
                properties={
                    'text': text_field("text"),
                    'user': fields.ObjectField(
                        properties={
                            'first_name': string_field("first_name"),
                            'last_name': string_field("last_name"),
                            'pk': string_field("last_name"),
                            'username': string_field("username"),
                        }
                    )
                },
                multi=True
            )
        }
    )


# ------------------------------------
# Elastic Reference Document
# ------------------------------------
@registry.register_document
class ReferenceDocument(Document):
    pk = fields.IntegerField(attr='pk')
    sid = string_field(attr='sid')
    pmid = string_field(attr='pmid')
    study = ObjectField(properties={
        "pk": fields.IntegerField(),
        "sid": string_field('sid'),
        "name": string_field('name'),
        "licence": string_field("licence"),
        "creator": fields.ObjectField(
            properties={
                'first_name': string_field("first_name"),
                'last_name': string_field("last_name"),
                'pk': string_field("pk"),
                'username': string_field("username"),
            }
        ),
        "curators": fields.ObjectField(
            attr="ratings",
            properties={
                'first_name': string_field("user.first_name"),
                'last_name': string_field("user.last_name"),
                'pk': string_field("user.pk"),
                'username': string_field("user.username"),
                'rating': fields.FloatField(attr='rating')

            },
            multi=True
        ),
        "collaborators": fields.ObjectField(
            attr="collaborators",
            properties={
                'first_name': string_field("first_name"),
                'last_name': string_field("last_name"),
                'pk': string_field("pk"),
                'username': string_field("username")

            },
            multi=True
        )
    })
    name = string_field("name")
    doi = string_field("doi")
    title = string_field("title")
    abstract = text_field("abstract")
    journal = text_field("journal")
    date = fields.DateField()
    pdf = fields.FileField(fielddata=True)

    authors = ObjectField(properties={
        'first_name': string_field("first_name"),
        'last_name': string_field("last_name"),
        'pk': fields.IntegerField(),
    })

    class Django:
        model = Reference
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = True
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False

    class Index:
        name = 'references'
        settings = elastic_settings


# ------------------------------------
# Elastic Study Document
# ------------------------------------
@registry.register_document
class StudyDocument(Document):
    id = fields.TextField(attr='sid')
    pk = fields.TextField(attr='sid')
    sid = string_field(attr='sid')
    pkdb_version = fields.IntegerField(attr='pkdb_version')
    descriptions = ObjectField(
        properties={
            'text': text_field("text"),
            'pk': fields.IntegerField()
        },
        multi=True
    )
    comments = fields.ObjectField(
        properties={
            'text': text_field("text"),
            'user': fields.ObjectField(
                properties={
                    'first_name': string_field("first_name"),
                    'last_name': string_field("last_name"),
                    'pk': string_field("last_name"),
                    'username': string_field("username"),
                }
            )
        },
        multi=True
    )
    creator = fields.ObjectField(
        properties={
            'first_name': string_field("first_name"),
            'last_name': string_field("last_name"),
            'pk': string_field("pk"),
            'username': string_field("username"),
        }
    )
    name = string_field("name")
    licence = string_field("licence")
    access = string_field("access")
    reference = ObjectField(
        properties={
            'sid': string_field(attr='sid'),
            'pk': fields.IntegerField(attr='pk'),
            'name': string_field(attr="name")
        }
    )
    curators = fields.ObjectField(
        attr="ratings",
        properties={
            'first_name': string_field("user.first_name"),
            'last_name': string_field("user.last_name"),
            'pk': string_field("user.pk"),
            'username': string_field("user.username"),
            'rating': fields.FloatField(attr='rating')
        },
        multi=True
    )
    collaborators = fields.ObjectField(
        attr="collaborators",
        properties={
            'first_name': string_field("first_name"),
            'last_name': string_field("last_name"),
            'pk': string_field("pk"),
            'username': string_field("username")

        },
        multi=True
    )
    substances = string_field(attr="get_substances", multi=True)
    files = ObjectField(
        attr="files_ordered",
        properties={
            'pk': fields.IntegerField(),
            'file': fields.TextField(
                attr="file.url",
                fielddata=True,
                analyzer=autocomplete,
                search_analyzer=autocomplete_search,
                fields={
                    'raw': fields.KeywordField(),
                }
            ),
            'name': fields.TextField(
                fielddata=True,
                analyzer=autocomplete,
                search_analyzer=autocomplete_search,
                fields={
                    'raw': fields.KeywordField(),
                }
            ),
            'timecourses': ObjectField(
                properties={
                    'pk': fields.IntegerField(multi=True),
                },
                multi=True
            )
        },
        multi=True
    )

    groupset = common_setfields("groups")
    individualset = common_setfields("individuals")
    interventionset = common_setfields("interventions", "interventions_normed")

    outputset = ObjectField(
        properties={
            "descriptions": ObjectField(
                properties={
                    'text': text_field("text"),
                    'pk': fields.IntegerField()
                },
                multi=True
            ),
            # "count_outputs" : fields.FloatField(),
            "outputs": ObjectField(
                attr="outputs_normed",
                properties={
                    "pk": fields.FloatField(),
                }
            ),
            # "count_timecourses": fields.FloatField(),
            "timecourses": ObjectField(
                attr="timecourses_normed",
                properties={
                    "pk": fields.FloatField(),
                }
            ),
            "comments": fields.ObjectField(
                properties={
                    'text': text_field("text"),
                    'user': fields.ObjectField(
                        properties={
                            'first_name': string_field("first_name"),
                            'last_name': string_field("last_name"),
                            'pk': string_field("last_name"),
                            'username': string_field("username"),
                        }
                    )
                },
                multi=True
            )
        }
    )
    group_count = fields.IntegerField()
    individual_count = fields.IntegerField()
    intervention_count = fields.IntegerField()
    output_count = fields.IntegerField()
    output_calculated_count = fields.IntegerField()
    timecourse_count = fields.IntegerField()

    class Django:
        model = Study
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = True
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False

    class Index:
        name = 'studies'
        settings = elastic_settings

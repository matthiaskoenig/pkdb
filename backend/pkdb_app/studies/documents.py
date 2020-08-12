from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from pkdb_app.documents import autocomplete, autocomplete_search, elastic_settings, string_field, text_field, \
    ObjectField, study_field, info_node
from pkdb_app.studies.models import Reference, Study

comments_field = fields.ObjectField(
    properties={
        'pk': fields.IntegerField(),
        'username': string_field("username"),
        'text': text_field("text"),
    },
    multi=True
)

descriptions_field = ObjectField(
    properties={
        'text': text_field("text"),
        'pk': fields.IntegerField()
    },
    multi=True)


def common_setfields(model, attr=None):
    if attr is None:
        attr = model
    return ObjectField(
        properties={
            "descriptions": descriptions_field,
            model: ObjectField(
                attr=attr,
                properties={
                    "pk": fields.FloatField(),
                }
            ),
            "comments": comments_field,
        }
    )

# ------------------------------------
# Elastic Reference Document
# ------------------------------------
# TODO: add permissions like on all other elastic documents.
@registry.register_document
class ReferenceDocument(Document):
    pk = fields.IntegerField(attr='pk')
    sid = string_field(attr='sid')
    pmid = string_field(attr='pmid')
    study = study_field,
    name = string_field("name")
    doi = string_field("doi")
    title = string_field("title")
    abstract = text_field("abstract")
    journal = text_field("journal")
    date = fields.DateField()
    authors = ObjectField(
        properties={
                       'pk': fields.IntegerField(),
                       'first_name': string_field("first_name"),
                       'last_name': string_field("last_name"),
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
    #id = fields.TextField(attr='sid')
    pk = fields.IntegerField()
    sid = string_field(attr='sid')
    name = string_field("name")
    licence = string_field("licence")
    access = string_field("access")
    date = fields.DateField()

    descriptions = descriptions_field
    comments = comments_field

    group_count = fields.IntegerField()
    individual_count = fields.IntegerField()
    intervention_count = fields.IntegerField()
    output_count = fields.IntegerField()
    output_calculated_count = fields.IntegerField()

    creator = fields.ObjectField(
        properties={
            'pk': string_field("pk"),
            'username': string_field("username"),
            'first_name': string_field("first_name"),
            'last_name': string_field("last_name"),
        }
    )
    reference = ObjectField(
        properties={
            "pk": fields.IntegerField(attr='pk'),
            "sid": string_field(attr='sid'),
            "pmid": string_field(attr='pmid'),
            "study": study_field,
            "name": string_field("name"),
            "doi": string_field("doi"),
            "title": string_field("title"),
            "abstract": text_field("abstract"),
            "journal": text_field("journal"),
            "date": fields.DateField(),

            "authors": ObjectField(
                properties={
                               'pk': fields.IntegerField(),
                               'first_name': string_field("first_name"),
                               'last_name': string_field("last_name"),
                           })
        }
    )
    reference_date = fields.DateField()

    curators = fields.ObjectField(
        attr="ratings",
        properties={
            'pk': string_field("user.pk"),
            'rating': fields.FloatField(attr='rating'),
            'username': string_field("user.username"),
            'first_name': string_field("user.first_name"),
            'last_name': string_field("user.last_name"),
        },
        multi=True
    )
    collaborators = fields.ObjectField(
        attr="collaborators",
        properties={
            'pk': string_field("pk"),
            'username': string_field("username"),
            'first_name': string_field("first_name"),
            'last_name': string_field("last_name"),
        },
        multi=True
    )
    substances = info_node(attr="get_substances", multi=True)
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
            )
        },
        multi=True
    )

    groupset = common_setfields("groups")
    individualset = common_setfields("individuals")
    interventionset = common_setfields("interventions", "interventions_normed")

    outputset = ObjectField(
        properties={
            "descriptions": descriptions_field,
            "comments": comments_field,
            "outputs": ObjectField(
                attr="outputs_normed",
                properties={
                    "pk": fields.FloatField(),
                }
            )
        }
    )
    dataset = common_setfields("data")


    class Django:
        model = Study
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = True
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False

    class Index:
        name = 'studies'
        settings = elastic_settings

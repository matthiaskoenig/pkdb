from django_elasticsearch_dsl import DocType, Index, fields
from pkdb_app.documents import autocomplete, autocomplete_search, elastic_settings, string_field, text_field, \
    ObjectField
from pkdb_app.interventions.models import Substance, InterventionSet, OutputSet, Timecourse, Intervention, Output
from pkdb_app.studies.models import Reference, Study, Keyword

# Elastic Reference
from pkdb_app.subjects.models import GroupSet, IndividualSet, Group, Individual

reference_index = Index("references")
reference_index.settings(**elastic_settings)


@reference_index.doc_type
class ReferenceDocument(DocType):
    pk = fields.IntegerField(attr='pk')
    sid = string_field(attr='sid')
    pmid = string_field(attr='pmid')
    study = ObjectField(properties={
        "pk": fields.IntegerField(),
        "name": string_field('name'),
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

    class Meta(object):
        model = Reference
        # Ignore auto updating of Elasticsearch when a model is saved
        # or deleted:
        ignore_signals = True
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False


# Elastic Study
study_index = Index("studies")
study_index.settings(**elastic_settings)


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
            # "count" : fields.FloatField(),

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
                multi=True)
        }
    )


@study_index.doc_type
class StudyDocument(DocType):
    pk = fields.IntegerField(attr='pk')
    sid = string_field(attr='sid')
    pkdb_version = fields.IntegerField(attr='pkdb_version')

    descriptions = ObjectField(
        properties={
            'text': text_field("text"),
            'pk': fields.IntegerField()
        },
        multi=True)

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
        multi=True)
    creator = fields.ObjectField(
        properties={
            'first_name': string_field("first_name"),
            'last_name': string_field("last_name"),
            'pk': string_field("last_name"),
            'username': string_field("username"),
        }
    )
    name = string_field("name")
    licence = string_field("licence")


    reference = ObjectField(properties={
        'sid': fields.IntegerField(attr='sid'),
        'pk': fields.IntegerField(attr='pk'),
        'name': string_field("name")
    })

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
    substances = string_field(attr="substances_name", multi=True)
    keywords = string_field(attr="keywords_name", multi=True)
    files = ObjectField(
        properties={
            'pk': fields.IntegerField(),
            'file': fields.StringField(
                attr="file.url",
                fielddata=True,
                analyzer=autocomplete,
                search_analyzer=autocomplete_search,
                fields={'raw': fields.KeywordField(), }
            ),
            'name': fields.StringField(
                fielddata=True,
                analyzer=autocomplete,
                search_analyzer=autocomplete_search,
                fields={'raw': fields.KeywordField(), }
            ),
            'timecourses': ObjectField(
                properties={
                    'pk': fields.IntegerField(multi=True),
                }, multi=True)
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
                multi=True),
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
                multi=True)
        }
    )
    group_count = fields.IntegerField()
    individual_count = fields.IntegerField()
    intervention_count = fields.IntegerField()
    output_count = fields.IntegerField()
    output_calculated_count = fields.IntegerField()
    timecourse_count = fields.IntegerField()

    class Meta(object):
        model = Study
        related_models = [Substance, Reference, Keyword, Individual, Group, Intervention, Timecourse, Output]
        # Ignore auto updating of Elasticsearch when a model is saved
        # or deleted:
        ignore_signals = True
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False

    def get_instances_from_related(self, related_instance):
        """If related_models is set, define how to retrieve the  instance(s) from the related model.
        The related_models option should be used with caution because it can lead in the index
        to the updating of a lot of items.
        """
        if isinstance(related_instance, Substance):
            return related_instance.studies.all()
        elif isinstance(related_instance, Reference):
            return related_instance.study.all()
        elif isinstance(related_instance, Keyword):
            return related_instance.studies.all()
        elif isinstance(related_instance, Individual):
            return related_instance.study

    # Elastic Study


keyword_index = Index("keywords")
keyword_index.settings(**elastic_settings)


@keyword_index.doc_type
class KeywordDocument(DocType):
    name = string_field(attr="name")

    class Meta(object):
        model = Keyword
        # Ignore auto updating of Elasticsearch when a model is saved
        # or deleted:
        ignore_signals = True
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False

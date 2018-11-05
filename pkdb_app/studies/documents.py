from django_elasticsearch_dsl import DocType, Index, fields
from pkdb_app.documents import autocomplete, autocomplete_search, elastic_settings, string_field, text_field, ObjectField
from pkdb_app.interventions.models import Substance
from pkdb_app.studies.models import Reference, Study, Keyword

# Elastic Reference
reference_index = Index("references")
reference_index.settings(**elastic_settings)

@reference_index.doc_type
class ReferenceDocument(DocType):
    pk = fields.IntegerField(attr='pk')
    sid = string_field(attr='sid')
    pmid = string_field(attr='pmid')
    study = ObjectField(properties={
        "pk":fields.IntegerField(),
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
        'pk' : fields.IntegerField(),
    })
    class Meta(object):
        model = Reference

# Elastic Study
study_index = Index("studies")
study_index.settings(**elastic_settings)

def common_setfields(model):
    return ObjectField(
        properties = {
            "descriptions" : ObjectField(
                properties={
                    'text': text_field("text"),
                    'pk': fields.IntegerField()
                },
                multi=True),
            #"count" : fields.FloatField(),

            model: ObjectField(
                properties = {
                    "pk" : fields.FloatField(),
                }
            ),
            "comments" : fields.ObjectField(
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
    pkdb_version= fields.IntegerField(attr='pkdb_version')

    descriptions = ObjectField(
        properties={
            'text': text_field("text"),
            'pk': fields.IntegerField()
        },
        multi=True)

    comments = fields.ObjectField(
        properties={
            'text': text_field("text"),
            'user' : fields.ObjectField(
                properties={
                    'first_name': string_field("first_name"),
                    'last_name': string_field("last_name"),
                    'pk':string_field("last_name"),
                    'username': string_field("username"),
                }
            )
        },
        multi=True)
    creator = fields.ObjectField(
                properties={
                    'first_name': string_field("first_name"),
                    'last_name': string_field("last_name"),
                    'pk':string_field("last_name"),
                    'username': string_field("username"),
                }
            )
    name = string_field("name")
    design = string_field("design")

    reference = ObjectField(properties={
        'sid': fields.IntegerField(attr='sid'),
        'pk':fields.IntegerField(attr='pk'),
        'name': string_field("name")
    })

    curators = fields.ObjectField(
        properties={
            'first_name': string_field("first_name"),
            'last_name': string_field("last_name"),
            'pk': string_field("last_name"),
            'username': string_field("username"),
        },
        multi=True
    )
    substances = string_field(attr="substances_name", multi=True)
    keywords = string_field(attr="keywords_name",multi=True)
    files = ObjectField(
        properties={
            'pk': fields.IntegerField(),
            'file': fields.StringField(
                attr="file.url",
                fielddata=True,
                analyzer=autocomplete,
                search_analyzer=autocomplete_search,
                fields={'raw': fields.KeywordField(),}
            ),
            'name': fields.StringField(
                fielddata=True,
                analyzer=autocomplete,
                search_analyzer=autocomplete_search,
                fields={'raw': fields.KeywordField(),}
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
    interventionset = common_setfields("interventions")
    outputset = ObjectField(
        properties = {
            "descriptions" : ObjectField(
                properties={
                    'text': text_field("text"),
                    'pk': fields.IntegerField()
                },
                multi=True),
            #"count_outputs" : fields.FloatField(),
            "outputs": ObjectField(
                properties = {
                    "pk" : fields.FloatField(),
                }
            ),
            #"count_timecourses": fields.FloatField(),
            "timecourses": ObjectField(
                properties={
                    "pk": fields.FloatField(),
                }
            ),
            "comments" : fields.ObjectField(
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
    timecourse_count = fields.IntegerField()


    class Meta(object):
        model = Study
        related_models = [Substance,Reference,Keyword]

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

    # Elastic Study
keyword_index = Index("keywords")
keyword_index.settings(**elastic_settings)

@keyword_index.doc_type
class KeywordDocument(DocType):
    name = string_field(attr="name")
    class Meta(object):
        model = Keyword

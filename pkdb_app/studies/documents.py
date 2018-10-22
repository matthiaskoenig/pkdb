from django_elasticsearch_dsl import DocType, Index, fields
from elasticsearch_dsl import analyzer, token_filter
from pkdb_app.studies.models import Reference, Study
reference_index = Index("references")
reference_index.settings(number_of_shards=1,
               number_of_replicas=1,)



edge_ngram_filter =  token_filter(
            'edge_ngram_filter',
            type="edge_ngram",
            min_gram=1, max_gram=20)


autocomplete_search = analyzer(
    'autocomplete_search',
    tokenizer="standard",
    filter=["lowercase"],
)


autocomplete = analyzer('autocomplete',
    tokenizer="standard",
    filter=[ "lowercase",edge_ngram_filter],
    char_filter=["html_strip"],
    chars=["letter"],
    token_chars=["letter"])





@reference_index.doc_type
class ReferenceDocument(DocType):
    pk = fields.IntegerField(attr='pk')
    pmid = fields.StringField(attr='pmid',fielddata=True)
    sid = fields.StringField(attr='sid',fielddata=True)
    study_name = fields.StringField(fielddata=True)
    study_pk = fields.StringField(fielddata=True)

    name = fields.StringField(
        fielddata = True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields = {'raw': fields.KeywordField(),
                  'suggest':fields.CompletionField(),
                  }
        )


    doi = fields.StringField(attr='doi',fielddata=True)

    title = fields.TextField(
        fielddata = True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields = {'raw': fields.KeywordField(),
                  'suggest':fields.CompletionField(),
                  })
    abstract = fields.TextField(
        fielddata = True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields={'raw': fields.KeywordField(),
                })

    journal = fields.TextField(
        fielddata = True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields={'raw': fields.KeywordField(),
                'suggest': fields.CompletionField(),
                })
    date = fields.DateField(
    )
    pdf = fields.FileField(fielddata=True)
    authors = fields.ObjectField(properties={
        'first_name': fields.StringField(
            analyzer=autocomplete,
            fields={
                'raw': fields.KeywordField(),
            },),
        'last_name': fields.StringField(
            fielddata = True,
            analyzer=autocomplete,
            fields={
            'raw': fields.KeywordField(),
        }),
        'pk' : fields.IntegerField(),

    })

    class Meta(object):
        model = Reference


study_index = Index("studies")
study_index.settings(number_of_shards=1,
               number_of_replicas=1,)

@study_index.doc_type
class StudyDocument(DocType):
    pk = fields.IntegerField(attr='pk')
    sid = fields.StringField(attr='sid',fielddata=True)
    pkdb_version= fields.IntegerField(attr='pkdb_version')

    descriptions = fields.ObjectField(
        properties={
            'text': fields.StringField(
                analyzer=autocomplete,
                search_analyzer=autocomplete_search,

                fields={
                    'raw': fields.KeywordField(),
                },
            ),
            'pk': fields.IntegerField()

        },
        multi=True)

    comments = fields.ObjectField(
        properties={
            'text': fields.StringField(
                analyzer=autocomplete,
                search_analyzer=autocomplete_search,

                fields={
                    'raw': fields.KeywordField(),
                },
            ),
            'user' : fields.ObjectField(properties={
                'first_name': fields.StringField(
                    analyzer=autocomplete,
                    search_analyzer=autocomplete_search,

                    fields={
                        'raw': fields.KeywordField(),
                    }, ),
                'last_name': fields.StringField(
                    fielddata=True,
                    analyzer=autocomplete,
                    search_analyzer=autocomplete_search,
                    fields={
                        'raw': fields.KeywordField(),
                    }),
                'pk': fields.StringField(
                    fielddata=True,
                    analyzer=autocomplete,
                    fields={
                        'raw': fields.KeywordField(),
                    }),
                'username': fields.StringField(
                    fielddata=True,
                    analyzer=autocomplete,
                    search_analyzer=autocomplete_search,

                    fields={
                        'raw': fields.KeywordField(),
                    })
                ,

            })
        },
        multi=True)


    creator = fields.ObjectField(properties={
        'first_name': fields.StringField(
            analyzer=autocomplete,
            search_analyzer=autocomplete_search,

            fields={
                'raw': fields.KeywordField(),
            }, ),
        'last_name': fields.StringField(
            fielddata=True,
            analyzer=autocomplete,
            search_analyzer=autocomplete_search,
            fields={
                'raw': fields.KeywordField(),
            }),
        'pk': fields.StringField(
            fielddata=True,
            analyzer=autocomplete,
            fields={
                'raw': fields.KeywordField(),
            }),
        'username': fields.StringField(
            fielddata=True,
            analyzer=autocomplete,
            search_analyzer=autocomplete_search,

            fields={
                'raw': fields.KeywordField(),
            })
        ,

    })
    name = fields.StringField(
        fielddata=True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields={'raw': fields.KeywordField(),
                }
    )

    design = fields.StringField(
        fielddata = True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields = {'raw': fields.KeywordField(),
                  })
    reference = fields.ObjectField(properties={
        'sid': fields.IntegerField(attr='sid'),
        'pk':fields.IntegerField(attr='pk'),
        'id': fields.IntegerField(attr='pk')

    })

    curators = fields.ObjectField(
        properties={
            'first_name': fields.StringField(
                analyzer=autocomplete,
                search_analyzer=autocomplete_search,

                fields={'raw': fields.KeywordField(),},
            ),
            'last_name': fields.StringField(
                fielddata=True,
                analyzer=autocomplete,
                search_analyzer=autocomplete_search,

                fields={'raw': fields.KeywordField(),}
            ),
            'pk': fields.StringField(
                fielddata=True,
                analyzer=autocomplete,
                fields={'raw': fields.KeywordField(),}
            ),
            'username': fields.StringField(
                fielddata=True,
                analyzer=autocomplete,
                search_analyzer=autocomplete_search,
                fields={'raw': fields.KeywordField(),}
            ),
        },
        multi=True
    )
    substances = fields.StringField(
        attr= "substances_name",
        fielddata=True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields={'raw': fields.KeywordField(multi=True),
                },
        multi=True,

    )
    keywords = fields.StringField(
        attr="keywords_name",
        fielddata=True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields={'raw': fields.KeywordField(),
                },
        multi=True,
    )

    files = fields.ObjectField(
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
            )
        },
        multi=True
    )
    group_count = fields.FloatField()
    individual_count = fields.FloatField()
    intervention_count = fields.FloatField()
    output_count =  fields.FloatField()
    timecourse_count = fields.FloatField()

    class Meta(object):
        model = Study
from django_elasticsearch_dsl import fields, DEDField, Object, collections
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from elasticsearch_dsl import analyzer, token_filter, Q

from pkdb_app.users.models import PUBLIC
from pkdb_app.users.permissions import user_group

elastic_settings = {
    'number_of_shards': 1,
    'number_of_replicas': 1,
    'max_ngram_diff': 15

}

edge_ngram_filter = token_filter(
    'edge_ngram_filter',
    type="edge_ngram",
    min_gram=1, max_gram=20
)

ngram_filter = token_filter(
    'ngram_filter',
    type="ngram",
    min_gram=1, max_gram=15
)

autocomplete_search = analyzer(
    'autocomplete_search',
    tokenizer="standard",
    filter=["lowercase"],
)

autocomplete = analyzer(
    'autocomplete',
    tokenizer="standard",
    filter=["lowercase", ngram_filter],
    char_filter=["html_strip"],
    chars=["letter"],
    token_chars=["letter"]
)


def string_field(attr, **kwargs):
    return fields.TextField(

        attr=attr,
        fielddata=True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields={'raw': fields.KeywordField()},
        **kwargs
    )

def basic_object(attr, **kwargs):
    return ObjectField(
        attr=attr,
        properties={
            "pk": fields.IntegerField(),
            "name": string_field("name"),
        },
        **kwargs
    )

def info_node(attr, **kwargs):
    return fields.ObjectField(
        attr=attr,
        properties={
           'sid': string_field('sid'),
           'name': string_field('name'),
       },

        **kwargs
    )

study_field = fields.ObjectField(
    attr="study",
    properties={
        'sid': string_field('sid'),
        'name': string_field('name'),
    }
)

def text_field(attr):
    return fields.TextField(
        attr=attr,
        fielddata=True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields={'raw': fields.KeywordField()}
    )


class ObjectField(DEDField, Object):
    """
    FIXME: DOCUMENT ME
    What is this for? I assume to solve some issue with nested ObjectFields.
    This looks copy-pasted from some solution. Please provide short description
    and link to solution.
    """

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
            for name, field in self._doc_class._doc_type.mapping.properties._params.get('properties',
                                                                                        {}).items():  # noqa
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



class AccessView(DocumentViewSet):

    def get_queryset(self):
        search = self.search  # .query()
        # qs = super().get_queryset()
        # return qs
        group = user_group(self.request.user)

        if group in ["admin", "reviewer"]:
            return search.query()

        elif group == "basic":

            qs = search.query(
                Q('term', access__raw=PUBLIC) |
                Q('term', allowed_users__raw=self.request.user.username)
            )

            # )
            # qs = qs.filter(
            #    'term',
            #   **{"access": PUBLIC, "creator":self.request.user}
            # )
            return qs

        elif group == "anonymous":

            qs = search.query(
                'match',
                **{"access__raw": PUBLIC}
            )

            return qs

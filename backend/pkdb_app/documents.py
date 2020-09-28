import operator
from functools import reduce

from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import get_object_or_404
from django_elasticsearch_dsl import fields, DEDField, Object, collections
from django_elasticsearch_dsl_drf.viewsets import BaseDocumentViewSet
from elasticsearch_dsl import analyzer, token_filter, Q
from pkdb_app.studies.models import IdCollection

from pkdb_app.users.models import PUBLIC
from pkdb_app.users.permissions import user_group

elastic_settings = {
    'number_of_shards': 1,
    'number_of_replicas': 1,
    'max_ngram_diff': 15,
    'max_terms_count':65536*4,
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
        required=True,
        attr=attr,
        properties={
           'sid': string_field('sid'),
           'name': string_field('name'),
           'label': string_field('label'),
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

    This document Object fields returns a null for any empty field and not an empty dictionary.
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


UUID_PARAM = openapi.Parameter(
    'uuid',
    openapi.IN_QUERY,
    description="The '/filter/' endpoint returns a UUID. Via the UUID the resulting query can be access.",
    type=openapi.TYPE_STRING,

)


@method_decorator(name='list', decorator=swagger_auto_schema( manual_parameters=[UUID_PARAM]))
class AccessView(BaseDocumentViewSet):
    """Permissions on views."""

    def _get_resource(self):
        resource = self.request.query_params.get("data_type", self.document.Index.name)
        if resource == "timecourse":
            return "timecourses"
        return resource

    def get_queryset(self):
        group = user_group(self.request.user)
        if hasattr(self, "initial_data"):
            id_queries = [Q('term', pk=pk) for pk in self.initial_data]
            if len(id_queries) > 0:
                self.search = self.search.query(reduce(operator.ior, id_queries))
            else:
                # empty query
                return self.search.query('match', access__raw="NOTHING")

        _uuid = self.request.query_params.get("uuid", [])

        if _uuid:
            ids = list(get_object_or_404(IdCollection, uuid=_uuid, resource=self._get_resource()).ids)
            _qs_kwargs = {'values': ids}

            self.search = self.search.query(
                'ids',
                **_qs_kwargs
            )

        if group == "basic":
            return self.search.query(Q('term', access__raw=PUBLIC) | Q('term', allowed_users__raw=self.request.user.username))
        elif group == "anonymous":
            return self.search.query(Q('term', access__raw=PUBLIC))
        elif group in ["admin", "reviewer"]:
            return self.search.query()
        else:
            raise AssertionError("wrong group name")

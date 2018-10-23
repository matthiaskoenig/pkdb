from django_elasticsearch_dsl import  fields, DEDField, Object, collections
from elasticsearch_dsl import analyzer, token_filter


elastic_settings = {'number_of_shards':1,
            'number_of_replicas':1,}


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


def string_field(attr,**kwargs):
    return fields.StringField(

        attr=attr,
        fielddata=True,
        analyzer=autocomplete,
        search_analyzer=autocomplete_search,
        fields={'raw': fields.KeywordField()},
        **kwargs
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
            for name, field in self._doc_class._doc_type.mapping.properties._params.get('properties', {}).items(): # noqa
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
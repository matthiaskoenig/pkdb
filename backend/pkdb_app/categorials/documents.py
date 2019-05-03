from django_elasticsearch_dsl import DocType, Index

from pkdb_app.documents import elastic_settings, string_field
from pkdb_app.categorials.models import Keyword
keyword_index = Index("keywords")
keyword_index.settings(**elastic_settings)


@keyword_index.doc_type
class KeywordDocument(DocType):
    name = string_field(attr="name")

    class Meta(object):
        model = Keyword
        # Ignore auto updating of Elasticsearch when a model is saved
        # or deleted:
        ignore_signals = False
        # Don't perform an index refresh after every update (overrides global setting):
        auto_refresh = False

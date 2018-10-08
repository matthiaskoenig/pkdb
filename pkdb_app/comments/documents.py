from elasticsearch_dsl import analyzer
from django_elasticsearch_dsl import DocType, Index, fields

# Name of the Elasticsearch index
individuals_index = Index("individuals")

# See Elasticsearch Indices API reference for available settings
individuals_index.settings(
    number_of_shards=1,
    number_of_replicas=1
)

html_strip = analyzer(
    'html_strip',
    tokenizer="standard",
    filter=["standard", "lowercase", "stop", "snowball"],
    char_filter=["html_strip"]
)

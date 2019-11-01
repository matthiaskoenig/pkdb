from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from pkdb_app.documents import elastic_settings, string_field, ObjectField, \
    text_field
from pkdb_app.comments.models import Comment, Description


# ------------------------------------
# Elastic Comment Document
# ------------------------------------
@registry.register_document
class CommentDocument(Document):
    pk = fields.IntegerField(attr='pk')
    user = ObjectField(
        properties={
            'first_name': string_field('first_name'),
            'last_name': string_field('last_name'),
        })
    text = text_field('text')
    date_time = fields.DateField()

    class Django:
        model = Comment
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False

    class Index:
        name = 'comments'
        settings = elastic_settings


# ------------------------------------
# Elastic Description Document
# ------------------------------------
@registry.register_document
class DescriptionDocument(Document):
    pk = fields.IntegerField(attr='pk')
    text = text_field('text')

    class Django:
        model = Description
        # Ignore auto updating of Elasticsearch when a model is saved/deleted
        ignore_signals = True
        # Don't perform an index refresh after every update
        auto_refresh = False

    class Index:
        name = 'descriptions'
        settings = elastic_settings

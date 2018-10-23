from django_elasticsearch_dsl import DocType, Index, fields
from pkdb_app.documents import elastic_settings, string_field, ObjectField
from pkdb_app.comments.models import Comment, Description

comments_index = Index("comments")
comments_index.settings(**elastic_settings)

@comments_index.doc_type
class CommentDocument(DocType):
    pk = fields.IntegerField(attr='pk')
    user = ObjectField(
        properties={
        'first_name': string_field('first_name'),
        'last_name': string_field('last_name'),})
    text = string_field('text')
    date_time = fields.DateField()

    class Meta(object):
        model = Comment


descriptions_index = Index("descriptions")
descriptions_index.settings(**elastic_settings)

@descriptions_index.doc_type
class DescriptionDocument(DocType):
    pk = fields.IntegerField(attr='pk')
    text = string_field('text')

    class Meta(object):
        model = Description

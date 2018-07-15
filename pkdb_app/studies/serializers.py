from rest_framework import serializers
from .models import Reference, Author, Study

from ..subjects.serializers import GroupSerializer
from ..subjects.models import Group

BASE_FIELDS = ()

class AuthorSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Author
        fields = ('id', 'first_name', 'last_name')

    def create(self, validated_data):
        author, created = Author.objects.update_or_create(**validated_data)
        return author


class ReferenceSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True, read_only=False)#, queryset=Study.objects.all(), source='studies')

    class Meta:
        model = Reference
        fields = BASE_FIELDS + ('pmid','sid', 'doi', 'title','abstract','journal', 'date', 'authors', 'pdf')


    def create(self, validated_data):
        authors_data = validated_data.pop('authors', [])
        reference, _ = Reference.objects.update_or_create(sid=validated_data["pmid"], defaults=validated_data)

        for author_data in authors_data:
            author, _ = Author.objects.update_or_create(**author_data)
            reference.authors.add(author)
            reference.save()
        return reference



class StudySerializer(serializers.ModelSerializer):
    reference = serializers.PrimaryKeyRelatedField(queryset=Reference.objects.all())
    groups = GroupSerializer(many=True, read_only=False)


    class Meta:
        model = Study
        fields = BASE_FIELDS + ('sid','comment','description', 'groups', 'reference')

    def create(self, validated_data):

        groups_data = validated_data.pop('groups', [])
        study, _ = Study.objects.update_or_create(sid=validated_data["sid"], defaults=validated_data)

        for group in groups_data:
            Group.objects.update_or_create(sid=group["sid"], study=study, defaults=group)


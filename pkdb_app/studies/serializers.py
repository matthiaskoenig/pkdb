from rest_framework import serializers

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from .models import Reference, Author, Study

from ..subjects.serializers import GroupSerializer
from ..subjects.models import Group
from ..serializers import BaseSerializer
from django.shortcuts import get_object_or_404

BASE_FIELDS = ()


class AuthorSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Author
        fields = ('id', 'first_name', 'last_name')

    def create(self, validated_data):
        author, created = Author.objects.update_or_create(**validated_data)
        return author


class ReferenceSerializer(BaseSerializer):
    authors = AuthorSerializer(many=True, read_only=False)#, queryset=Study.objects.all(), source='studies')

    class Meta:
        model = Reference
        fields = BASE_FIELDS + ('pmid', 'sid', 'name', 'doi', 'title','abstract','journal', 'date', 'authors', 'pdf')

    def create(self, validated_data):

        authors_data = validated_data.pop('authors',[])
        reference = Reference.objects.create(**validated_data)

        for author_data in authors_data:
            author, _ = Author.objects.update_or_create(**author_data)
            reference.authors.add(author)
            reference.save()

        return reference

    def update(self, instance, validated_data):
        authors_data = validated_data.pop('authors',[])

        for name, value in validated_data.items():
            setattr(instance, name, value)

        for author_data in authors_data:
            author, _ = Author.objects.update_or_create(**author_data)
            instance.authors.add(author)
            instance.save()

        return instance


class StudySerializer(BaseSerializer):
    #reference = ReferenceSerializer(read_only=False)
    reference = serializers.PrimaryKeyRelatedField(queryset=Reference.objects.all())
    groups = GroupSerializer(many=True, read_only=False)

    class Meta:
        model = Study
        fields = BASE_FIELDS + ('sid','comment','name','description', 'groups', 'reference')

    def create(self, validated_data):

        groups_data = validated_data.pop('groups', [])
        reference = validated_data.pop('reference')

        study, _ = Study.objects.update_or_create(sid=validated_data["sid"], reference=reference, defaults=validated_data,)

        for group in groups_data:
            Group.objects.update_or_create(name=group["name"], study=study, defaults=group)

        study.save()
        return study

    def update(self, instance, validated_data):
        groups_data = validated_data.pop('groups', [])
        for name, value in validated_data.items():
            setattr(instance, name, value)

        for group in groups_data:
            Group.objects.update_or_create(name=group["name"], study=instance, defaults=group)


        return instance

from rest_framework import serializers
from .models import Reference, Author
from ..subjects.models import Group
from ..subjects.serializers import GroupSerializer

BASE_FIELDS = ()

#class InterventionSerializer(serializers.ModelSerializer):


#    class Meta:
#        model = Intervention
#        fields = BASE_FIELDS + ('type', 'study',)


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
    groups = GroupSerializer(many=True, read_only=False)#, queryset=Study.objects.all(), source='studies')

    class Meta:
        model = Reference
        fields = BASE_FIELDS + ('sid', 'groups', 'pmid', 'doi', 'title', 'abstract', 'journal', 'date', 'authors', 'pdf')

    def validate(self, data):
        # TODO: add validation code


        return data

    def create(self, validated_data):
        authors_data = validated_data.pop('authors', [])
        groups_data = validated_data.pop('groups', [])

        reference, _ = Reference.objects.update_or_create(pmid=validated_data["pmid"], defaults=validated_data)

        for author_data in authors_data:
            author, created = Author.objects.update_or_create(**author_data)
            reference.authors.add(author)
            reference.save()

        for group in groups_data:
            Group.objects.update_or_create(sid=group["sid"], reference=reference, defaults=group)

        return reference


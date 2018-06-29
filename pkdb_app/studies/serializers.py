from rest_framework import serializers
from .models import Intervention, Author, Study


BASE_FIELDS = ('comment', 'description',)

class InterventionSerializer(serializers.ModelSerializer):


    class Meta:
        model = Intervention
        fields = BASE_FIELDS + ('type', 'study',)


class AuthorSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()


    class Meta:
        model = Author
        fields = ('id', 'first_name', 'last_name')

    def create(self, validated_data):
        author, created = Author.objects.update_or_create(**validated_data)
        return author


class StudySerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True,read_only=False)#, queryset=Study.objects.all(), source='studies')


    class Meta:
        model = Study
        fields = BASE_FIELDS + ('title', 'pmid', 'authors', 'abstract','file')

    def create(self, validated_data):
        authors_data = validated_data.pop('authors')
        study, _ = Study.objects.update_or_create(pmid=validated_data["pmid"],defaults = validated_data)
        for author_data in authors_data:
            author, created = Author.objects.update_or_create(**author_data)
            study.authors.add(author)
            study.save()

        return study
from rest_framework import serializers
from .models import Intervention, Author, Study


BASE_FIELDS = ('sid', 'comment', 'description',)

class InterventionSerializer(serializers.ModelSerializer):


    class Meta:
        model = Intervention
        fields = BASE_FIELDS + ('type', 'study',)


class AuthorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Author
        fields = ('first_name', 'last_name')

    def create(self, validated_data):
        author, created = Author.objects.update_or_create(**validated_data)
        return author


class StudySerializer(serializers.ModelSerializer):

    class Meta:
        model = Study
        fields = BASE_FIELDS + ('title', 'pmid', 'authors', 'file')

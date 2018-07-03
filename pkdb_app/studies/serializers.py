from rest_framework import serializers
from .models import Reference, Author, Study


BASE_FIELDS = ('comment', 'description',)

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
    authors = AuthorSerializer(many=True,read_only=False)#, queryset=Study.objects.all(), source='studies')

    class Meta:
        model = Reference
        fields = BASE_FIELDS + ('pmid', 'doi', 'title', 'abstract', 'journal','year', 'authors','pdf')

    def create(self, validated_data):
        authors_data = validated_data.pop('authors')
        reference, _ = Reference.objects.update_or_create(pmid=validated_data["pmid"],defaults = validated_data)
        for author_data in authors_data:
            author, created = Author.objects.update_or_create(**author_data)
            reference.authors.add(author)
            reference.save()

        studies_data = validated_data.pop('study')
        for study in studies_data:
            reference.study_set.update_or_create(sid=study["sid"], defaults=study)

        return reference

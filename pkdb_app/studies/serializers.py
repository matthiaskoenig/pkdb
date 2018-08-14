from django.contrib.sites.shortcuts import get_current_site
from rest_framework import serializers

from pkdb_app.utils import update_or_create_multiple, get_or_val_error
from ..interventions.models import Substance, DataFile
from ..interventions.serializers import InterventionSetSerializer, OutputSetSerializer
from ..subjects.serializers import GroupSetSerializer, IndividualSetSerializer
from ..users.models import User
from .models import Reference, Author, Study
from ..serializers import BaseSerializer


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
        fields = ('pmid', 'sid', 'name', 'doi', 'title','abstract', 'journal', 'date', 'authors', 'pdf')

    def create(self, validated_data):
        authors_data = validated_data.pop('authors',[])
        reference = Reference.objects.create(**validated_data)
        update_or_create_multiple(reference,authors_data,"authors")
        reference.save()
        return reference

    def update(self, instance, validated_data):
        authors_data = validated_data.pop('authors',[])
        for name, value in validated_data.items():
            setattr(instance, name, value)
        update_or_create_multiple(instance,authors_data,"authors")
        instance.save()
        return instance



class StudySerializer(BaseSerializer):
    reference = serializers.PrimaryKeyRelatedField(queryset=Reference.objects.all(), required=False, allow_null=True)
    groupset = GroupSetSerializer(read_only=False, required=False,allow_null=True)
    curators = serializers.SlugRelatedField(queryset=User.objects.all(), slug_field='username', many=True,required=False,allow_null=True)
    creator = serializers.SlugRelatedField(queryset=User.objects.all(), slug_field='username',required=False,allow_null=True)
    substances = serializers.SlugRelatedField(queryset=Substance.objects.all(), slug_field='name',required=False, many=True,allow_null=True)
    interventionset = InterventionSetSerializer(read_only=False, required=False,allow_null=True)
    individualset = IndividualSetSerializer(read_only=False, required=False, allow_null=True)
    outputset =OutputSetSerializer(read_only=False, required=False, allow_null=True)
    files = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True, many=True)

    class Meta:
        model = Study
        fields = ('sid',"pkdb_version","creator",'name',"design",'reference',"curators","substances",
                 "groupset","individualset","interventionset","outputset","files")

    def create(self, validated_data):
        related = self.pop_relations(validated_data)

        creator = validated_data.get("creator", None)
        if creator:
            validated_data["creator"] = get_or_val_error(User,username=creator)

        study, _ = Study.objects.update_or_create(sid=validated_data["sid"],
                                                  reference=related["reference"],
                                                  defaults=validated_data,)

        study = self.create_relations(study,related)
        return study

    def update(self, instance, validated_data):

        related = self.pop_relations(validated_data)

        creator = validated_data.get("creator", None)
        if creator:
            validated_data["creator"] = get_or_val_error(User, username=creator)


        for name, value in validated_data.items():
            setattr(instance, name, value)

        instance.save()
        instance = self.create_relations(instance,related)

        return instance


    def to_representation(self, instance):
        rep = super().to_representation(instance)
        current_site = f'http://{get_current_site(self.context["request"]).domain}'

        if "files" in rep:
            rep["files"] = [current_site + file.file.url for file in instance.files.all()]
        return rep



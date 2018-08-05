from rest_framework import serializers

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from pkdb_app.categoricals import SUBSTANCES_DATA
from pkdb_app.interventions.models import Substance, InterventionSet
from pkdb_app.interventions.serializers import SubstanceSerializer, InterventionSetSerializer
from pkdb_app.subjects.serializers import GroupSetSerializer
from pkdb_app.users.models import User
from pkdb_app.users.serializers import UserSerializer
from .models import Reference, Author, Study
from django.core.exceptions import ObjectDoesNotExist
#from ..subjects.serializers import GroupSerializer
from ..subjects.models import Group, GroupSet
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
        fields = BASE_FIELDS + ('pmid', 'sid', 'name', 'doi', 'title','abstract', 'journal', 'date', 'authors', 'pdf')

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
    reference = serializers.PrimaryKeyRelatedField(queryset=Reference.objects.all(), required=False)
    groupset = GroupSetSerializer(read_only=False, required=False)
    curators = serializers.SlugRelatedField(queryset=User.objects.all(), slug_field='username', many=True,required=False)
    creator = serializers.SlugRelatedField(queryset=User.objects.all(), slug_field='username',required=False)
    substances = serializers.SlugRelatedField(queryset=Substance.objects.all(), slug_field='name',required=False, many=True)
    interventionset = InterventionSetSerializer(read_only=False, required=False)

    class Meta:
        model = Study
        fields = BASE_FIELDS + ('sid','name',"creator","pkdb_version","design",'reference',"curators",
                                "groupset", "interventionset","substances")

    def create(self, validated_data):
        interventionset_data = validated_data.pop('interventionset',None)

        substances_data = validated_data.pop('substances', [])
        curators_data = validated_data.pop('curators', [])
        groupset_data = validated_data.pop('groupset', None)
        creator_data = validated_data.pop('creator', None)
        reference = validated_data.pop('reference')


        try:
            creator = User.objects.get(username=creator_data)
        except ObjectDoesNotExist:
            creator = None

        study, _ = Study.objects.update_or_create(sid=validated_data["sid"], reference=reference, creator=creator, defaults=validated_data,)

        if groupset_data is not None:
            groupset = GroupSet.objects.create(**groupset_data)

            groupset.save()
            study.groupset = groupset

        if interventionset_data is not None:
            interventionset = InterventionSet.objects.create(**interventionset_data)
            interventionset.save()
            study.interventionset = interventionset
        study.save()

        for curator_data in curators_data:
            try:
                curator = User.objects.get(username=curator_data)
            except ObjectDoesNotExist:
                curator = None
            study.curators.add(curator)

        for substance_data in substances_data:
            try:
                substance = Substance.objects.get(name=substance_data)
            except ObjectDoesNotExist:
                substance = None
            study.substances.add(substance)

        study.save()
        return study

    def update(self, instance, validated_data):
        groupset_data = validated_data.pop('groupset',None)
        interventionset_data = validated_data.pop('interventionset',None)
        substances_data = validated_data.pop('substances', [])
        curators_data = validated_data.pop('curators', [])
        creator_data = validated_data.pop('creator', None)

        try:
            creator = User.objects.get(username=creator_data)
        except ObjectDoesNotExist:
            creator = None

        instance.creator = creator

        for name, value in validated_data.items():
            setattr(instance, name, value)

        instance.save()


        if interventionset_data is not None:
            interventionset = InterventionSet.objects.create(**interventionset_data)
            interventionset.save()
            instance.interventionset = interventionset
        instance.save()

        if groupset_data is not None:
            groupset = GroupSet.objects.create(**groupset_data)

            groupset.save()
            instance.groupset = groupset

        instance.save()

        for curator_data in curators_data:
            try:
                curator = User.objects.get(username=curator_data)
            except ObjectDoesNotExist:
                curator = None
            instance.curators.add(curator)
        instance.save()

        for substance_data in substances_data:
            try:
                substance = Substance.objects.get(name=substance_data)
            except ObjectDoesNotExist:
                substance = None
            instance.substances.add(substance)

        return instance


from rest_framework import serializers

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from pkdb_app.categoricals import SUBSTANCES_DATA
from pkdb_app.interventions.models import Substance, InterventionSet, OutputSet
from pkdb_app.interventions.serializers import SubstanceSerializer, InterventionSetSerializer, OutputSetSerializer
from pkdb_app.subjects.serializers import GroupSetSerializer, IndividualSetSerializer
from pkdb_app.users.models import User
from pkdb_app.users.serializers import UserSerializer
from .models import Reference, Author, Study
from django.core.exceptions import ObjectDoesNotExist
#from ..subjects.serializers import GroupSerializer
from ..subjects.models import Group, GroupSet, IndividualSet
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
    reference = serializers.PrimaryKeyRelatedField(queryset=Reference.objects.all(), required=False, allow_null=True)
    groupset = GroupSetSerializer(read_only=False, required=False,allow_null=True)
    curators = serializers.SlugRelatedField(queryset=User.objects.all(), slug_field='username', many=True,required=False,allow_null=True)
    creator = serializers.SlugRelatedField(queryset=User.objects.all(), slug_field='username',required=False,allow_null=True)
    substances = serializers.SlugRelatedField(queryset=Substance.objects.all(), slug_field='name',required=False, many=True,allow_null=True)
    interventionset = InterventionSetSerializer(read_only=False, required=False,allow_null=True)
    individualset = IndividualSetSerializer(read_only=False, required=False, allow_null=True)
    outputset =OutputSetSerializer(read_only=False, required=False, allow_null=True)

    class Meta:
        model = Study
        fields = BASE_FIELDS + ('sid','name',"creator","pkdb_version","design",'reference',"curators",
                                "groupset", "interventionset","individualset","outputset","substances")

    def to_internal_value(self, data):
        sid = data.get("sid")
        self.context["study"] = sid

        return super().to_internal_value(data)

    @staticmethod
    def pop_relations(validated_data):
        related = {}
        related["interventionset_data"] = validated_data.pop('interventionset', None)
        related["substances_data"] = validated_data.pop('substances', [])
        related["curators_data"] = validated_data.pop('curators', [])
        related["groupset_data"] = validated_data.pop('groupset', None)
        related["individualset_data"] = validated_data.pop('individualset', None)
        related["outputset_data"] = validated_data.pop('outputset', None)
        related["creator_data"] = validated_data.pop('creator', None)

        related["reference"] = validated_data.pop('reference',None)

        try:
            related["creator"] = User.objects.get(username=related["creator_data"])
        except ObjectDoesNotExist:
            related["creator"] = None
        return related

    @staticmethod
    def create_relations(study, related):
        if related["groupset_data"] is not None:
            groupset = GroupSet.objects.create(**related["groupset_data"])

            groupset.save()
            study.groupset = groupset

        if related["individualset_data"] is not None:
            individualset = IndividualSet.objects.create(**related["individualset_data"])

            individualset.save()
            study.individualset = individualset

        if related["interventionset_data"] is not None:
            interventionset = InterventionSet.objects.create(**related["interventionset_data"])
            interventionset.save()
            study.interventionset = interventionset
        study.save()

        if related["outputset_data"] is not None:
            outputset = OutputSet.objects.create(**related["outputset_data"])
            outputset.save()
            study.outputset = outputset
        study.save()

        for curator_data in related["curators_data"]:
            try:
                curator = User.objects.get(username=curator_data)
            except ObjectDoesNotExist:
                curator = None
            study.curators.add(curator)

        for substance_data in related["substances_data"]:
            try:
                substance = Substance.objects.get(name=substance_data)
            except ObjectDoesNotExist:
                substance = None
            study.substances.add(substance)

        study.save()

        return study


    def create(self, validated_data):
        related = self.pop_relations(validated_data)

        study, _ = Study.objects.update_or_create(sid=validated_data["sid"],
                                                  reference=related["reference"],
                                                  creator=related["creator"],
                                                  defaults=validated_data,)

        study = self.create_relations(study,related)


        return study

    def update(self, instance, validated_data):

        related = self.pop_relations(validated_data)

        if related["creator"] is not None:
            instance.creator =  related["creator"]

        for name, value in validated_data.items():
            setattr(instance, name, value)

        instance.save()
        instance = self.create_relations(instance,related)

        return instance



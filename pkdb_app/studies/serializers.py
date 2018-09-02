"""
Studies serializers.
"""
from django.contrib.sites.shortcuts import get_current_site
from rest_framework import serializers

from pkdb_app.subjects.models import GroupSet, IndividualSet
from pkdb_app.utils import update_or_create_multiple
from ..interventions.models import Substance, DataFile, InterventionSet, OutputSet
from ..interventions.serializers import InterventionSetSerializer, OutputSetSerializer
from ..subjects.serializers import GroupSetSerializer, IndividualSetSerializer
from ..users.models import User
from .models import Reference, Author, Study, Keyword
from ..serializers import WrongKeyValidationSerializer, SidSerializer


# ----------------------------------
# Keyword
# ----------------------------------
class KeywordSerializer(serializers.ModelSerializer):
    """ Keyword. """
    class Meta:
        model = Keyword
        fields = ["name"]

    def create(self, validated_data):
        keyword, created = Keyword.objects.update_or_create(**validated_data)
        return keyword

    def to_internal_value(self, data):
        # FIXME
        self.validate_wrong_keys(data)
        return super().to_internal_value(data)


# ----------------------------------
# Study / Reference
# ----------------------------------
class AuthorSerializer(WrongKeyValidationSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Author
        fields = ('id','first_name', 'last_name')

    def create(self, validated_data):
        author, created = Author.objects.update_or_create(**validated_data)
        return author

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        return super().to_internal_value(data)


class ReferenceSerializer(SidSerializer):
    authors = AuthorSerializer(many=True, read_only=False)

    class Meta:
        model = Reference
        fields = ('pmid', 'sid', 'name', 'doi', 'title','abstract', 'journal', 'date', 'authors', 'pdf')

    def create(self, validated_data):
        authors_data = validated_data.pop('authors',[])
        reference = Reference.objects.create(**validated_data)
        update_or_create_multiple(reference,authors_data,'authors')
        reference.save()
        return reference

    def update(self, instance, validated_data):
        authors_data = validated_data.pop('authors',[])
        for name, value in validated_data.items():
            setattr(instance, name, value)
        update_or_create_multiple(instance,authors_data,'authors')
        instance.save()
        return instance

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        return super().to_internal_value(data)

class StudySerializer(SidSerializer):
    """ Study Serializer.

    JSON -> Model_Ex
    - to_internal_value
    - validate
    - is_valid (triggers create or update)

    Validators:
    - field validators (local)
    - validate (model)

    Model_Ex -> JSON
    - to representation

    """
    reference = serializers.PrimaryKeyRelatedField(queryset=Reference.objects.all(), required=False, allow_null=True)
    groupset = GroupSetSerializer(read_only=False, required=False,allow_null=True)
    curators = serializers.SlugRelatedField(queryset=User.objects.all(), slug_field='username', many=True,required=False,allow_null=True)
    creator = serializers.SlugRelatedField(queryset=User.objects.all(), slug_field='username',required=False,allow_null=True)
    substances = serializers.SlugRelatedField(queryset=Substance.objects.all(), slug_field='name',required=False, many=True)
    keywords = serializers.SlugRelatedField(queryset=Keyword.objects.all(), slug_field='name',required=False, many=True)

    interventionset = InterventionSetSerializer(read_only=False, required=False,allow_null=True)
    individualset = IndividualSetSerializer(read_only=False, required=False, allow_null=True)
    outputset = OutputSetSerializer(read_only=False, required=False, allow_null=True)
    files = serializers.PrimaryKeyRelatedField(queryset=DataFile.objects.all(), required=False, allow_null=True, many=True)

    class Meta:
        model = Study
        fields = ('sid', 'pkdb_version','name', 'reference', 'creator', 'curators', 'substances','keywords', 'design',
                  'groupset', 'individualset', 'interventionset', 'outputset', 'files')




    def create(self, validated_data):
        related = self.pop_relations(validated_data)
        instance, _ = Study.objects.update_or_create(sid=validated_data["sid"],
                                                     reference=related["reference"],
                                                     defaults=validated_data,)
        instance = self.create_relations(instance, related)
        instance.save()
        return instance

    def update(self, instance, validated_data):

        # remove nested relations (handled via own serializers)
        related = self.pop_relations(validated_data)

        for name, value in validated_data.items():
            setattr(instance, name, value)
        instance.save()

        instance = self.create_relations(instance, related)
        return instance

    def to_internal_value(self, data):
        creator = data.get("creator")
        if creator:
            data["creator"] = self.get_or_val_error(User, username=creator)

        self.validate_wrong_keys(data)
        return super().to_internal_value(data)


    def to_representation(self, instance):
        """ Convert to JSON.

        :param instance:
        :return:
        """
        rep = super().to_representation(instance)
        current_site = f'http://{get_current_site(self.context["request"]).domain}'

        # replace file url
        if "files" in rep:
            rep["files"] = [current_site + file.file.url for file in instance.files.all()]
        return rep


    #############################################################################################
    # Helpers
    #############################################################################################

    @staticmethod
    def related_sets():
        return {
            "groupset": GroupSet,
            "individualset": IndividualSet,
            "interventionset": InterventionSet,
            "outputset": OutputSet
        }

    def pop_relations(self, validated_data):
        """ Remove nested relations (handled via own serializers)

        :param validated_data:
        :return:
        """
        related_foreinkeys = self.related_sets().copy()
        related_foreinkeys["reference"] = Reference
        related_many2many = {"substances": Substance,"keywords": Keyword, "curators": User, "files": DataFile}
        related_foreinkeys_dict = {name: validated_data.pop(name, None) for name in related_foreinkeys.keys()}
        related_many2many_dict = {name: validated_data.pop(name, []) for name in related_many2many.keys()}
        related = {**related_foreinkeys_dict, **related_many2many_dict}
        return related

    def create_relations(self, study, related):
        """ Function creates all the related_sets.

        :param study:
        :param related:
        :return:
        """


        for name, model in self.related_sets().items():

            if related[name] is not None:
                if getattr(study, name):
                        getattr(study, name).delete()
                instance = model.objects.create(study = study, **related[name])
                setattr(study, name, instance)
            study.save()

        for curator in related["curators"]:
            study.curators.add(curator)

        for substance in related["substances"]:
            study.substances.add(substance)

        for keyword in related["keywords"]:
            study.keywords.add(keyword)

        study.save()


        if related["files"]:
            study.files.all().delete()

            for file_pk in related["files"]:
                study.files.add(file_pk)
            study.save()

        return study
###############################################################################################
# Read Serializer
###############################################################################################
class StudyReadSerializer(serializers.HyperlinkedModelSerializer):

    curators = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='users_read-detail')
    substances = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='substances_read-detail')
    keywords = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='keywords_read-detail')

    creator = serializers.HyperlinkedRelatedField(read_only=True, view_name='users_read-detail')
    reference = serializers.HyperlinkedRelatedField(read_only=True, lookup_field='sid', view_name='references_read-detail')

    individualset = serializers.HyperlinkedRelatedField(read_only=True, view_name='individualsets_read-detail')
    groupset = serializers.HyperlinkedRelatedField(read_only=True, view_name='groupsets_read-detail')
    outputset = serializers.HyperlinkedRelatedField(read_only=True, view_name='outputsets_read-detail')


    files = serializers.HyperlinkedRelatedField(many=True,read_only=True, view_name='datafiles_read-detail')

    class Meta:
        model = Study
        fields = ('pk','sid', 'pkdb_version','name', 'reference', 'creator', 'curators', 'substances', 'keywords', 'design', 'individualset','groupset','outputset','files')


class ReferenceReadSerializer(serializers.HyperlinkedModelSerializer):
    authors = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='authors_read-detail')
    study = serializers.HyperlinkedRelatedField(many=True, lookup_field='sid', read_only=True, view_name='studies_read-detail')


    class Meta:
        model = Reference
        fields = ('pk','study','pmid', 'sid', 'name', 'doi', 'title', 'abstract', 'journal', 'date', 'authors', 'pdf')

class AuthorReadSerializer(serializers.HyperlinkedModelSerializer):
    references = serializers.HyperlinkedRelatedField(many=True, read_only=True, lookup_field='sid', view_name='references_read-detail')

    class Meta:
        model = Author
        fields = ('pk','references', 'first_name', 'last_name')

class KeywordReadSerializer(serializers.HyperlinkedModelSerializer):
    studies = serializers.HyperlinkedRelatedField(many=True, lookup_field='sid', read_only=True, view_name='studies_read-detail')

    """ Keyword. """
    class Meta:
        model = Keyword
        fields = ["pk","name", "studies"]
"""
Studies serializers.
"""
from django.contrib.sites.shortcuts import get_current_site
from rest_framework import serializers

from pkdb_app.comments.models import Description, Comment
from pkdb_app.comments.serializers import DescriptionSerializer, CommentSerializer, CommentElasticSerializer, \
    DescriptionElasticSerializer
from pkdb_app.subjects.models import GroupSet, IndividualSet
from pkdb_app.users.serializers import UserReadSerializer
from pkdb_app.utils import update_or_create_multiple, create_multiple
from ..interventions.models import Substance, DataFile, InterventionSet, OutputSet
from ..interventions.serializers import InterventionSetSerializer, OutputSetSerializer, SubstanceReadSerializer
from ..subjects.serializers import GroupSetSerializer, IndividualSetSerializer, DataFileReadSerializer
from ..users.models import User
from .models import Reference, Author, Study, Keyword
from ..serializers import WrongKeyValidationSerializer, SidSerializer


# ----------------------------------
# Keyword
# ----------------------------------
class KeywordSerializer(WrongKeyValidationSerializer):
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
        fields = ("id", "first_name", "last_name")

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
        fields = (
            "pmid",
            "sid",
            "name",
            "doi",
            "title",
            "abstract",
            "journal",
            "date",
            "authors",
            "pdf",
        )

    def create(self, validated_data):
        authors_data = validated_data.pop("authors", [])
        reference = Reference.objects.create(**validated_data)
        update_or_create_multiple(reference, authors_data, "authors")
        reference.save()
        return reference

    def update(self, instance, validated_data):
        authors_data = validated_data.pop("authors", [])
        for name, value in validated_data.items():
            setattr(instance, name, value)
        update_or_create_multiple(instance, authors_data, "authors")
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

    reference = serializers.PrimaryKeyRelatedField(
        queryset=Reference.objects.all(), required=False, allow_null=True
    )
    groupset = GroupSetSerializer(read_only=False, required=False, allow_null=True)
    curators = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="username",
        many=True,
        required=False,
        allow_null=True,
    )
    creator = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="username",
        required=False,
        allow_null=True,
    )
    substances = serializers.SlugRelatedField(
        queryset=Substance.objects.all(), slug_field="name", required=True, many=True
    )
    keywords = serializers.SlugRelatedField(
        queryset=Keyword.objects.all(), slug_field="name", required=True, many=True
    )
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    interventionset = InterventionSetSerializer(
        read_only=False, required=False, allow_null=True
    )
    individualset = IndividualSetSerializer(
        read_only=False, required=False, allow_null=True
    )
    outputset = OutputSetSerializer(read_only=False, required=False, allow_null=True)
    files = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True, many=True
    )

    class Meta:
        model = Study
        fields = (
            "sid",
            "pkdb_version",
            "name",
            "reference",
            "creator",
            "curators",
            "substances",
            "descriptions",
            "keywords",
            "design",
            "groupset",
            "individualset",
            "interventionset",
            "outputset",
            "files",
            "comments",
        )

    def create(self, validated_data):
        related = self.pop_relations(validated_data)
        instance, _ = Study.objects.update_or_create(
            sid=validated_data["sid"],
            reference=related["reference"],
            defaults=validated_data,
        )
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

            rep["files"] = [
            current_site + file.file.url for file in instance.files.all()
            ]

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
            "outputset": OutputSet,
        }

    def pop_relations(self, validated_data):
        """ Remove nested relations (handled via own serializers)

        :param validated_data:
        :return:
        """
        related_foreinkeys = self.related_sets().copy()
        related_foreinkeys["reference"] = Reference
        related_many2many = {
            "substances": Substance,
            "keywords": Keyword,
            "descriptions": Description,
            "comments": Comment,
            "curators": User,
            "files": DataFile,
        }
        related_foreinkeys_dict = {
            name: validated_data.pop(name, None) for name in related_foreinkeys.keys()
        }
        related_many2many_dict = {
            name: validated_data.pop(name, []) for name in related_many2many.keys()
        }
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
                instance = model.objects.create(study=study, **related[name])
                setattr(study, name, instance)
            study.save()

        for curator in related["curators"]:
            study.curators.add(curator)

        for substance in related["substances"]:
            study.substances.add(substance)

        for keyword in related["keywords"]:
            study.keywords.add(keyword)

        if related["descriptions"]:
            study.descriptions.all().delete()
            create_multiple(study, related["descriptions"], "descriptions")

        create_multiple(study, related["comments"], "comments")

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
class KeywordReadSerializer(serializers.HyperlinkedModelSerializer):
    studies = serializers.HyperlinkedRelatedField(many=True, lookup_field="sid", read_only=True, view_name="studies_read-detail"
    )

    """ Keyword. """

    class Meta:
        model = Keyword
        fields = ["pk", "name", "studies"]



class StudyReadSerializer(serializers.HyperlinkedModelSerializer):

    curators = UserReadSerializer( many=True, read_only=True)
    substances = SubstanceReadSerializer(many=True, read_only=True)
    keywords = KeywordReadSerializer(many=True, read_only=True)
    descriptions = DescriptionElasticSerializer(many=True, read_only=True)
    creator = UserReadSerializer(read_only=True)
    reference = serializers.HyperlinkedRelatedField(
        read_only=True, lookup_field="sid", view_name="references_read-detail"
    )
    #reference = serializers.HyperlinkedRelatedField(
    #    read_only=True, lookup_field="sid", view_name="references_read-detail"
    #)
    #reference = serializers.SlugRelatedField(
    #    read_only=True,
    #    slug_field='name'
    # )

    individualset = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="individualsets_read-detail"
    )
    interventionset = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="interventionsets_read-detail"
    )
    groupset = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="groupsets_read-detail"
    )
    outputset = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="outputsets_read-detail"
    )
    files = DataFileReadSerializer(many=True,
             read_only=True,)


    #serializers.HyperlinkedRelatedField(
    #    many=True, read_only=True, view_name="datafiles_read-detail"
    #)
    comments = CommentElasticSerializer(many=True, read_only=True)


    class Meta:
        model = Study
        fields = [
            "pk",
            "sid",
            "pkdb_version",
            "name",
            "reference",
            "creator",
            "curators",
            "substances",
            "keywords",
            "descriptions",
            "comments",
            "design",
            "individualset",
            "interventionset",
            "groupset",
            "outputset",
            "files",
        ] + ["group_count","individual_count","intervention_count","output_count","timecourse_count"]



class AuthorReadSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Author
        fields = ("pk", "first_name", "last_name")

class ReferenceReadSerializer(serializers.HyperlinkedModelSerializer):
    authors = AuthorReadSerializer(
        many=True, read_only=True)

    class Meta:
        model = Reference
        fields = (
            "pk",
            "study_name",
            "study_pk",
            "pmid",
            "sid",
            "name",
            "doi",
            "title",
            "abstract",
            "journal",
            "date",
            "authors",
            "pdf",
        )


class ReferenceSmallElasticSerializer(serializers.HyperlinkedModelSerializer):
    #url = serializers.HyperlinkedIdentityField(read_only=True, lookup_field="id",view_name="references_elastic-detail")
    class Meta:
        model = Reference
        fields = ["sid"]#, 'url']

class StudyElasticSerializer(serializers.HyperlinkedModelSerializer):


    #reference = serializers.HyperlinkedRelatedField(
    #read_only=True, lookup_field="sid", view_name="references_read-detail"
    #)
    reference = ReferenceSmallElasticSerializer()

    design = serializers.CharField(read_only=True)
    pkdb_version = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)


    curators = UserReadSerializer(many=True, read_only=True)
    creator = UserReadSerializer( read_only=True)

    substances = serializers.SerializerMethodField()
    keywords = serializers.SerializerMethodField()
    #files = serializers.SerializerMethodField()

    #files = DataFileReadSerializer(many=True, read_only=True,)

    comments = CommentElasticSerializer(many=True, read_only=True)
    descriptions = DescriptionElasticSerializer(many=True, read_only=True)



    class Meta:
        model = Study
        fields = [
                     "pk","sid",
            "reference",
            "name",
            "design",
            "pkdb_version",
            "curators",
            "creator",
            "substances",
            "keywords",
            #"files",
            "comments",
            "descriptions"] + ["group_count", "individual_count", "intervention_count", "output_count", "timecourse_count"]

        read_only_fields = fields


    def get_substances(self, obj):
        """Get substances."""
        if obj.substances:
            return list(obj.substances)
        else:
            return []

    def get_keywords(self, obj):
        """Get substances."""
        if obj.keywords:
            return list(obj.keywords)
        else:
            return []


    def get_files(self,obj):
        #current_site = f'http://{get_current_site(self.context["request"]).domain}'

        if "files" in obj:
            files = []
            for n,file in enumerate(obj.files):
                #if file.file:
                #    file.file =  current_site + file.file
                files.append(file.to_dict())

            return list(files)
        else:
            return list([])





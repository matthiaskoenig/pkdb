"""
Studies serializers.
"""

from rest_framework import serializers

from pkdb_app import utils
from pkdb_app.outputs.models import OutputSet
from pkdb_app.outputs.serializers import OutputSetSerializer, OutputSetElasticSmallSerializer
from pkdb_app.users.permissions import get_study_file_permission
from .models import Reference, Author, Study, Rating
from ..comments.models import Description, Comment
from ..comments.serializers import DescriptionSerializer, CommentSerializer, CommentElasticSerializer, \
    DescriptionElasticSerializer
from ..interventions.models import DataFile, InterventionSet
from ..interventions.serializers import InterventionSetSerializer, InterventionSetElasticSmallSerializer
from ..serializers import WrongKeyValidationSerializer, SidSerializer, StudySmallElasticSerializer, SidNameSerializer
from ..subjects.models import GroupSet, IndividualSet
from ..subjects.serializers import GroupSetSerializer, IndividualSetSerializer, DataFileElasticSerializer, \
    GroupSetElasticSmallSerializer, IndividualSetElasticSmallSerializer
from ..users.models import User
from ..users.serializers import UserElasticSerializer
from ..utils import update_or_create_multiple, create_multiple, list_duplicates, _validate_requried_key, \
    _validate_not_allowed_key


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


class ReferenceSerializer(WrongKeyValidationSerializer):
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
        )

    def create(self, validated_data):
        # return super().create(validated_data)

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


class CuratorRatingSerializer(serializers.ModelSerializer):
    rating = serializers.FloatField(min_value=0, max_value=5)

    user = utils.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="username"
    )
    study = serializers.PrimaryKeyRelatedField(required=False,
                                               queryset=Study.objects.all()
                                               )

    class Meta:
        model = Rating
        fields = ("rating", "user", "study")

    def to_representation(self, instance):
        return {"curator": instance.username}


class StudySerializer(SidSerializer):
    """ Study Serializer.
    """

    reference = utils.SlugRelatedField(slug_field="sid",
                                       queryset=Reference.objects.all(), required=True, allow_null=False
                                       )
    groupset = GroupSetSerializer(read_only=False, required=False, allow_null=True)
    curators = CuratorRatingSerializer(many=True, required=False,
                                       allow_null=True)
    collaborators = utils.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="username",
        many=True,
        required=False,
        allow_null=True,
    )

    creator = utils.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="username",
        required=False,
        allow_null=True,
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
    warnings = DescriptionSerializer(
        many=True, read_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Study
        fields = (
            "sid",
            "name",
            "date",
            "reference",
            "creator",
            "curators",
            "collaborators",
            "descriptions",
            "licence",
            "access",
            "groupset",
            "individualset",
            "interventionset",
            "outputset",
            "files",
            "comments",
            "warnings"
        )
        write_only_fields = ('curators', 'collaborators')

    def to_internal_value(self, data):
        creator = data.get("creator")
        if creator:
            data["creator"] = self.get_or_val_error(User, username=creator)

        # curators to internal
        if "curators" in data:
            ratings = []
            for curator_and_rating in data.get("curators", []):
                rating_dict = {}
                if isinstance(curator_and_rating, list):
                    if len(curator_and_rating) != 2:
                        raise serializers.ValidationError(
                            {
                                "curators": " Each curator in the list of curator can be added either via the curator "
                                            "username or as a list with first position beeing the curator username "
                                            " and the second posion the rating between (0-5)",
                                "details": curator_and_rating,

                            })
                    rating_dict["user"] = curator_and_rating[0]
                    rating_dict["rating"] = curator_and_rating[1]

                else:
                    rating_dict["user"] = curator_and_rating
                    rating_dict["rating"] = 0

                ratings.append(rating_dict)
            data["curators"] = ratings

        # check for duplicates
        #######################################
        for item in ["collaborators", "curators", "substances"]:

            if item in ["curators"]:
                related_unique_field = "user"
                unique_values = [instance.get(related_unique_field) for instance in data.get(item, [])]

            else:
                unique_values = data.get(item, [])

            duplicates = list_duplicates(unique_values)
            if duplicates:
                raise serializers.ValidationError(
                    {item: f"Duplicated {item} <{duplicates}> are not allowed."})

        #######################################################################

        if data.get("reference"):
            reference = self.get_or_val_error(model=Reference, sid=data["reference"])
            if hasattr(reference, "study"):
                if str(reference.study.sid) != str(data.get("sid")):
                    raise serializers.ValidationError(
                        {
                            "reference":
                                f"References are required to be unqiue on every study. "
                                f"This Reference already exist in study with sid: <{reference.study.sid} and "
                                f"name: <{reference.study.name}>. If you changed the sid of the study "
                                f"you might want to run `delete_study -s {reference.study.sid}`. ",
                            "details": data["reference"],
                        }
                    )

        return super().to_internal_value(data)

    def create(self, validated_data):

        related = self.pop_relations(validated_data)
        instance, _ = Study.objects.update_or_create(
            sid=validated_data["sid"],
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

    def to_representation(self, instance):
        """ Convert to JSON.

        :param instance:
        :return:
        """

        rep = super().to_representation(instance)
        request = self.context.get('request')
        # replace file url

        # todo: This is not working correctly
        if "files" in rep:
            rep["files"] = [request.build_absolute_uri(file.file.url) for file in instance.files.all()]

        curators = []
        for user in instance.curators.all():
            rating = instance.ratings.get(user=user)
            curators.append({"rating": rating.rating,
                             "first_name": user.first_name,
                             "last_name": user.last_name,
                             "pk": user.pk})

        rep["curators"] = curators

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
    def related_serializer(self):
        return {
            "groupset": GroupSetSerializer,
            "individualset": IndividualSetSerializer,
            "interventionset": InterventionSetSerializer,
            "outputset": OutputSetSerializer,
        }

    def pop_relations(self, validated_data):
        """ Remove nested relations (handled via own serializers)

        :param validated_data:
        :return:
        """
        related_foreignkeys = self.related_sets().copy()

        related_many2many = {
            "descriptions": Description,
            "comments": Comment,
            "curators": User,
            "collaborators": User,
            "files": DataFile,
        }
        related_foreignkeys_dict = {
            name: validated_data.pop(name, None) for name in related_foreignkeys.keys()
        }
        related_many2many_dict = {name: validated_data.pop(name) for name in related_many2many.keys() if
                                  name in validated_data}
        related = {**related_foreignkeys_dict, **related_many2many_dict}

        return related

    def create_relations(self, study, related):
        """ Function creates all the related_sets.

        :param study:
        :param related:
        :return:
        """

        for name, serializer in self.related_serializer().items():

            if related[name] is not None:
                if getattr(study, name):
                    getattr(study, name).delete()

                context = self.context
                context["study"] = study
                instance = serializer(context=context).create(validated_data={**related[name]})


                setattr(study, name, instance)
            study.save()


        if "curators" in related:
            study.ratings.all().delete()
            if related["curators"]:
                for curator in related["curators"]:
                    curator["study"] = study
                    Rating.objects.create(**curator)

        if "collaborators" in related:
            study.collaborators.clear()
            if related["collaborators"]:
                study.collaborators.add(*related["collaborators"])

        if "descriptions" in related:
            study.descriptions.all().delete()
            if related["descriptions"]:
                create_multiple(study, related["descriptions"], "descriptions")

        if "comments" in related:
            study.comments.all().delete()
            if related["comments"]:
                create_multiple(study, related["comments"], "comments")

        if "files" in related:

            study.files.clear()
            if related["files"]:
                for file_pk in related["files"]:
                    study.files.add(file_pk)

        study.save()


        return study

    def validate(self, attrs):

        if str(attrs.get("sid")).startswith("PKDB"):
            _validate_requried_key(attrs, "date", extra_message="For a study with a '^PKDB\d+$' identifier "
                                                                "the date must be set in the study.json.")
        else:
            if attrs.get("date", None) is not None:
                _validate_not_allowed_key(attrs, "date", extra_message="For a study without a '^PKDB\d+$' identifier "
                                                                "the date must not be set in the study.json.")

        if "curators" in attrs and "creator" in attrs:
            if attrs["creator"] not in [curator["user"] for curator in attrs["curators"]]:
                error_json = {"creator": "Creator must be in curator."}
                raise serializers.ValidationError(error_json)
        return super().validate(attrs)


###############################################################################################
# Elastic Serializer
###############################################################################################
class AuthorElasticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ("pk", "first_name", "last_name")
        read_only_fields = fields



class CuratorRatingElasticSerializer(serializers.Serializer):
    rating = serializers.FloatField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()

    class Meta:
        fields = ["rating", "username", "first_name", "last_name"]


class ReferenceElasticSerializer(serializers.ModelSerializer):
    study = StudySmallElasticSerializer(read_only=True)
    authors = AuthorElasticSerializer(many=True, read_only=True)

    class Meta:
        model = Reference
        fields = (
            "pk",
            "study",
            "pmid",
            "sid",
            "name",
            "doi",
            "title",
            "abstract",
            "journal",
            "date",
            "authors",
        )
        read_only_fields = fields


class ReferenceSmallElasticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reference
        fields = ["pk", "sid"]  # , 'url']
        read_only_fields = fields


class StudyElasticStatisticsSerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    licence = serializers.CharField(read_only=True)
    access = serializers.CharField(read_only=True)
    curators = CuratorRatingElasticSerializer(many=True, read_only=True)
    creator = UserElasticSerializer(read_only=True)

    class Meta:
        model = Study

        fields = [
            "pk",
            "sid",
            "name",
            "licence",
            "access",
            "date",

            "group_count",
            "individual_count",
            "intervention_count",
            "output_count",
            "output_calculated_count",
            "timecourse_count",

            "creator",
            "substances",
        ]

        read_only_fields = fields


class StudyElasticSerializer(serializers.ModelSerializer):
    pk = serializers.CharField()
    reference = ReferenceSmallElasticSerializer()

    name = serializers.CharField()
    licence = serializers.CharField()
    access = serializers.CharField()

    curators = CuratorRatingElasticSerializer(many=True, )
    creator = UserElasticSerializer()
    collaborators = UserElasticSerializer(many=True, )

    substances = SidNameSerializer(many=True, )

    files = serializers.SerializerMethodField()  # DataFileElasticSerializer(many=True, )

    comments = CommentElasticSerializer(many=True, )
    descriptions = DescriptionElasticSerializer(many=True, )
    groupset = GroupSetElasticSmallSerializer()
    individualset = IndividualSetElasticSmallSerializer()
    interventionset = InterventionSetElasticSmallSerializer()
    outputset = OutputSetElasticSmallSerializer()

    class Meta:
        model = Study

        fields = [
            "pk",
            "sid",
            "name",
            "licence",
            "access",
            "date",

            "group_count",
            "individual_count",
            "intervention_count",
            "output_count",
            "output_calculated_count",
            "timecourse_count",

            "reference",
            "creator",
            "curators",
            "collaborators",

            "comments",
            "descriptions",

            "files",
            "substances",

            "groupset",
            "individualset",
            "interventionset",
            "outputset",
        ]

        read_only_fields = fields

    @staticmethod
    def get_substances(obj):
        """Get substances."""
        if obj.substances:
            return list(obj.substances)
        else:
            return []

    def get_files(self, obj):

        if get_study_file_permission(self.context["request"].user, obj):
            files_serializer = DataFileElasticSerializer(obj.files, many=True, read_only=True)
            return files_serializer.data

        else:
            return []


"""Serializers for studies, their references, authors and curator ratings."""

from collections import OrderedDict

from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers

from pkdb_app import utils
from pkdb_app.data.models import DataSet
from pkdb_app.data.serializers import DataSetElasticSmallSerializer, DataSetSerializer
from pkdb_app.outputs.models import OutputSet
from pkdb_app.outputs.serializers import (
    OutputSetElasticSmallSerializer,
    OutputSetSerializer,
)
from pkdb_app.users.permissions import get_study_file_permission

from ..comments.models import Comment, Description
from ..comments.serializers import (
    CommentElasticSerializer,
    CommentSerializer,
    DescriptionElasticSerializer,
    DescriptionSerializer,
)
from ..interventions.models import DataFile, InterventionSet
from ..interventions.serializers import (
    InterventionSetElasticSmallSerializer,
    InterventionSetSerializer,
)
from ..serializers import (
    SidNameLabelSerializer,
    SidSerializer,
    StudySmallElasticSerializer,
    WrongKeyValidationSerializer,
)
from ..subjects.models import GroupSet, IndividualSet
from ..subjects.serializers import (
    DataFileElasticSerializer,
    GroupSetElasticSmallSerializer,
    GroupSetSerializer,
    IndividualSetElasticSmallSerializer,
    IndividualSetSerializer,
)
from ..users.models import User
from ..users.serializers import UserElasticSerializer
from ..utils import (
    _validate_not_allowed_key,
    _validate_required_key,
    create_multiple,
    list_duplicates,
    update_or_create_multiple,
)
from .models import Author, Rating, Reference, Study


class AuthorSerializer(WrongKeyValidationSerializer):
    """Serialize an author of a study reference for upload and read."""

    id = serializers.ReadOnlyField()

    class Meta:
        model = Author
        fields = ("id", "first_name", "last_name")

    def create(self, validated_data):
        """Create the author, or update the matching author if one with the same fields already exists."""
        author, _ = Author.objects.update_or_create(**validated_data)
        return author

    def to_internal_value(self, data):
        """Reject unknown keys before deferring to the default deserialization."""
        self.validate_wrong_keys(data)
        return super().to_internal_value(data)

    def validate(self, attrs):
        """Reject the placeholder author name 'Max Mustermann', then defer to the default validation."""
        if attrs.get("first_name") == "Max" and attrs.get("last_name").startswith(
            "Musterman"
        ):
            raise serializers.ValidationError(
                "Replace 'Max Mustermann' with the correct authors in <reference.json>"
            )
        return super().validate(attrs)


class ReferenceSerializer(WrongKeyValidationSerializer):
    """Serialize the publication or reference of a study, with its authors, for upload and read."""

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
        extra_kwargs = {
            "name": {"error_messages": {"required": "add name to reference.json"}},
            "pmid": {"error_messages": {"required": "add pmid to reference.json"}},
            "sid": {"error_messages": {"required": "add sid to reference.json"}},
        }

    def create(self, validated_data):
        """Create the reference and its authors."""
        authors_data = validated_data.pop("authors", [])
        reference = Reference.objects.create(**validated_data)
        create_multiple(reference, authors_data, "authors")
        reference.save()
        return reference

    def update(self, instance, validated_data):
        """Update the reference fields and update or create the given authors, without deleting any existing author."""
        authors_data = validated_data.pop("authors", [])
        for name, value in validated_data.items():
            setattr(instance, name, value)
        update_or_create_multiple(instance, authors_data, "authors")
        instance.save()
        return instance

    def to_internal_value(self, data):
        """Reject unknown keys before deferring to the default deserialization."""
        self.validate_wrong_keys(data)
        return super().to_internal_value(data)

    def validate(self, attrs):
        """Reject the unfilled placeholder values for journal, title and date, then defer to the default validation."""
        if attrs.get("journal") and attrs.get("journal").startswith("Add your title"):
            raise serializers.ValidationError("Add a journal to <reference.json>.")
        if attrs.get("title") and attrs.get("title").startswith("Add your title"):
            raise serializers.ValidationError("Add a title to <reference.json>.")
        if attrs.get("date") == "1000-10-10":
            raise serializers.ValidationError(
                "Replace '1000-10-10' with the correct date in <reference.json>."
            )
        return super().validate(attrs)


class CuratorRatingSerializer(serializers.ModelSerializer):
    """Serialize a curator's rating of a study, for upload and read."""

    rating = serializers.FloatField(min_value=0, max_value=5)

    user = utils.SlugRelatedField(queryset=User.objects.all(), slug_field="username")
    study = serializers.PrimaryKeyRelatedField(
        required=False, queryset=Study.objects.all()
    )

    class Meta:
        model = Rating
        fields = ("rating", "user", "study")

    def to_representation(self, instance):
        """Represent the rating by the curator's username only."""
        return {"curator": instance.username}


class StudySerializer(SidSerializer):
    """Serialize a study, with its reference, curators, collaborators and related sets, for upload and read."""

    reference = utils.SlugRelatedField(
        slug_field="sid",
        queryset=Reference.objects.all(),
        required=True,
        allow_null=False,
    )
    groupset = GroupSetSerializer(read_only=False, required=False, allow_null=True)
    curators = CuratorRatingSerializer(many=True)
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
    dataset = DataSetSerializer(read_only=False, required=False, allow_null=True)

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
            "dataset",
            "files",
            "comments",
            "warnings",
        )
        write_only_fields = ("curators", "collaborators")

    def to_internal_value(self, data):
        """Resolve the creator username, normalize curators to rating dicts, reject duplicates and check the reference.

        Resolves the creator to a User, accepts curators either as a list of usernames or as
        [username, rating] pairs and normalizes them to {"user": ..., "rating": ...} dicts,
        raises a ValidationError on duplicate collaborators, curators or substances, and raises
        a ValidationError if the reference is already used by a different study.
        """
        creator = data.get("creator")
        if creator:
            data["creator"] = self.get_or_val_error(User, username=creator)

        # curators to internal
        if hasattr(data, "curators"):
            if len(data.get("curators", [])) == 0:
                raise serializers.ValidationError(
                    {"curators": "At least One curator is required"}
                )
        else:
            ratings = []
            for curator_and_rating in data.get("curators", []):
                rating_dict = {}
                if isinstance(curator_and_rating, list):
                    if len(curator_and_rating) != 2:
                        raise serializers.ValidationError(
                            {
                                "curators": "Each curator in the list of curator can be added either via the curator "
                                "username or as a list with first position beeing the curator username "
                                "and the second position the rating between (0-5).",
                                "details": curator_and_rating,
                            }
                        )
                    rating_dict["user"] = curator_and_rating[0]
                    rating_dict["rating"] = curator_and_rating[1]
                else:
                    rating_dict["user"] = curator_and_rating
                    rating_dict["rating"] = 0

                ratings.append(rating_dict)
            data["curators"] = ratings

        # check for duplicates
        for item in ["collaborators", "curators", "substances"]:
            if item in ["curators"]:
                related_unique_field = "user"
                unique_values = [
                    instance.get(related_unique_field)
                    for instance in data.get(item, [])
                ]
            else:
                unique_values = data.get(item, [])
            duplicates = list_duplicates(unique_values)
            if duplicates:
                raise serializers.ValidationError(
                    {item: f"Duplicated {item} <{duplicates}> are not allowed."}
                )

        # handle reference
        if data.get("reference"):
            reference = self.get_or_val_error(model=Reference, sid=data["reference"])
            if hasattr(reference, "study") and str(reference.study.sid) != str(
                data.get("sid")
            ):
                raise serializers.ValidationError(
                    {
                        "reference": f"References are required to be unqiue on every study. "
                        f"This Reference already exist in study with sid: <{reference.study.sid} and "
                        f"name: <{reference.study.name}>. If you changed the sid of the study "
                        f"you might want to run `delete_study -s {reference.study.sid}`. ",
                        "details": data["reference"],
                    }
                )

        return super().to_internal_value(data)

    def create(self, validated_data):
        """Create the study, or update the matching study by sid, and create its related sets."""
        related = self.pop_relations(validated_data)
        instance, _ = Study.objects.update_or_create(
            sid=validated_data["sid"],
            defaults=validated_data,
        )
        instance = self.create_relations(instance, related)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        """Update the study fields and replace its related sets."""
        # remove nested relations (handled via own serializers)
        related = self.pop_relations(validated_data)

        for name, value in validated_data.items():
            setattr(instance, name, value)
        instance.save()
        return self.create_relations(instance, related)

    def to_representation(self, instance):
        """Replace the files with their absolute URLs and the curators with their rating, name and pk."""
        rep = super().to_representation(instance)
        request = self.context.get("request")
        # replace file url

        # todo: This is not working correctly
        if "files" in rep:
            rep["files"] = [
                request.build_absolute_uri(file.file.url)
                for file in instance.files.all()
            ]

        curators = []
        for user in instance.curators.all():
            rating = instance.ratings.get(user=user)
            curators.append(
                {
                    "rating": rating.rating,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "pk": user.pk,
                }
            )

        rep["curators"] = curators

        return rep

    #############################################################################################
    # Helpers
    #############################################################################################

    @staticmethod
    def related_sets():
        """Return the ordered mapping of study field name to related set model."""
        return OrderedDict(
            [
                ("groupset", GroupSet),
                ("individualset", IndividualSet),
                ("interventionset", InterventionSet),
                ("outputset", OutputSet),
                ("dataset", DataSet),
            ]
        )

    def related_serializer(self):
        """Return the ordered mapping of study field name to related set serializer class."""
        return OrderedDict(
            [
                ("groupset", GroupSetSerializer),
                ("individualset", IndividualSetSerializer),
                ("interventionset", InterventionSetSerializer),
                ("outputset", OutputSetSerializer),
                ("dataset", DataSetSerializer),
            ]
        )

    def pop_relations(self, validated_data):
        """Remove nested relations (handled via own serializers).

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
        related_foreignkeys_dict = OrderedDict(
            [(name, validated_data.pop(name, None)) for name in related_foreignkeys]
        )
        related_many2many_dict = OrderedDict(
            [
                (name, validated_data.pop(name))
                for name in related_many2many
                if name in validated_data
            ]
        )
        return OrderedDict(
            list(related_foreignkeys_dict.items())
            + list(related_many2many_dict.items())
        )

    def create_relations(self, study, related):
        """Replace the study's related one-to-one sets, ratings, collaborators, descriptions, comments and files.

        :param study:
        :param related:
        :return:
        """
        context = self.context
        context["study"] = study

        for name, serializer in self.related_serializer().items():
            if related[name] is not None:
                if getattr(study, name):
                    getattr(study, name).delete()
                this_serializer = serializer(context=context)
                instance = this_serializer.create(validated_data={**related[name]})
                setattr(study, name, instance)
                study.save()

        if related.get("curators"):
            study.ratings.all().delete()
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
        """Validate the study's date requirement by sid pattern and that the creator is among the curators."""
        if str(attrs.get("sid")).startswith("PKDB"):
            _validate_required_key(
                attrs,
                "date",
                extra_message=r"For a study with a '^PKDB\d+$' identifier "
                "the date must be set in the study.json.",
            )
        else:
            if attrs.get("date", None) is not None:
                _validate_not_allowed_key(
                    attrs,
                    "date",
                    extra_message=r"For a study without a '^PKDB\d+$' identifier "
                    "the date must not be set in the study.json.",
                )

        if (
            "curators" in attrs
            and "creator" in attrs
            and attrs["creator"]
            not in [curator["user"] for curator in attrs["curators"]]
        ):
            error_json = {"curators": "Creator must be in curators."}
            raise serializers.ValidationError(error_json)
        return super().validate(attrs)


# --------------------
# Elastic Serializer
# --------------------
class AuthorElasticSerializer(serializers.ModelSerializer):
    """Serialize an author for the elasticsearch index."""

    class Meta:
        model = Author
        fields = ("pk", "first_name", "last_name")
        read_only_fields = fields


class CuratorRatingElasticSerializer(serializers.Serializer):
    """Serialize a curator's rating of a study for the elasticsearch index."""

    rating = serializers.FloatField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()

    class Meta:
        fields = ["rating", "username", "first_name", "last_name"]


class ReferenceElasticSerializer(serializers.ModelSerializer):
    """Serialize a reference, with its study and authors, for the elasticsearch index."""

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
    """Serialize a reference by its primary key and sid only, for the elasticsearch index."""

    class Meta:
        model = Reference
        fields = ["pk", "sid"]  # , 'url']
        read_only_fields = fields


class StudyElasticStatisticsSerializer(serializers.Serializer):
    """Serialize the statistics of a study (counts, curators, creator) for the elasticsearch index."""

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
            "creator",
            "curators",
            "substances",
        ]

        read_only_fields = fields


@swagger_auto_schema(tags=["Studies"])
class StudyElasticSerializer(serializers.ModelSerializer):
    """Serialize a study, with its reference, subject sets, comments and counts, for the elasticsearch index."""

    pk = serializers.CharField()
    sid = serializers.CharField(help_text="This is the string id.")
    reference = ReferenceElasticSerializer()

    name = serializers.CharField(
        help_text="Name of the study. The convention is to deduce the name from the "
        "refererence with the following pattern "
        "'[Author][PublicationYear][A-Z(optional)]'."
    )
    licence = serializers.CharField(
        help_text="Licence",
    )
    access = serializers.CharField()

    curators = CuratorRatingElasticSerializer(
        many=True,
    )
    creator = UserElasticSerializer()
    collaborators = UserElasticSerializer(
        many=True,
    )

    substances = SidNameLabelSerializer(
        many=True,
    )

    files = serializers.SerializerMethodField()

    comments = CommentElasticSerializer(
        many=True,
    )
    descriptions = DescriptionElasticSerializer(
        many=True,
    )
    groupset = GroupSetElasticSmallSerializer()
    individualset = IndividualSetElasticSmallSerializer()
    interventionset = InterventionSetElasticSmallSerializer()
    outputset = OutputSetElasticSmallSerializer()
    dataset = DataSetElasticSmallSerializer()

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
            "subset_count",
            "timecourse_count",
            "scatter_count",
            "reference",
            "reference_date",
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
            "dataset",
        ]

        read_only_fields = fields

    @staticmethod
    def get_substances(obj):
        """Return the study's substances as a list, or an empty list if there are none."""
        if obj.substances:
            return list(obj.substances)
        return []

    def get_files(self, obj):
        """Return the study's files if the request user has file permission for the study, else an empty list."""
        if get_study_file_permission(self.context["request"].user, obj):
            files_serializer = DataFileElasticSerializer(
                obj.files, many=True, read_only=True
            )
            return files_serializer.data

        return []


class StudyAnalysisSerializer(serializers.Serializer):
    """Serialize a reduced set of study fields for analysis, resolving creator, curators, substances and reference."""

    sid = serializers.CharField()
    name = serializers.CharField()
    licence = serializers.CharField()
    access = serializers.CharField()
    date = serializers.DateField()

    creator = serializers.SerializerMethodField()
    curators = serializers.SerializerMethodField()
    substances = serializers.SerializerMethodField()

    reference_pmid = serializers.SerializerMethodField()
    reference_title = serializers.SerializerMethodField()
    reference_date = serializers.DateField()

    def get_substances(self, obj):
        """Return the labels of the study's substances."""
        return [s["label"] for s in obj.substances]

    def get_reference_pmid(self, obj):
        """Return the pmid of the study's reference."""
        return obj.reference["pmid"]

    def get_reference_title(self, obj):
        """Return the title of the study's reference."""
        return obj.reference["title"]

    def get_creator(self, obj):
        """Return the username of the study's creator."""
        return obj.creator["username"]

    def get_curators(self, obj):
        """Return the usernames of the study's curators."""
        return [s["username"] for s in obj.curators]

    class Meta:
        fields = [
            "sid",
            "name",
            "licence",
            "access",
            "date",
            "creator",
            "curators",
            "substances",
            "reference_pmid",
            "reference_title",
            "reference_date",
        ]

        read_only_fields = fields

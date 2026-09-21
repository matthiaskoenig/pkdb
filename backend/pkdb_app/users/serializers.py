"""Serializers for reading, creating and registering user accounts."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_email_auth import models, signals
from rest_email_auth.authentication import VerifiedEmailBackend
from rest_email_auth.serializers import RegistrationSerializer
from rest_framework import serializers
from rest_framework.authtoken.serializers import AuthTokenSerializer

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Read and update serializer for a user's name and group memberships."""

    groups = serializers.SlugRelatedField(
        queryset=Group.objects.all(), slug_field="name", required=True, many=True
    )

    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "groups")
        read_only_fields = ("username",)


class UserGroupSerializer(serializers.ModelSerializer):
    """Read and update serializer for a group's name and permissions."""

    class Meta:
        model = Group
        fields = ["name", "permissions"]


class AuthTokenSerializerCostum(AuthTokenSerializer):
    """Auth token serializer with an additional requirement.

    The email of the user has to be verified.
    """

    def validate(self, attrs):
        """Reject the credentials unless the user's email address has been verified."""
        result = super().validate(attrs)

        user = VerifiedEmailBackend().authenticate(
            request=self.context.get("request"),
            password=attrs["password"],
            email=result["user"].email,
        )
        if not user:
            msg = "User is not verified. Check your mail for the verification key."
            raise serializers.ValidationError(msg, code="authorization")

        return result


class UserRegistrationSerializer(RegistrationSerializer):
    """Registration serializer that creates an unverified user.

    The user is pending the email confirmation.
    """

    class Meta:
        extra_kwargs = {
            "password": {
                "style": {"input_type": "password"},
                "write_only": True,
            }
        }
        fields = (get_user_model().USERNAME_FIELD, "email", "password")
        model = get_user_model()

    def create(self, validated_data):
        """Create a new user from the data passed to the serializer.

        If the provided email has not been verified yet, the user is
        created and a verification email is sent to the address.
        Otherwise we send a notification to the email address that
        someone attempted to register with an email that's already been
        verified.

        Args:
            validated_data (dict):
                The data passed to the serializer after it has been
                validated.

        Returns:
            A new user created from the provided data.
        """
        email = validated_data.pop("email")

        password = validated_data.pop("password")

        # We don't save the user instance yet in case the provided email
        # address already exists.
        user = get_user_model()(**validated_data)
        user.set_password(password)

        # We set an ephemeral email property so that it is included in
        # the data returned by the serializer.
        user.email = email

        email_query = models.EmailAddress.objects.filter(email=email)

        if email_query.exists():
            existing_email = email_query.get()
            existing_email.send_duplicate_notification()
        else:
            user.save()
            user.groups.clear()
            basic_group = Group.objects.get(name="basic")
            user.groups.add(basic_group)

            email_instance = models.EmailAddress.objects.create(
                email=email, is_primary=True, user=user
            )
            email_instance.send_confirmation()

            signals.user_registered.send(sender=self.__class__, user=user)
        return user


class CreateUserSerializer(serializers.ModelSerializer):
    """Admin serializer that creates or updates a user account.

    The account has a verified email and groups.
    """

    groups = serializers.SlugRelatedField(
        queryset=Group.objects.all(), slug_field="name", required=True, many=True
    )

    def create(self, validated_data):
        """Create the user with a hashed password and a verified email.

        The given groups are assigned to the user.
        """
        # call create_user on user object. Without this
        # the password will be stored in plain text.
        groups = validated_data.pop("groups", ["basic"])
        user = User.objects.create_user(**validated_data)
        self.create_verified_email(user)
        if groups:
            user.groups.clear()
            user.groups.add(*groups)
        user.save()
        return user

    def update(self, instance, validated_data):
        """Update the user's fields and replace its groups when new groups are given."""
        # call create_user on user object. Without this
        # the password will be stored in plain text.
        groups = validated_data.pop("groups", [])
        for name, value in validated_data.items():
            setattr(instance, name, value)
        instance.save()

        if groups:
            instance.groups.clear()
            instance.groups.add(*groups)
            instance.save()
        return instance

    def create_verified_email(self, user):
        """Create an already verified, primary email address for the user."""
        email_dict = {
            "email": user.email,
            "is_primary": True,
            "is_verified": True,
            "user": user,
        }
        return models.EmailAddress.objects.create(**email_dict)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "password",
            "first_name",
            "last_name",
            "email",
            "auth_token",
            "groups",
        )
        read_only_fields = ("auth_token",)
        extra_kwargs = {"password": {"write_only": True}}


# -----------------------------------------------------------------------------
# Elastic Serializer
# -----------------------------------------------------------------------------
class UserElasticSerializer(serializers.ModelSerializer):
    """Elasticsearch read serializer exposing a user's username and name."""

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
        )
        read_only_fields = ("username",)

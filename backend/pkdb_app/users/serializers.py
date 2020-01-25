from django.contrib.auth import get_user_model
from rest_email_auth.authentication import VerifiedEmailBackend
from rest_email_auth.serializers import RegistrationSerializer, EmailSerializer
from rest_framework import serializers
from rest_framework.authtoken.serializers import AuthTokenSerializer

from .models import User
from django.contrib.auth.models import Group
from rest_email_auth import models, signals


class UserSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(
        queryset=Group.objects.all(),
        slug_field="name",
        required=True,
        many=True
    )

    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "groups")
        read_only_fields = ("username",)


class UserGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["name", "permissions"]


class AuthTokenSerializerCostum(AuthTokenSerializer):
    def validate(self, attrs):
        result = super().validate(attrs)

        user = VerifiedEmailBackend().authenticate(request=self.context.get('request'),
                                                   password=attrs["password"], email=result["user"].email)
        if not user:
            msg = 'User is not verified. Check your mail for the verification key.'
            raise serializers.ValidationError(msg, code='authorization')

        return result


class UserRegistrationSerializer(RegistrationSerializer):
    class Meta(object):
        extra_kwargs = {
            "password": {
                "style": {"input_type": "password"},
                "write_only": True,
            }
        }
        fields = (get_user_model().USERNAME_FIELD, "email", "password")
        model = get_user_model()

    def create(self, validated_data):
        """
          Create a new user from the data passed to the serializer.

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
    groups = serializers.SlugRelatedField(
        queryset=Group.objects.all(),
        slug_field="name",
        required=True,
        many=True
    )

    def create(self, validated_data):
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
        email_dict = {"email": user.email, "is_primary": True, "is_verified": True, "user": user}
        email = models.EmailAddress.objects.create(**email_dict)
        return email

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
            "groups"
        )
        read_only_fields = ("auth_token",)
        extra_kwargs = {"password": {"write_only": True}}


# -----------------------------------------------------------------------------
# Elastic Serializer
# -----------------------------------------------------------------------------
class UserElasticSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ( "username", "first_name", "last_name",)
        read_only_fields = ("username",)

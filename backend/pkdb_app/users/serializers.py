from rest_framework import serializers
from .models import User
from django.contrib.auth.models import Group

class UserSerializer(serializers.ModelSerializer):

    groups = serializers.SlugRelatedField(
        queryset=Group.objects.all(),
        slug_field="name",
        required=True,
        many=True
    )
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name","groups")
        read_only_fields = ("username",)


class UserGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["name","permissions"]



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
        groups = validated_data.pop("groups", [])
        user = User.objects.create_user(**validated_data)
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


###############################################################################################
# Elastic Serializer
###############################################################################################


class UserElasticSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "first_name", "last_name","username")
        read_only_fields = ("username",)

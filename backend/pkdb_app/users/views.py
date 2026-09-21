"""Viewsets for managing and authenticating user accounts."""

from django.contrib.auth.models import Group
from rest_framework import mixins, viewsets
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import IsAdminUser

from pkdb_app.users.models import User
from pkdb_app.users.serializers import (
    AuthTokenSerializerCostum,
    CreateUserSerializer,
    UserGroupSerializer,
    UserSerializer,
)


class UserViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """Retrieve and update user accounts, restricted to admin users."""

    swagger_schema = None
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAdminUser,)


class UserGroupViewSet(viewsets.ModelViewSet):
    """Manage the available user groups, restricted to admin users."""

    swagger_schema = None
    queryset = Group.objects.all()
    serializer_class = UserGroupSerializer
    permission_classes = (IsAdminUser,)


class UserCreateViewSet(
    mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """Create and update user accounts, restricted to admin users."""

    swagger_schema = None
    queryset = User.objects.all()
    serializer_class = CreateUserSerializer
    permission_classes = (IsAdminUser,)

    # def create(self, request, *args, **kwargs):
    #    return super().create(request, *args, **kwargs)


class ObtainAuthTokenCustom(ObtainAuthToken):
    """Issue an auth token, requiring the account's email to be verified."""

    swagger_schema = None
    serializer_class = AuthTokenSerializerCostum

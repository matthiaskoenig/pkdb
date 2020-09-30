from django.contrib.auth.models import Group
from rest_framework import viewsets, mixins
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import IsAdminUser

from pkdb_app.users.models import User
from pkdb_app.users.serializers import AuthTokenSerializerCostum
from pkdb_app.users.serializers import UserGroupSerializer, CreateUserSerializer, UserSerializer


class UserViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """
    Updates and retrieves user accounts
    """
    swagger_schema = None
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAdminUser,)


class UserGroupViewSet(viewsets.ModelViewSet):
    swagger_schema = None
    queryset = Group.objects.all()
    serializer_class = UserGroupSerializer
    permission_classes = (IsAdminUser,)


class UserCreateViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    Creates user accounts
    """
    swagger_schema = None
    queryset = User.objects.all()
    serializer_class = CreateUserSerializer
    permission_classes = (IsAdminUser,)

    # def create(self, request, *args, **kwargs):
    #    return super().create(request, *args, **kwargs)


class ObtainAuthTokenCustom(ObtainAuthToken):
    swagger_schema = None
    serializer_class = AuthTokenSerializerCostum

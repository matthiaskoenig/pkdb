from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAdminUser
from .models import User
from .serializers import CreateUserSerializer, UserSerializer


class UserViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """
    Updates and retrieves user accounts
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAdminUser,)


class UserCreateViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    Creates user accounts
    """

    queryset = User.objects.all()
    serializer_class = CreateUserSerializer
    permission_classes = (IsAdminUser,)



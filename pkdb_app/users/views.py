from rest_framework import viewsets, mixins, generics
from rest_framework.permissions import AllowAny, IsAdminUser
from .models import User
from .serializers import CreateUserSerializer, UserSerializer, UserReadSerializer


class UserViewSet(mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  viewsets.GenericViewSet):
    """
    Updates and retrieves user accounts
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (AllowAny,)
    # permission_classes = (IsAdminUser,)



class UserCreateViewSet(mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    """
    Creates user accounts
    """
    queryset = User.objects.all()
    serializer_class = CreateUserSerializer
    permission_classes = (AllowAny,)
    # permission_classes = (IsAdminUser,)


class UserReadViewSet(viewsets.ModelViewSet):
    """
    Updates and retrieves user accounts
    """
    queryset = User.objects.all()
    serializer_class = UserReadSerializer
    permission_classes = (AllowAny,)
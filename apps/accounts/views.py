from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.accounts.models import User
from apps.accounts.permissions import IsAdministrator
from apps.accounts.serializers import RegisterSerializer, UserRoleSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    @extend_schema(summary="Criar uma conta de usuário")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CurrentUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
    queryset = User.objects.order_by("first_name", "username")
    serializer_class = UserSerializer
    permission_classes = [IsAdministrator]


class UserAccessUpdateView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRoleSerializer
    permission_classes = [IsAdministrator]
    http_method_names = ["patch", "options"]

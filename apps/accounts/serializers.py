from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "role_display",
            "is_active",
        )
        read_only_fields = ("id", "username", "role", "role_display", "is_active")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirmation = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirmation",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirmation"):
            raise serializers.ValidationError({"password_confirmation": "As senhas não coincidem."})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(role=User.Role.USER, **validated_data)


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("role", "is_active")

    def validate(self, attrs):
        request = self.context["request"]
        if request.user == self.instance:
            raise serializers.ValidationError("Altere o acesso de outro administrador.")
        return attrs

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Department

User = get_user_model()


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "code", "description"]


class UserSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "phone",
            "avatar",
            "department",
            "must_change_password",
            "date_joined",
            "last_login",
        ]
        read_only_fields = [
            "id",
            "email",
            "role",
            "department",
            "must_change_password",
            "date_joined",
            "last_login",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["id", "email", "password", "first_name", "last_name", "role"]
        read_only_fields = ["id", "role"]

    def validate(self, attrs):
        candidate = User(email=attrs.get("email"), first_name=attrs.get("first_name", ""))
        try:
            validate_password(attrs["password"], user=candidate)
        except Exception as exc:  # django ValidationError
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate_new_password(self, value):
        try:
            validate_password(value, user=self.context["request"].user)
        except Exception as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

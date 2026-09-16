from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from . import services
from .models import Department, FacultyProfile, StudentProfile

User = get_user_model()


class DepartmentSerializer(serializers.ModelSerializer):
    user_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Department
        fields = ["id", "name", "code", "description", "user_count"]


class DepartmentBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "code"]


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = ["roll_number", "batch", "year", "bio"]


class FacultyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacultyProfile
        fields = ["employee_id", "designation", "bio"]


PROFILE_SERIALIZERS = {
    "student": ("student_profile", StudentProfileSerializer),
    "faculty": ("faculty_profile", FacultyProfileSerializer),
}


@extend_schema_field(
    {
        "type": "object",
        "nullable": True,
        "description": "Student: roll_number, batch, year, bio. Faculty: employee_id, "
        "designation, bio. Admin: null.",
        "additionalProperties": True,
    }
)
class ProfileField(serializers.Field):
    """Read: the role's profile (or null). Write: a dict applied in ``update``."""

    def __init__(self, **kwargs):
        kwargs.setdefault("source", "*")
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)

    def to_representation(self, user):
        entry = PROFILE_SERIALIZERS.get(user.role)
        if not entry:
            return None
        attr, serializer_cls = entry
        profile = getattr(user, attr, None)
        return serializer_cls(profile).data if profile else None

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("Expected an object.")
        return {"profile": data}


class UserSerializer(serializers.ModelSerializer):
    """Current user (``auth/me/``). Users may edit names, phone, avatar and profile bio."""

    profile_editable_fields = {"bio"}

    department = DepartmentBriefSerializer(read_only=True)
    profile = ProfileField()

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
            "profile",
            "must_change_password",
            "is_active",
            "date_joined",
            "last_login",
        ]
        read_only_fields = [
            "id",
            "email",
            "role",
            "department",
            "must_change_password",
            "is_active",
            "date_joined",
            "last_login",
        ]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)
        instance = super().update(instance, validated_data)
        if profile_data:
            services.update_profile(instance, profile_data, self.profile_editable_fields)
        return instance


class AdminUserSerializer(serializers.ModelSerializer):
    """Full user management for admins. Writes go through ``services``."""

    role = serializers.ChoiceField(choices=User.Role.choices)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), allow_null=True, required=False
    )
    department_detail = DepartmentBriefSerializer(source="department", read_only=True)
    profile = ProfileField()
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "phone",
            "department",
            "department_detail",
            "profile",
            "password",
            "is_active",
            "must_change_password",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["id", "must_change_password", "date_joined", "last_login"]

    def validate(self, attrs):
        password = attrs.get("password")
        if password:
            candidate = self.instance or User(
                email=attrs.get("email", ""), first_name=attrs.get("first_name", "")
            )
            try:
                validate_password(password, user=candidate)
            except Exception as exc:
                raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs


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


class SetPasswordSerializer(serializers.Serializer):
    """Choose a password from a one-time invite or reset link."""

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from .password_links import user_for_link

        user = user_for_link(attrs["uid"], attrs["token"])
        if user is None:
            raise serializers.ValidationError(
                {"token": ["This link is invalid or has expired. Ask for a new one."]}
            )
        try:
            validate_password(attrs["new_password"], user=user)
        except Exception as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc
        attrs["user"] = user
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

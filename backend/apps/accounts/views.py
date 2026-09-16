from django.contrib.auth import get_user_model
from django.core.cache import cache
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import exceptions, generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.audit.services import log_action
from apps.core.authentication import stamp_token

from . import password_links, services
from .serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LogoutSerializer,
    RegisterSerializer,
    SetPasswordSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def perform_create(self, serializer):
        data = serializer.validated_data
        serializer.instance = services.register_student(
            email=data["email"],
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
        )


LOCKOUT_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


def _lock_key(email):
    return f"login-fail:{(email or '').strip().lower()}"


class ForgeTokenObtainSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        return stamp_token(super().get_token(user), user)


class LoginView(TokenObtainPairView):
    """Obtain tokens. Five failed attempts for one email lock it for 15 minutes."""

    serializer_class = ForgeTokenObtainSerializer
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        key = _lock_key(request.data.get("email"))
        if cache.get(key, 0) >= LOCKOUT_ATTEMPTS:
            return Response(
                {
                    "detail": "Too many failed sign-in attempts. Try again in 15 minutes.",
                    "code": "login_locked",
                    "errors": {},
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        try:
            response = super().post(request, *args, **kwargs)
        except exceptions.AuthenticationFailed:
            # Wrong email/password or inactive account: count it, then let DRF answer 401.
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, 1, LOCKOUT_SECONDS)
            raise
        cache.delete(key)
        return response


class RefreshView(TokenRefreshView):
    authentication_classes: list = []


class LogoutView(APIView):
    @extend_schema(request=LogoutSerializer, responses={205: None})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.blacklist_refresh_token(serializer.validated_data["refresh"])
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


TokenPairResponse = inline_serializer(
    "TokenPair", {"access": serializers.CharField(), "refresh": serializers.CharField()}
)


class ChangePasswordView(APIView):
    @extend_schema(request=ChangePasswordSerializer, responses=TokenPairResponse)
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        tokens = services.change_password(request.user, serializer.validated_data["new_password"])
        return Response(tokens)


class SetPasswordView(APIView):
    """Set a password from an invite/reset link. Signs the user in on success."""

    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(request=SetPasswordSerializer, responses=TokenPairResponse)
    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        tokens = password_links.set_password_from_link(data["user"], data["new_password"])
        log_action(data["user"], "user.set_password_link", target=data["user"], request=request)
        cache.delete(_lock_key(data["user"].email))
        return Response(tokens)


class ForgotPasswordView(APIView):
    """Email a reset link. Always 204 so the endpoint can't be used to probe emails."""

    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(request=ForgotPasswordSerializer, responses={204: None})
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"], is_active=True
        ).first()
        if user is not None:
            password_links.send_link(user, purpose="forgot")
        return Response(status=status.HTTP_204_NO_CONTENT)

from django.core.cache import cache
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import exceptions, generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import services
from .serializers import (
    ChangePasswordSerializer,
    LogoutSerializer,
    RegisterSerializer,
    UserSerializer,
)


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


class LoginView(TokenObtainPairView):
    """Obtain tokens. Five failed attempts for one email lock it for 15 minutes."""

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


class ChangePasswordView(APIView):
    @extend_schema(
        request=ChangePasswordSerializer,
        responses=inline_serializer(
            "TokenPair", {"access": serializers.CharField(), "refresh": serializers.CharField()}
        ),
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        tokens = services.change_password(request.user, serializer.validated_data["new_password"])
        return Response(tokens)

"""JWT authentication with server-side revocation and forced password change."""

from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication

# Endpoints a user who must change their password can still reach.
PASSWORD_CHANGE_ALLOWED = {
    "auth-me",
    "auth-change-password",
    "auth-logout",
    "auth-token-refresh",
}


class TokenRevoked(exceptions.AuthenticationFailed):
    default_detail = "This session has ended. Sign in again."
    default_code = "token_revoked"


class PasswordChangeRequired(exceptions.PermissionDenied):
    default_detail = "Change your password to continue."
    default_code = "password_change_required"


class ForgeJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result

        cutoff = getattr(user, "tokens_valid_after", None)
        if cutoff is not None and int(token.get("iat", 0)) < int(cutoff.timestamp()):
            raise TokenRevoked()

        if getattr(user, "must_change_password", False):
            match = getattr(request._request, "resolver_match", None)
            if match is None or match.url_name not in PASSWORD_CHANGE_ALLOWED:
                raise PasswordChangeRequired()
        return user, token

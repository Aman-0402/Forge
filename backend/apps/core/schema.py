"""OpenAPI extensions. Imported from CoreConfig.ready()."""

from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme


class ForgeJWTScheme(SimpleJWTScheme):
    target_class = "apps.core.authentication.ForgeJWTAuthentication"

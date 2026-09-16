from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.files import SignedFileView, public_media

api_v1 = [
    path("files/<str:token>/<str:filename>", SignedFileView.as_view(), name="signed-file"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.audit.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.courses.urls")),
    path("", include("apps.exams.urls")),
    path("", include("apps.coding.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    # Only public folders (avatars, course thumbnails). Private uploads use signed links.
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", public_media)]

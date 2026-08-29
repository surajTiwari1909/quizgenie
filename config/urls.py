from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from core.views import api_not_found

handler404 = "core.views.api_not_found"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("documents/", include("documents.urls")),
    path("games/", include("games.urls")),
    path("multiplayer/", include("multiplayer.urls")),
    path("quizzes/", include("quizzes.urls")),
    path("", include("core.urls")),
    path("auth/", include("users.urls")),
    path("profiles/", include("profiles.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Keep this last so valid application and development media routes take precedence.
urlpatterns += [re_path(r"^.*$", api_not_found, name="api-not-found")]

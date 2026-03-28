from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from notes.views import dashboard, login_view, register_view, note_view, forgot_password_view, reset_password_view, verify_email_view

admin.site.site_header = "Note_App Admin"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", dashboard),
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path("forgot_password/", forgot_password_view, name="forgot_password"),
    path("reset_password/", reset_password_view, name="reset_password"),
    path("verify_email/", verify_email_view, name="verify_email"),
    path("view_notes/", note_view, name="view_notes"),


    path("api/", include("notes.urls")),
    path("", include("django_prometheus.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

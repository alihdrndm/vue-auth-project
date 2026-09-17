from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

from eingang.accuracy_api import AccuracyView
from eingang.docs_view import DocsView
from eingang.health import HealthzView, ReadyzView

urlpatterns = [
    path("healthz", HealthzView.as_view(), name="healthz"),
    path("readyz", ReadyzView.as_view(), name="readyz"),
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("suppliers.urls")),
    path("api/v1/", include("sandbox.urls")),
    path("api/v1/", include("invoices.urls")),
    path("api/v1/", include("exports.urls")),
    path("api/v1/", include("invoices.rules_urls")),
    path("api/v1/", include("invoices.stats_urls")),
    path("api/v1/accuracy", AccuracyView.as_view(), name="accuracy"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs", DocsView.as_view(url_name="schema"), name="docs"),
]

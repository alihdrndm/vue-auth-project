from django.urls import path
from drf_spectacular.views import SpectacularAPIView

from eingang.docs_view import DocsView
from eingang.health import HealthzView, ReadyzView

urlpatterns = [
    path("healthz", HealthzView.as_view(), name="healthz"),
    path("readyz", ReadyzView.as_view(), name="readyz"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs", DocsView.as_view(url_name="schema"), name="docs"),
]

"""Swagger UI at /docs, with a Content-Security-Policy of its own."""

from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularSwaggerSplitView
from rest_framework.request import Request

# The split view serves its init script from this same URL (?script), so no inline
# script is needed. Swagger UI itself comes from the pinned jsdelivr build and sets
# inline styles at runtime.
DOCS_CSP = (
    "default-src 'none'; "
    "script-src 'self' https://cdn.jsdelivr.net; "
    "style-src 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://cdn.jsdelivr.net; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)


class DocsView(SpectacularSwaggerSplitView):
    @extend_schema(exclude=True)
    def get(self, request: Request, *args: object, **kwargs: object) -> HttpResponse:
        response: HttpResponse = super().get(request, *args, **kwargs)  # type: ignore[no-untyped-call]  # drf-spectacular is untyped
        response["Content-Security-Policy"] = DOCS_CSP
        return response

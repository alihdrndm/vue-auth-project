"""Describes the session cookie authentication in the OpenAPI schema."""

from typing import Any

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.openapi import AutoSchema


class SessionAuthenticationScheme(OpenApiAuthenticationExtension):  # type: ignore[no-untyped-call]  # drf-spectacular is untyped
    target_class = "accounts.authentication.SessionAuthentication"
    name = "sessionAuth"

    def get_security_definition(
        self, auto_schema: AutoSchema
    ) -> dict[str, Any]:  # boundary: OpenAPI document
        return {"type": "apiKey", "in": "cookie", "name": "sessionid"}

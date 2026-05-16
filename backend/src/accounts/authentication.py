"""Session authentication for the API (HANDOFF "Auth")."""

from typing import Any

from django.contrib.auth import logout
from rest_framework import authentication, exceptions
from rest_framework.request import Request

from accounts.models import User
from eingang import clock
from eingang.problem import ProblemError


def sandbox_expired() -> ProblemError:
    return ProblemError(
        401,
        "SANDBOX_EXPIRED",
        "Sandbox expired",
        "This sandbox has expired. Open a new one.",
    )


class SessionAuthentication(authentication.SessionAuthentication):
    """DRF's session authentication, answering 401 (not 403) and ending expired sandboxes."""

    def authenticate_header(self, request: Request) -> str:
        # Any value here makes DRF answer 401 NOT_AUTHENTICATED instead of 403.
        return "Session"

    def authenticate(self, request: Request) -> tuple[User, Any] | None:  # boundary: rest_framework
        result = super().authenticate(request)
        if result is None:
            return None
        user = result[0]
        organization = user.organization
        if (
            organization.is_sandbox
            and organization.expires_at is not None
            and organization.expires_at <= clock.now()
        ):
            # A sandbox visitor cannot sign in again, so the session simply ends.
            logout(request._request)
            raise sandbox_expired()
        return user, result[1]

    def enforce_csrf(self, request: Request) -> None:
        try:
            super().enforce_csrf(request)
        except exceptions.PermissionDenied as error:
            raise ProblemError(
                403,
                "CSRF_FAILED",
                "CSRF check failed",
                "Fetch GET /api/v1/auth/csrf first, then send its token in the X-CSRFToken header.",
            ) from error

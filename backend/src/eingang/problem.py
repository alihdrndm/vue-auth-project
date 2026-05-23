"""RFC 9457 problem+json responses: the one error format of the API.

Every error code used here is documented in docs/ERRORS.md.
"""

import logging
import math
from collections.abc import Mapping
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404, HttpRequest, JsonResponse
from rest_framework import exceptions

from eingang.log import request_id_var

PROBLEM_CONTENT_TYPE = "application/problem+json"
ERRORS_DOC_URL = "https://github.com/alihdrndm/eingang/blob/main/docs/ERRORS.md"

logger = logging.getLogger(__name__)


class ProblemError(Exception):
    """Raise from a view to answer with a specific documented error code."""

    def __init__(
        self,
        status: int,
        code: str,
        title: str,
        detail: str,
        *,
        errors: list[dict[str, str]] | None = None,
        extra: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.errors = errors
        self.extra = extra or {}
        self.headers: Mapping[str, str] = headers or {}


def problem_response(
    status: int,
    code: str,
    title: str,
    detail: str,
    *,
    errors: list[dict[str, str]] | None = None,
    extra: Mapping[str, object] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JsonResponse:
    body: dict[str, object] = {
        "type": f"{ERRORS_DOC_URL}#{code.lower()}",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
        "instance": request_id_var.get(),
    }
    if errors is not None:
        body["errors"] = errors
    body.update(extra or {})
    response = JsonResponse(body, status=status, content_type=PROBLEM_CONTENT_TYPE)
    for name, value in (headers or {}).items():
        response[name] = value
    return response


def from_problem_error(error: ProblemError) -> JsonResponse:
    return problem_response(
        error.status,
        error.code,
        error.title,
        error.detail,
        errors=error.errors,
        extra=error.extra,
        headers=error.headers,
    )


def not_found() -> JsonResponse:
    return problem_response(404, "NOT_FOUND", "Not found", "No resource exists at this path.")


def for_status(status: int) -> JsonResponse:
    """Problem for an error response that Django produced outside our views."""
    if status >= 500:
        return internal_error()
    if status == 404:
        return not_found()
    if status == 403:
        return problem_response(403, "FORBIDDEN_ROLE", "Not allowed", "You can't do this.")
    if status == 405:
        return problem_response(
            405,
            "METHOD_NOT_ALLOWED",
            "Method not allowed",
            "This path does not accept this method.",
        )
    return problem_response(
        400, "MALFORMED_REQUEST", "Malformed request", "The request could not be processed."
    )


def csrf_failure(request: HttpRequest, reason: str = "") -> JsonResponse:
    """Django's CSRF_FAILURE_VIEW. The reason is not echoed; it can name cookie details."""
    return problem_response(
        403,
        "CSRF_FAILED",
        "CSRF check failed",
        "Fetch GET /api/v1/auth/csrf first, then send its token in the X-CSRFToken header.",
    )


def internal_error() -> JsonResponse:
    return problem_response(
        500, "INTERNAL", "Internal error", "Something went wrong on our side. Try again later."
    )


def _flatten_validation_errors(
    detail: Any,  # boundary: rest_framework error detail
    path: str = "",
) -> list[dict[str, str]]:
    if isinstance(detail, Mapping):
        entries: list[dict[str, str]] = []
        for key, value in detail.items():
            child = str(key) if not path else f"{path}.{key}"
            if key == "non_field_errors":
                child = path
            entries += _flatten_validation_errors(value, child)
        return entries
    if isinstance(detail, list):
        if all(isinstance(item, exceptions.ErrorDetail) for item in detail):
            return [_entry(path, item) for item in detail]
        entries = []
        for index, item in enumerate(detail):
            entries += _flatten_validation_errors(item, f"{path}[{index}]")
        return entries
    return [_entry(path, detail)]


def _entry(path: str, item: Any) -> dict[str, str]:  # boundary: rest_framework ErrorDetail
    code = getattr(item, "code", "invalid")
    return {"path": path, "code": str(code), "message": str(item)}


# Each DRF exception class maps to one documented code. Order matters: subclasses first.
_DRF_CODES: list[tuple[type[exceptions.APIException], int, str, str]] = [
    (exceptions.NotAuthenticated, 401, "NOT_AUTHENTICATED", "Not signed in"),
    (exceptions.AuthenticationFailed, 401, "NOT_AUTHENTICATED", "Not signed in"),
    (exceptions.PermissionDenied, 403, "FORBIDDEN_ROLE", "Not allowed"),
    (exceptions.NotFound, 404, "NOT_FOUND", "Not found"),
    (exceptions.MethodNotAllowed, 405, "METHOD_NOT_ALLOWED", "Method not allowed"),
    (exceptions.NotAcceptable, 406, "NOT_ACCEPTABLE", "Not acceptable"),
    (exceptions.UnsupportedMediaType, 415, "UNSUPPORTED_MEDIA_TYPE", "Unsupported media type"),
    (exceptions.ParseError, 400, "MALFORMED_REQUEST", "Malformed request"),
    (exceptions.Throttled, 429, "RATE_LIMITED", "Too many requests"),
]


def exception_handler(exc: Exception, context: Mapping[str, object]) -> JsonResponse | None:
    """DRF's EXCEPTION_HANDLER. Returning None lets the exception reach the middleware (500)."""
    if isinstance(exc, ProblemError):
        return from_problem_error(exc)
    if isinstance(exc, Http404):
        return not_found()
    if isinstance(exc, exceptions.ValidationError):
        return problem_response(
            422,
            "VALIDATION_FAILED",
            "Validation failed",
            "One or more fields are invalid.",
            errors=_flatten_validation_errors(exc.detail),
        )
    for exc_class, status, code, title in _DRF_CODES:
        if isinstance(exc, exc_class):
            headers: dict[str, str] = {}
            # DRF sets this for 401s so clients learn the scheme (Session, from M3 on).
            auth_header: str | None = getattr(exc, "auth_header", None)
            if auth_header:
                headers["WWW-Authenticate"] = auth_header
            # The stubs omit Throttled.wait (seconds until the next request is allowed).
            wait: float | None = getattr(exc, "wait", None)
            if wait is not None:
                headers["Retry-After"] = str(math.ceil(wait))
            return problem_response(status, code, title, str(exc.detail), headers=headers)
    if isinstance(exc, exceptions.APIException):
        # An APIException we did not map is a programming error, not a client error.
        logger.error("Unmapped API exception %s", type(exc).__name__)
        return internal_error()
    if isinstance(exc, DjangoPermissionDenied):
        return problem_response(403, "FORBIDDEN_ROLE", "Not allowed", "You can't do this.")
    return None

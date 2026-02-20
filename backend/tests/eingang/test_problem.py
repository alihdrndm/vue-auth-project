import json

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions

from eingang.problem import (
    ERRORS_DOC_URL,
    PROBLEM_CONTENT_TYPE,
    ProblemError,
    exception_handler,
    for_status,
)


def handle(exc: Exception) -> dict[str, object]:
    response = exception_handler(exc, {})
    assert response is not None
    assert response["Content-Type"] == PROBLEM_CONTENT_TYPE
    body: dict[str, object] = json.loads(response.content)
    assert body["status"] == response.status_code
    return body


def test_validation_failed_has_one_entry_per_field_problem() -> None:
    body = handle(
        exceptions.ValidationError(
            {"email": ["Enter a valid email."], "lines": [{"quantity": ["Required."]}]}
        )
    )
    assert body["status"] == 422
    assert body["code"] == "VALIDATION_FAILED"
    assert body["type"] == f"{ERRORS_DOC_URL}#validation_failed"
    assert body["errors"] == [
        {"path": "email", "code": "invalid", "message": "Enter a valid email."},
        {"path": "lines[0].quantity", "code": "invalid", "message": "Required."},
    ]


def test_non_field_errors_use_the_parent_path() -> None:
    body = handle(exceptions.ValidationError({"non_field_errors": ["Pick one."]}))
    assert body["errors"] == [{"path": "", "code": "invalid", "message": "Pick one."}]


def test_not_authenticated_is_401() -> None:
    assert handle(exceptions.NotAuthenticated())["code"] == "NOT_AUTHENTICATED"


def test_401_carries_the_authenticate_header_drf_provides() -> None:
    exc = exceptions.NotAuthenticated()
    exc.auth_header = "Session"  # type: ignore[attr-defined]  # set by DRF's APIView
    response = exception_handler(exc, {})
    assert response is not None
    assert response["WWW-Authenticate"] == "Session"


def test_errors_django_produces_map_to_documented_codes() -> None:
    assert json.loads(for_status(400).content)["code"] == "MALFORMED_REQUEST"
    assert json.loads(for_status(403).content)["code"] == "FORBIDDEN_ROLE"
    assert json.loads(for_status(404).content)["code"] == "NOT_FOUND"
    assert json.loads(for_status(405).content)["code"] == "METHOD_NOT_ALLOWED"
    assert json.loads(for_status(502).content)["code"] == "INTERNAL"


def test_permission_denied_is_forbidden_role() -> None:
    assert handle(exceptions.PermissionDenied())["code"] == "FORBIDDEN_ROLE"
    assert handle(DjangoPermissionDenied())["code"] == "FORBIDDEN_ROLE"


def test_http404_is_not_found() -> None:
    assert handle(Http404())["code"] == "NOT_FOUND"


def test_rate_limited_sets_retry_after() -> None:
    response = exception_handler(exceptions.Throttled(wait=29.4), {})
    assert response is not None
    assert response.status_code == 429
    assert response["Retry-After"] == "30"


def test_other_mapped_drf_errors() -> None:
    assert handle(exceptions.MethodNotAllowed("POST"))["code"] == "METHOD_NOT_ALLOWED"
    assert handle(exceptions.NotAcceptable())["code"] == "NOT_ACCEPTABLE"
    assert handle(exceptions.UnsupportedMediaType("text/plain"))["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert handle(exceptions.ParseError())["code"] == "MALFORMED_REQUEST"


def test_unmapped_api_exception_is_internal_without_details() -> None:
    body = handle(exceptions.APIException("secret internal message"))
    assert body["code"] == "INTERNAL"
    assert "secret" not in str(body)


def test_problem_error_carries_code_and_extension_members() -> None:
    body = handle(ProblemError(409, "INVALID_TRANSITION", "Conflict", "No.", extra={"x": 1}))
    assert body["code"] == "INVALID_TRANSITION"
    assert body["x"] == 1


def test_other_exceptions_are_left_to_the_middleware() -> None:
    assert exception_handler(RuntimeError("boom"), {}) is None

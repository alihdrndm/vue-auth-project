"""Endpoint by error-code matrix for the M3 API (HANDOFF "HTTP API", "Errors").

The per-feature tests cover single cases; this module checks every session endpoint,
every role rule of the endpoint table, the problem+json shape, and that docs/ERRORS.md
documents every code the source uses.
"""

import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from django.core.cache import cache
from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.test.client import MULTIPART_CONTENT

from eingang import temporal_client
from eingang.problem import ERRORS_DOC_URL, PROBLEM_CONTENT_TYPE
from tests.conftest import ApiClient

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse as Response

pytestmark = pytest.mark.django_db

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
S01 = (REPO / "samples" / "S01-RE-2026-0412.xml").read_bytes()

# Any id works: permissions are checked before the object is looked up.
SOME_ID = UUID("01960000-0000-7000-8000-000000000001")

ALL_ROLES = ("admin", "accountant", "approver", "viewer")
ADMIN = frozenset({"admin"})
ADMIN_OR_ACCOUNTANT = frozenset({"admin", "accountant"})
ADMIN_OR_APPROVER = frozenset({"admin", "approver"})
ANY_ROLE = frozenset(ALL_ROLES)

# Every endpoint that needs a session, with the roles the endpoint table allows.
SESSION_ENDPOINTS: list[tuple[str, str, frozenset[str]]] = [
    ("post", "/api/v1/auth/logout", ANY_ROLE),
    ("get", "/api/v1/auth/me", ANY_ROLE),
    ("get", "/api/v1/documents", ANY_ROLE),
    ("post", "/api/v1/documents", ADMIN_OR_ACCOUNTANT),
    ("get", f"/api/v1/documents/{SOME_ID}", ANY_ROLE),
    ("delete", f"/api/v1/documents/{SOME_ID}", ADMIN),
    ("get", f"/api/v1/documents/{SOME_ID}/file", ANY_ROLE),
    ("get", f"/api/v1/documents/{SOME_ID}/xml", ANY_ROLE),
    ("get", f"/api/v1/documents/{SOME_ID}/text", ANY_ROLE),
    ("get", f"/api/v1/documents/{SOME_ID}/visualization", ANY_ROLE),
    ("get", "/api/v1/suppliers", ANY_ROLE),
    ("get", f"/api/v1/suppliers/{SOME_ID}", ANY_ROLE),
    ("get", "/api/v1/organization", ANY_ROLE),
    ("patch", "/api/v1/organization", ADMIN),
    ("get", "/api/v1/members", ADMIN),
    ("post", "/api/v1/members", ADMIN),
    ("patch", f"/api/v1/members/{SOME_ID}", ADMIN),
    ("get", "/api/v1/stats", ANY_ROLE),
    ("get", "/api/v1/rules/BR-DE-15", ANY_ROLE),
    ("patch", f"/api/v1/documents/{SOME_ID}/invoice", ADMIN_OR_ACCOUNTANT),
    ("post", f"/api/v1/checks/{SOME_ID}/resolve", ADMIN_OR_ACCOUNTANT),
    ("post", f"/api/v1/documents/{SOME_ID}/mark-reviewed", ADMIN_OR_ACCOUNTANT),
    ("post", f"/api/v1/documents/{SOME_ID}/decision", ADMIN_OR_APPROVER),
    ("post", f"/api/v1/documents/{SOME_ID}/send-back", ADMIN_OR_ACCOUNTANT),
    ("post", f"/api/v1/documents/{SOME_ID}/reopen", ADMIN_OR_ACCOUNTANT),
    ("post", f"/api/v1/documents/{SOME_ID}/retry", ADMIN_OR_ACCOUNTANT),
    ("get", "/api/v1/exports", ANY_ROLE),
    ("post", "/api/v1/exports", ADMIN_OR_ACCOUNTANT),
    ("get", f"/api/v1/exports/{SOME_ID}/download", ANY_ROLE),
]


def _endpoint_id(method: str, path: str) -> str:
    return f"{method.upper()} {path.replace(str(SOME_ID), '{id}')}"


FORBIDDEN_CASES = [
    pytest.param(method, path, role, id=f"{_endpoint_id(method, path)} as {role}")
    for method, path, allowed in SESSION_ENDPOINTS
    for role in ALL_ROLES
    if role not in allowed
]
ALLOWED_CASES = [
    pytest.param(method, path, role, id=f"{_endpoint_id(method, path)} as {role}")
    for method, path, allowed in SESSION_ENDPOINTS
    for role in ALL_ROLES
    if role in allowed
]
ENDPOINT_CASES = [
    pytest.param(method, path, id=_endpoint_id(method, path))
    for method, path, _allowed in SESSION_ENDPOINTS
]


def call(api: ApiClient, method: str, path: str) -> "Response":
    """Send the request the way the SPA would: unsafe methods carry the CSRF token."""
    if method == "get":
        return api.get(path)
    if (method, path) == ("post", "/api/v1/documents"):
        # Uploads are multipart. DRF's CSRF check parses the body before the role check,
        # so a JSON body here would answer 415 UNSUPPORTED_MEDIA_TYPE first.
        return api.unsafe(method, path, data={}, content_type=MULTIPART_CONTENT)
    return api.unsafe(method, path, data={})


def assert_problem(response: "Response", status: int, code: str) -> dict[str, object]:
    assert response.status_code == status
    assert response["Content-Type"] == PROBLEM_CONTENT_TYPE
    body: dict[str, object] = response.json()
    assert body["code"] == code
    return body


# --- NOT_AUTHENTICATED ------------------------------------------------------------------


@pytest.mark.parametrize(("method", "path"), ENDPOINT_CASES)
def test_NOT_AUTHENTICATED_endpoint(api: ApiClient, method: str, path: str) -> None:
    response = call(api, method, path)
    assert_problem(response, 401, "NOT_AUTHENTICATED")
    assert response["WWW-Authenticate"] == "Session"


# --- FORBIDDEN_ROLE ---------------------------------------------------------------------


def test_matrix_has_forbidden_cases_for_every_restricted_endpoint() -> None:
    restricted = {(m, p) for m, p, allowed in SESSION_ENDPOINTS if allowed != ANY_ROLE}
    covered = {(case.values[0], case.values[1]) for case in FORBIDDEN_CASES}
    assert covered == restricted


@pytest.mark.parametrize(("method", "path", "role"), FORBIDDEN_CASES)
def test_FORBIDDEN_ROLE_endpoint(
    signed_in: Callable[[str], ApiClient], method: str, path: str, role: str
) -> None:
    assert_problem(call(signed_in(role), method, path), 403, "FORBIDDEN_ROLE")


@pytest.mark.parametrize(("method", "path", "role"), ALLOWED_CASES)
def test_allowed_role_is_not_FORBIDDEN_ROLE(
    signed_in: Callable[[str], ApiClient], method: str, path: str, role: str
) -> None:
    response = call(signed_in(role), method, path)
    assert response.status_code != 401
    if response.status_code == 403:
        assert response.json()["code"] != "FORBIDDEN_ROLE"


# --- METHOD_NOT_ALLOWED -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        pytest.param("put", "/api/v1/documents", id="PUT /api/v1/documents"),
        pytest.param("delete", "/api/v1/auth/me", id="DELETE /api/v1/auth/me"),
    ],
)
def test_METHOD_NOT_ALLOWED_signed_in(
    signed_in: Callable[[str], ApiClient], method: str, path: str
) -> None:
    # Signed in, because DRF checks authentication and permissions before the method.
    assert_problem(call(signed_in("admin"), method, path), 405, "METHOD_NOT_ALLOWED")


def test_METHOD_NOT_ALLOWED_get_sandbox(api: ApiClient) -> None:
    assert_problem(api.get("/api/v1/sandbox"), 405, "METHOD_NOT_ALLOWED")


# --- RATE_LIMITED -----------------------------------------------------------------------


def exhaust_general_limit(client: Client) -> "Response":
    """121 requests from one IP; returns the last one."""
    for _ in range(120):
        assert client.get("/healthz").status_code == 200
    response: Response = client.get("/healthz")
    return response


def test_RATE_LIMITED_general_120_per_minute(client: Client) -> None:
    response = exhaust_general_limit(client)
    assert_problem(response, 429, "RATE_LIMITED")
    assert int(response["Retry-After"]) > 0


@pytest.fixture
def _temporary_storage(tmp_path: Path) -> Iterator[None]:
    documents = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": str(tmp_path), "allow_overwrite": True},
    }
    with override_settings(STORAGES={**storages.backends, "documents": documents}):
        yield


@pytest.mark.usefixtures("_temporary_storage")
def test_RATE_LIMITED_uploads_30_per_minute_per_user(
    signed_in: Callable[[str], ApiClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(temporal_client, "start_processing", lambda document_id: None)
    api = signed_in("accountant")

    def upload() -> "Response":
        return api.unsafe(
            "post",
            "/api/v1/documents",
            data={"files": [SimpleUploadedFile("rechnung.xml", S01)]},
            content_type=MULTIPART_CONTENT,
        )

    # Duplicates still count against the limit.
    for _ in range(30):
        assert upload().status_code == 201
    response = upload()
    assert_problem(response, 429, "RATE_LIMITED")
    assert int(response["Retry-After"]) > 0


# --- Problem shape ----------------------------------------------------------------------

PROBLEM_KEYS = {"type", "title", "status", "detail", "code", "instance"}


def assert_problem_shape(response: "Response", code: str) -> None:
    body = assert_problem(response, response.status_code, code)
    expected = PROBLEM_KEYS | {"errors"} if code == "VALIDATION_FAILED" else PROBLEM_KEYS
    assert set(body) == expected
    assert body["type"] == f"{ERRORS_DOC_URL}#{code.lower()}"
    assert str(body["type"]).endswith(f"#{code.lower()}")
    assert body["status"] == response.status_code
    assert body["instance"] == response["x-request-id"]
    assert isinstance(body["title"], str)
    assert body["title"]
    assert isinstance(body["detail"], str)
    assert body["detail"]


def test_every_error_body_has_the_problem_shape(
    api: ApiClient, signed_in: Callable[[str], ApiClient], client: Client
) -> None:
    assert_problem_shape(api.get("/api/v1/auth/me"), "NOT_AUTHENTICATED")
    assert_problem_shape(api.get("/api/v1/sandbox"), "METHOD_NOT_ALLOWED")

    viewer = signed_in("viewer")
    assert_problem_shape(call(viewer, "post", "/api/v1/documents"), "FORBIDDEN_ROLE")
    viewer.logout()

    admin = signed_in("admin")
    assert_problem_shape(admin.unsafe("post", "/api/v1/members", data={}), "VALIDATION_FAILED")

    cache.clear()  # start the per-IP count from zero
    assert_problem_shape(exhaust_general_limit(client), "RATE_LIMITED")


# --- docs/ERRORS.md ---------------------------------------------------------------------

# The code is the second argument: ProblemError(<status>, "<CODE>", ...).
_CALL_SITE = re.compile(r"(?:ProblemError|problem_response)\(\s*[^,()]+,\s*\"([A-Z_]{4,})\"")
_QUOTED_CODE = re.compile(r"\"([A-Z_]{4,})\"")


def codes_used_by_the_api() -> set[str]:
    codes: set[str] = set()
    for source in (BACKEND / "src").rglob("*.py"):
        codes |= set(_CALL_SITE.findall(source.read_text(encoding="utf-8")))
    problem_module = (BACKEND / "src" / "eingang" / "problem.py").read_text(encoding="utf-8")
    codes |= set(_QUOTED_CODE.findall(problem_module))
    return codes


def test_docs_errors_md_lists_every_code_the_api_uses() -> None:
    documented = set(
        re.findall(
            r"^### ([A-Z_]+)\s*$",
            (REPO / "docs" / "ERRORS.md").read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )
    used = codes_used_by_the_api()
    # Guard against a regex that silently stops matching.
    assert {"NOT_AUTHENTICATED", "FORBIDDEN_ROLE", "UNSUPPORTED_FILE", "SANDBOX_LIMIT"} <= used
    assert used - documented == set()


def test_order_anonymous_wrong_method_is_NOT_AUTHENTICATED_first(api: ApiClient) -> None:
    # Sign-in is checked before the method (docs/DECISIONS.md, "Order of checks").
    response = api.unsafe("put", "/api/v1/documents")
    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"


def test_order_json_upload_is_UNSUPPORTED_MEDIA_TYPE_before_the_role_check(
    signed_in: Callable[[str], ApiClient],
) -> None:
    # The CSRF check parses the body first; the SPA always sends multipart.
    response = signed_in("viewer").unsafe("post", "/api/v1/documents", data={})
    assert response.status_code == 415
    assert response.json()["code"] == "UNSUPPORTED_MEDIA_TYPE"

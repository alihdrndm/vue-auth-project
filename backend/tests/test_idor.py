"""No endpoint reads or changes another organisation's objects (HANDOFF "Permissions").

Every object endpoint is called by an admin of organisation A with the id of an object of
organisation B. The answer must be 404 NOT_FOUND (never revealing that the object exists),
and the object must be unchanged.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from django.core.files.storage import storages
from django.test import override_settings

from accounts.models import Organization, User
from eingang import storage
from invoices.models import Document
from tests.conftest import PASSWORD, ApiClient
from tests.factories import add_iban, make_document, make_invoice, make_supplier

pytestmark = pytest.mark.django_db


@dataclass(frozen=True)
class Victim:
    document: Document
    supplier_id: str
    member: User


@pytest.fixture(autouse=True)
def _temporary_storage(tmp_path: Path) -> Iterator[None]:
    documents = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": str(tmp_path), "allow_overwrite": True},
    }
    with override_settings(STORAGES={**storages.backends, "documents": documents}):
        yield


@pytest.fixture
def victim(other_organization: Organization) -> Victim:
    """Organisation B's objects, with every derived file present, so only scoping can stop A."""
    document = make_document(other_organization)
    supplier = make_supplier(other_organization)
    invoice = make_invoice(document, supplier=supplier, iban="DE89370400440532013000")
    add_iban(supplier, "DE89370400440532013000", invoice)
    storage.write(document.storage_key, b"<Invoice/>")
    for name in ("invoice.xml", "text.txt", "visualization.html"):
        storage.write(storage.derived_key(other_organization.id, document.id, name), b"x")
    member = User.objects.create_user(
        "b-member@example.invalid", PASSWORD, organization=other_organization, role="viewer"
    )
    return Victim(document=document, supplier_id=str(supplier.id), member=member)


ObjectCall = Callable[[ApiClient, Victim], object]

OBJECT_ENDPOINTS: dict[str, ObjectCall] = {
    "GET documents/{id}": lambda api, v: api.get(f"/api/v1/documents/{v.document.id}"),
    "DELETE documents/{id}": lambda api, v: api.unsafe(
        "delete", f"/api/v1/documents/{v.document.id}"
    ),
    "GET documents/{id}/file": lambda api, v: api.get(f"/api/v1/documents/{v.document.id}/file"),
    "GET documents/{id}/xml": lambda api, v: api.get(f"/api/v1/documents/{v.document.id}/xml"),
    "GET documents/{id}/text": lambda api, v: api.get(f"/api/v1/documents/{v.document.id}/text"),
    "GET documents/{id}/visualization": lambda api, v: api.get(
        f"/api/v1/documents/{v.document.id}/visualization"
    ),
    "GET suppliers/{id}": lambda api, v: api.get(f"/api/v1/suppliers/{v.supplier_id}"),
    "PATCH members/{id}": lambda api, v: api.unsafe(
        "patch", f"/api/v1/members/{v.member.id}", data={"role": "admin", "is_active": False}
    ),
}


@pytest.mark.parametrize("endpoint", list(OBJECT_ENDPOINTS))
def test_IDOR_object_of_another_organization_is_not_found(
    endpoint: str, signed_in: Callable[[str], ApiClient], victim: Victim
) -> None:
    response = OBJECT_ENDPOINTS[endpoint](signed_in("admin"), victim)
    assert response.status_code == 404, endpoint  # type: ignore[attr-defined]  # test response
    assert response.json()["code"] == "NOT_FOUND"  # type: ignore[attr-defined]  # test response
    victim.document.refresh_from_db()
    victim.member.refresh_from_db()
    assert victim.document.deleted_at is None
    assert (victim.member.role, victim.member.is_active) == ("viewer", True)


def test_IDOR_lists_never_show_another_organizations_objects(
    signed_in: Callable[[str], ApiClient], victim: Victim
) -> None:
    api = signed_in("admin")
    assert api.get("/api/v1/documents").json()["count"] == 0
    assert api.get("/api/v1/suppliers").json()["count"] == 0
    emails = [member["email"] for member in api.get("/api/v1/members").json()["results"]]
    assert victim.member.email not in emails
    filtered = api.get("/api/v1/documents", {"supplier": victim.supplier_id})
    assert filtered.json()["count"] == 0


def test_IDOR_organization_endpoint_is_always_the_users_own(
    signed_in: Callable[[str], ApiClient], organization: Organization, victim: Victim
) -> None:
    api = signed_in("admin")
    assert api.get("/api/v1/organization").json()["id"] == str(organization.id)
    api.unsafe("patch", "/api/v1/organization", data={"name": "Changed"})
    victim.document.organization.refresh_from_db()
    assert victim.document.organization.name == "Andere GmbH"


def test_IDOR_every_object_route_is_covered() -> None:
    """A new object endpoint must be added to OBJECT_ENDPOINTS above."""
    from django.urls import get_resolver

    object_routes = set()
    for pattern in get_resolver().url_patterns:
        for inner in getattr(pattern, "url_patterns", []):
            route = str(inner.pattern)
            if "<uuid:" in route:
                object_routes.add(route)
    assert object_routes == {
        "documents/<uuid:document_id>",
        "documents/<uuid:document_id>/file",
        "documents/<uuid:document_id>/xml",
        "documents/<uuid:document_id>/text",
        "documents/<uuid:document_id>/visualization",
        "suppliers/<uuid:supplier_id>",
        "members/<uuid:member_id>",
    }

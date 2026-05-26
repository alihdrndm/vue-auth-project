from collections.abc import Callable

import pytest

from accounts.models import Organization
from invoices.models import Document
from suppliers.models import Supplier
from tests.conftest import ApiClient
from tests.factories import RECEIVED, add_iban, make_document, make_invoice, make_supplier

pytestmark = pytest.mark.django_db

KNOWN = "DE89370400440532013000"
CONFIRMED = "DE02120300000000202051"
NEW = "DE75512108001245126199"


def test_NOT_AUTHENTICATED_supplier_list(api: ApiClient) -> None:
    response = api.get("/api/v1/suppliers")
    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"


def test_list_is_ordered_by_name_for_every_role(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    make_supplier(organization, "Zimmerei Ost")
    supplier = make_supplier(organization, "Elektro Kessler GmbH")
    api = signed_in("viewer")
    response = api.get("/api/v1/suppliers")
    assert response.status_code == 200
    body = response.json()
    assert [row["name"] for row in body["results"]] == ["Elektro Kessler GmbH", "Zimmerei Ost"]
    # vat_id is unset, so it is omitted.
    assert body["results"][0] == {
        "id": str(supplier.id),
        "name": "Elektro Kessler GmbH",
        "invoice_count": 0,
        "first_seen_at": "2026-03-01T08:00:00Z",
        "last_seen_at": "2026-03-01T08:00:00Z",
    }


def test_list_only_shows_the_own_organization(
    signed_in: Callable[[str], ApiClient], other_organization: Organization
) -> None:
    make_supplier(other_organization, "Fremd AG")
    body = signed_in("accountant").get("/api/v1/suppliers").json()
    assert body["count"] == 0


def test_search_q_is_a_case_insensitive_name_substring(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    make_supplier(organization, "Elektro Kessler GmbH")
    make_supplier(organization, "Zimmerei Ost")
    body = signed_in("viewer").get("/api/v1/suppliers?q=KESSLER").json()
    assert [row["name"] for row in body["results"]] == ["Elektro Kessler GmbH"]


def test_pagination_shape(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    for number in range(27):
        make_supplier(organization, f"Lieferant {number:02d}")
    api = signed_in("viewer")
    first = api.get("/api/v1/suppliers").json()
    assert set(first) == {"count", "next", "previous", "results"}
    assert first["count"] == 27
    assert len(first["results"]) == 25
    assert first["previous"] is None
    assert first["next"].endswith("/api/v1/suppliers?page=2")
    second = api.get("/api/v1/suppliers?page=2").json()
    assert [row["name"] for row in second["results"]] == ["Lieferant 25", "Lieferant 26"]
    assert second["next"] is None


def _supplier_with_history(organization: Organization, admin_name: str | None) -> Supplier:
    supplier = make_supplier(organization)
    supplier.vat_id = "DE123456789"
    supplier.save()
    first = make_invoice(
        make_document(organization, received_minutes=1), supplier=supplier, iban=KNOWN
    )
    second = make_invoice(
        make_document(organization, received_minutes=2, status=Document.Status.APPROVED),
        supplier=supplier,
        number="RE-2",
        gross="238.00",
        iban=CONFIRMED,
    )
    third = make_invoice(
        make_document(organization, received_minutes=3), supplier=supplier, iban=NEW
    )
    add_iban(supplier, KNOWN, first)
    confirmed = add_iban(supplier, CONFIRMED, second)
    confirmed.confirmed_at = RECEIVED
    confirmed.confirmation_note = "Called the supplier."
    if admin_name is not None:
        confirmed.confirmed_by = organization.users.get(name=admin_name)
    confirmed.save()
    add_iban(supplier, NEW, third)
    return supplier


def test_detail_reports_iban_statuses(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    api = signed_in("admin")
    supplier = _supplier_with_history(organization, "Admin")
    response = api.get(f"/api/v1/suppliers/{supplier.id}")
    assert response.status_code == 200
    ibans = {entry["iban"]: entry for entry in response.json()["ibans"]}
    assert ibans[KNOWN]["status"] == "known"
    assert ibans[KNOWN]["trusted"] is True
    assert "confirmed_at" not in ibans[KNOWN]
    assert "confirmed_by_name" not in ibans[KNOWN]
    assert ibans[CONFIRMED]["status"] == "confirmed"
    assert ibans[CONFIRMED]["trusted"] is True
    assert ibans[CONFIRMED]["confirmed_by_name"] == "Admin"
    assert ibans[CONFIRMED]["confirmed_at"] == "2026-03-01T08:00:00Z"
    assert ibans[CONFIRMED]["confirmation_note"] == "Called the supplier."
    assert ibans[NEW]["status"] == "new"
    assert ibans[NEW]["trusted"] is False


def test_detail_lists_invoices_newest_first_without_deleted_ones(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    api = signed_in("viewer")
    supplier = _supplier_with_history(organization, None)
    deleted = make_document(organization, received_minutes=4)
    make_invoice(deleted, supplier=supplier)
    deleted.deleted_at = RECEIVED
    deleted.save()
    body = api.get(f"/api/v1/suppliers/{supplier.id}").json()
    assert body["vat_id"] == "DE123456789"
    assert len(body["invoices"]) == 3
    received = [invoice["received_at"] for invoice in body["invoices"]]
    assert received == sorted(received, reverse=True)
    second = body["invoices"][1]
    assert second["invoice_number"] == "RE-2"
    assert second["gross_total"] == "238.00"
    assert second["currency"] == "EUR"
    assert second["status"] == "approved"
    assert second["issue_date"] == "2026-03-01"
    assert set(second) == {
        "document_id",
        "invoice_number",
        "issue_date",
        "gross_total",
        "currency",
        "status",
        "received_at",
    }


def test_NOT_FOUND_supplier_of_another_organization(
    signed_in: Callable[[str], ApiClient], other_organization: Organization
) -> None:
    supplier = make_supplier(other_organization, "Fremd AG")
    response = signed_in("admin").get(f"/api/v1/suppliers/{supplier.id}")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_NOT_AUTHENTICATED_supplier_detail(api: ApiClient, organization: Organization) -> None:
    supplier = make_supplier(organization)
    response = api.get(f"/api/v1/suppliers/{supplier.id}")
    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"

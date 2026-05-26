from collections.abc import Callable

import pytest

from accounts.models import Organization
from invoices.models import Document
from tests.conftest import ApiClient
from tests.factories import (
    RECEIVED,
    add_check,
    add_iban,
    make_document,
    make_invoice,
    make_supplier,
)

pytestmark = pytest.mark.django_db


def ids(response: object) -> list[str]:
    return [item["id"] for item in response.json()["results"]]  # type: ignore[attr-defined]  # test response


def test_list_returns_paginated_summaries_newest_first(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    older = make_document(organization, received_minutes=1)
    newer = make_document(organization, received_minutes=2)
    response = signed_in("viewer").get("/api/v1/documents")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"count", "next", "previous", "results"}
    assert body["count"] == 2
    assert ids(response) == [str(newer.id), str(older.id)]


def test_summary_fields_from_invoice_checks_and_supplier(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    supplier = make_supplier(organization)
    first = make_invoice(make_document(organization, received_minutes=1), supplier=supplier)
    add_iban(supplier, "DE89370400440532013000", first)
    document = make_document(organization, received_minutes=2)
    make_invoice(document, number="RE-7", supplier=supplier, iban="DE02120300000000202051")
    add_check(document, "C05", "block")
    add_check(document, "C07", "warn")
    response = signed_in("accountant").get("/api/v1/documents?ordering=received_at")
    summary = response.json()["results"][1]
    assert summary["invoice_number"] == "RE-7"
    assert summary["supplier_name"] == "Elektro Kessler GmbH"
    assert summary["gross_total"] == "1190.00"  # money is a string
    assert summary["open_block_checks"] == 1
    assert summary["open_warn_checks"] == 1
    assert summary["payee_iban_last4"] == "2051"
    assert summary["iban_status"] == "new"
    assert summary["is_einvoice"] is True
    mark = {item["action"]: item for item in summary["allowed_actions"]}["mark_reviewed"]
    assert mark == {
        "action": "mark_reviewed",
        "enabled": False,
        "reason_code": "BLOCKING_CHECKS",
        "reason": "Resolve 1 blocking check first.",
    }
    assert (
        "reason" not in {item["action"]: item for item in summary["allowed_actions"]}["edit_fields"]
    )


def test_summary_without_invoice_omits_invoice_fields(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    make_document(organization, status=Document.Status.RECEIVED)
    (summary,) = signed_in("viewer").get("/api/v1/documents").json()["results"]
    assert "invoice_number" not in summary
    assert "gross_total" not in summary
    assert summary["allowed_actions"] == []


def test_filters(signed_in: Callable[[str], ApiClient], organization: Organization) -> None:
    supplier = make_supplier(organization, "Bürobedarf Nord KG")
    review = make_document(organization, status=Document.Status.NEEDS_REVIEW)
    make_invoice(review, number="BN-88213", supplier=supplier)
    approval = make_document(
        organization, status=Document.Status.AWAITING_APPROVAL, kind=Document.Kind.PDF_TEXT,
        format_label="Plain PDF",
    )  # fmt: skip
    plain = make_invoice(approval, number="2026-1043")
    plain.is_einvoice = False
    plain.save()
    api = signed_in("viewer")
    assert ids(api.get("/api/v1/documents", {"status": "awaiting_approval"})) == [str(approval.id)]
    assert ids(api.get("/api/v1/documents", {"q": "88213"})) == [str(review.id)]
    assert ids(api.get("/api/v1/documents", {"q": "bürobedarf"})) == [str(review.id)]
    assert ids(api.get("/api/v1/documents", {"supplier": str(supplier.id)})) == [str(review.id)]
    assert ids(api.get("/api/v1/documents", {"kind": "pdf_text"})) == [str(approval.id)]
    assert ids(api.get("/api/v1/documents", {"format": "Plain PDF"})) == [str(approval.id)]
    assert ids(api.get("/api/v1/documents", {"einvoice": "false"})) == [str(approval.id)]
    assert ids(api.get("/api/v1/documents", {"einvoice": "true"})) == [str(review.id)]


def test_ordering_by_gross_and_due_date(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    small = make_document(organization)
    make_invoice(small, gross="10.00").__class__.objects.filter(document=small).update(
        due_date=RECEIVED.date().replace(day=20)
    )
    large = make_document(organization)
    make_invoice(large, gross="900.00").__class__.objects.filter(document=large).update(
        due_date=RECEIVED.date().replace(day=10)
    )
    without = make_document(organization, status=Document.Status.RECEIVED)
    api = signed_in("viewer")
    assert ids(api.get("/api/v1/documents", {"ordering": "-gross_total"})) == [
        str(large.id), str(small.id), str(without.id)
    ]  # fmt: skip
    assert ids(api.get("/api/v1/documents", {"ordering": "due_date"})) == [
        str(large.id), str(small.id), str(without.id)
    ]  # fmt: skip


def test_deleted_documents_are_not_listed(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    document = make_document(organization)
    Document.objects.filter(id=document.id).update(deleted_at=RECEIVED)
    assert signed_in("viewer").get("/api/v1/documents").json()["count"] == 0


def test_other_organisations_documents_are_never_listed(
    signed_in: Callable[[str], ApiClient], other_organization: Organization
) -> None:
    make_document(other_organization)
    assert signed_in("admin").get("/api/v1/documents").json()["count"] == 0


@pytest.mark.parametrize(
    "query", ["status=lost", "ordering=name", "einvoice=maybe", "supplier=not-a-uuid", "page=0"]
)
def test_VALIDATION_FAILED_bad_list_parameters(
    query: str, signed_in: Callable[[str], ApiClient]
) -> None:
    response = signed_in("viewer").get(f"/api/v1/documents?{query}")
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_FAILED"


def test_NOT_AUTHENTICATED_list(api: ApiClient) -> None:
    assert api.get("/api/v1/documents").status_code == 401

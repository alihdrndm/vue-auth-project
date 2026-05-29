from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.files.storage import storages
from django.test import override_settings

from accounts.models import Organization
from eingang import storage
from invoices.models import (
    Approval,
    Document,
    Event,
    InvoiceLine,
    RuleExplanation,
    ValidationReport,
)
from tests.conftest import ApiClient, MakeUser
from tests.factories import add_check, make_document, make_invoice

pytestmark = pytest.mark.django_db
DECIDED = datetime(2026, 3, 2, 10, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _temporary_storage(tmp_path: Path) -> Iterator[None]:
    documents = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": str(tmp_path), "allow_overwrite": True},
    }
    with override_settings(STORAGES={**storages.backends, "documents": documents}):
        yield


def url(document: Document, suffix: str = "") -> str:
    return f"/api/v1/documents/{document.id}{suffix}"


def test_detail_has_invoice_lines_validation_checks_approvals_and_events(
    signed_in: Callable[[str], ApiClient], organization: Organization, make_user: MakeUser
) -> None:
    api = signed_in("accountant")
    approver = make_user("approver")
    document = make_document(organization)
    invoice = make_invoice(document, number="RE-1")
    InvoiceLine.objects.create(
        invoice=invoice, position=1, description="Kabel", net_amount=Decimal("10")
    )
    ValidationReport.objects.create(
        document=document, status="invalid", engine="test", xsd_ok=True,
        issues=[{"rule_id": "BR-DE-15", "severity": "fatal", "message": "m", "location": "/",
                 "test": "t", "source": "xrechnung"}],
        fatal_count=1, warning_count=0, ran_at=DECIDED,
    )  # fmt: skip
    RuleExplanation.objects.create(
        rule_id="BR-DE-15", plain_text="The buyer reference is missing.", fix_hint="Ask for it.",
        source="curated",
    )  # fmt: skip
    add_check(document, "C15", "block")
    Approval.objects.create(document=document, decision="rejected", decided_by=approver,
                            comment="Wrong cost centre", decided_at=DECIDED)  # fmt: skip
    Event.objects.create(
        organization=organization, document=document, type="document.received", data={}
    )
    Event.objects.create(
        organization=organization, document=document, type="processing.started", data={}
    )
    body = api.get(url(document)).json()
    assert body["invoice"]["invoice_number"] == "RE-1"
    assert body["invoice"]["gross_total"] == "1190.00"
    assert "seller_vat_id" not in body["invoice"]  # unset fields are omitted
    assert body["lines"][0]["description"] == "Kabel"
    issue = body["validation"]["issues"][0]
    assert issue["explanation"] == {
        "plain_text": "The buyer reference is missing.",
        "fix_hint": "Ask for it.",
    }
    (check,) = body["checks"]
    # C15 ("accept anyway") may only be resolved by an admin.
    assert check["resolve"] == {
        "enabled": False,
        "reason_code": "FORBIDDEN_ROLE",
        "reason": "Your role (accountant) can't do this.",
    }
    assert body["approvals"][0]["decided_by_name"] == "Approver"
    assert [event["type"] for event in body["events"]] == [
        "processing.started",
        "document.received",
    ]
    assert body["text_truncated"] is False
    assert {entry["action"] for entry in body["allowed_actions"]} >= {"edit_fields"}


def test_resolve_state_of_checks(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    api = signed_in("admin")
    document = make_document(organization)
    add_check(document, "C05", "block")
    add_check(document, "C04", "info")
    resolved = add_check(document, "C07", "warn")
    resolved.resolved_at = DECIDED
    resolved.save()
    states = {
        check["check_id"]: check["resolve"] for check in api.get(url(document)).json()["checks"]
    }
    assert states["C05"] == {"enabled": True}
    assert states["C04"]["reason_code"] == "CHECK_NOT_RESOLVABLE"
    assert states["C07"] == {
        "enabled": False, "reason_code": "CHECK_NOT_RESOLVABLE", "reason": "Already resolved."
    }  # fmt: skip
    document.status = Document.Status.AWAITING_APPROVAL
    document.save()
    states = {
        check["check_id"]: check["resolve"] for check in api.get(url(document)).json()["checks"]
    }
    assert states["C05"]["reason_code"] == "INVALID_TRANSITION"


def test_file_is_an_attachment_that_never_renders_as_a_page(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    document = make_document(organization)
    storage.write(document.storage_key, b"<Invoice/>")
    response = signed_in("viewer").get(url(document, "/file"))
    assert response.status_code == 200
    assert response.content == b"<Invoice/>"
    assert response["Content-Disposition"].startswith("attachment;")
    assert response["Content-Security-Policy"] == "sandbox; default-src 'none'"


@pytest.mark.parametrize(
    ("suffix", "name", "content_type"),
    [
        ("/xml", "invoice.xml", "application/xml"),
        ("/text", "text.txt", "text/plain; charset=utf-8"),
    ],
)
def test_xml_and_text_send_the_same_two_headers(
    suffix: str,
    name: str,
    content_type: str,
    signed_in: Callable[[str], ApiClient],
    organization: Organization,
) -> None:
    document = make_document(organization)
    storage.write(storage.derived_key(organization.id, document.id, name), b"content")  # type: ignore[arg-type]  # test values
    response = signed_in("viewer").get(url(document, suffix))
    assert response.content == b"content"
    assert response["Content-Type"] == content_type
    assert response["Content-Disposition"].startswith("attachment;")
    assert response["Content-Security-Policy"] == "sandbox; default-src 'none'"


def test_visualization_is_frameable_by_the_app_only(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    document = make_document(organization)
    key = storage.derived_key(organization.id, document.id, "visualization.html")
    storage.write(key, b"<html></html>")
    response = signed_in("viewer").get(url(document, "/visualization"))
    assert response["Content-Security-Policy"] == (
        "default-src 'none'; style-src 'unsafe-inline'; img-src data:"
    )
    assert response["X-Frame-Options"] == "SAMEORIGIN"


@pytest.mark.parametrize("suffix", ["/xml", "/text", "/visualization"])
def test_NOT_AVAILABLE_when_the_worker_stored_nothing(
    suffix: str, signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    response = signed_in("viewer").get(url(make_document(organization), suffix))
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_AVAILABLE"


def test_delete_hides_the_document_and_records_an_event(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    api = signed_in("admin")
    document = make_document(organization)
    assert api.unsafe("delete", url(document)).status_code == 204
    document.refresh_from_db()
    assert document.deleted_at is not None
    assert Event.objects.filter(document=document, type="document.deleted").exists()
    assert api.get(url(document)).json()["code"] == "NOT_FOUND"


def test_ALREADY_EXPORTED_cannot_be_deleted(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    document = make_document(organization, status=Document.Status.EXPORTED)
    response = signed_in("admin").unsafe("delete", url(document))
    assert response.status_code == 409
    assert response.json()["code"] == "ALREADY_EXPORTED"


def test_INVALID_TRANSITION_delete_while_processing(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    document = make_document(organization, status=Document.Status.PROCESSING)
    assert signed_in("admin").unsafe("delete", url(document)).json()["code"] == "INVALID_TRANSITION"


@pytest.mark.parametrize("role", ["accountant", "approver", "viewer"])
def test_FORBIDDEN_ROLE_delete(
    role: str, signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    response = signed_in(role).unsafe("delete", url(make_document(organization)))
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN_ROLE"


def test_NOT_FOUND_unknown_document(signed_in: Callable[[str], ApiClient]) -> None:
    response = signed_in("viewer").get("/api/v1/documents/01900000-0000-7000-8000-000000000000")
    assert response.json()["code"] == "NOT_FOUND"

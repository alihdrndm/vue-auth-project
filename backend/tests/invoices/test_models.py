from datetime import UTC, datetime

import pytest
from django.db import IntegrityError, models, transaction

from accounts.models import Organization, User
from exports.models import ExportBatch
from invoices.models import (
    AppendOnlyError,
    Approval,
    Check,
    Document,
    Event,
    Invoice,
    InvoiceLine,
    RuleExplanation,
    ValidationReport,
)
from llm.models import LlmCache, LlmCall
from suppliers.models import Supplier, SupplierIban

RECEIVED_AT = datetime(2026, 3, 10, 9, 30, tzinfo=UTC)
SHA256 = "a" * 64


def make_document(organization: Organization, sha256: str = SHA256) -> Document:
    return Document.objects.create(
        organization=organization,
        source=Document.Source.UPLOAD,
        original_filename="rechnung.xml",
        content_type="application/xml",
        size_bytes=1024,
        sha256=sha256,
        storage_key=f"orgs/{organization.id}/documents/x/{sha256}.xml",
        received_at=RECEIVED_AT,
        kind=Document.Kind.XML,
        format_label="XRechnung · UBL",
    )


@pytest.mark.django_db
def test_event_refuses_update() -> None:
    organization = Organization.objects.create(name="Holzwerk Brandt GmbH", slug="holzwerk")
    event = Event.objects.create(organization=organization, type=Event.Type.DOCUMENT_RECEIVED)
    event.data = {"changed": True}
    with pytest.raises(AppendOnlyError):
        event.save()
    event.refresh_from_db()
    assert event.data == {}


@pytest.mark.django_db
def test_event_refuses_delete() -> None:
    organization = Organization.objects.create(name="Holzwerk Brandt GmbH", slug="holzwerk")
    event = Event.objects.create(organization=organization, type=Event.Type.DOCUMENT_RECEIVED)
    with pytest.raises(AppendOnlyError):
        event.delete()
    assert Event.objects.filter(id=event.id).exists()


@pytest.mark.django_db
def test_document_sha256_is_unique_per_organization_while_not_deleted() -> None:
    organization = Organization.objects.create(name="Holzwerk Brandt GmbH", slug="holzwerk")
    first = make_document(organization)
    with transaction.atomic(), pytest.raises(IntegrityError):
        make_document(organization)

    first.deleted_at = RECEIVED_AT
    first.save()
    second = make_document(organization)

    assert Document.objects.filter(organization=organization, sha256=SHA256).count() == 2
    assert second.status == Document.Status.RECEIVED


@pytest.mark.django_db
def test_same_document_in_two_organizations_is_allowed() -> None:
    make_document(Organization.objects.create(name="A", slug="a"))
    make_document(Organization.objects.create(name="B", slug="b"))
    assert Document.objects.filter(sha256=SHA256).count() == 2


@pytest.mark.parametrize(
    ("model", "table"),
    [
        (Document, "documents"),
        (Invoice, "invoices"),
        (InvoiceLine, "invoice_lines"),
        (ValidationReport, "validation_reports"),
        (RuleExplanation, "rule_explanations"),
        (Check, "checks"),
        (Approval, "approvals"),
        (Event, "events"),
        (Supplier, "suppliers"),
        (SupplierIban, "supplier_ibans"),
        (ExportBatch, "export_batches"),
        (LlmCall, "llm_calls"),
        (LlmCache, "llm_cache"),
        (Organization, "organizations"),
        (User, "users"),
    ],
)
def test_model_uses_the_spec_table_name(model: type[models.Model], table: str) -> None:
    assert model._meta.db_table == table


@pytest.mark.django_db
def test_deleting_an_organization_removes_its_decisions_and_exports() -> None:
    organization = Organization.objects.create(name="Sandbox", slug="sb-del", kind="sandbox")
    user = User.objects.create_user(
        "sb-del@example.invalid", None, organization=organization, role="admin"
    )
    document = make_document(organization)
    Approval.objects.create(
        document=document, decision="approved", decided_by=user, decided_at=RECEIVED_AT
    )
    ExportBatch.objects.create(
        organization=organization,
        created_by=user,
        format="csv_invoices",
        document_ids=[],
        storage_key="k",
        row_count=0,
    )
    organization.delete()
    assert not Document.objects.filter(pk=document.pk).exists()
    assert not User.objects.filter(pk=user.pk).exists()


@pytest.mark.django_db
def test_a_user_with_decisions_cannot_be_deleted_alone(organization: Organization) -> None:
    user = User.objects.create_user(
        "decider@example.invalid", None, organization=organization, role="approver"
    )
    Approval.objects.create(
        document=make_document(organization),
        decision="approved",
        decided_by=user,
        decided_at=RECEIVED_AT,
    )
    with pytest.raises(models.RestrictedError):
        user.delete()

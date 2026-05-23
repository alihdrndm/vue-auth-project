"""Small builders for test data. Every value is fictional."""

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import count

from accounts.models import Organization, User
from invoices.models import Check, Document, Invoice
from suppliers.models import Supplier, SupplierIban

RECEIVED = datetime(2026, 3, 1, 8, 0, tzinfo=UTC)
_sequence = count(1)


def make_document(
    organization: Organization,
    *,
    status: str = Document.Status.NEEDS_REVIEW,
    received_minutes: int | None = None,
    kind: str = Document.Kind.XML,
    format_label: str = "XRechnung · UBL",
    reviewed_by: User | None = None,
) -> Document:
    number = next(_sequence)
    sha256 = hashlib.sha256(f"document-{number}".encode()).hexdigest()
    minutes = number if received_minutes is None else received_minutes
    return Document.objects.create(
        organization=organization,
        source=Document.Source.UPLOAD,
        original_filename=f"rechnung-{number}.xml",
        content_type="application/xml",
        size_bytes=1000 + number,
        sha256=sha256,
        storage_key=f"orgs/{organization.id}/documents/test/{sha256}.xml",
        received_at=RECEIVED + timedelta(minutes=minutes),
        kind=kind,
        format_label=format_label,
        status=status,
        reviewed_by=reviewed_by,
    )


def make_invoice(
    document: Document,
    *,
    number: str | None = None,
    supplier: Supplier | None = None,
    gross: str = "1190.00",
    iban: str | None = None,
) -> Invoice:
    return Invoice.objects.create(
        document=document,
        organization=document.organization,
        extraction_method=Invoice.ExtractionMethod.XML,
        is_einvoice=True,
        invoice_number=number or f"RE-{document.id.hex[:8]}",
        issue_date=RECEIVED.date(),
        currency="EUR",
        seller_name=supplier.name if supplier else "Elektro Kessler GmbH",
        seller_vat_id=supplier.vat_id if supplier else None,
        gross_total=Decimal(gross),
        payee_iban=iban,
        supplier=supplier,
    )


def make_supplier(organization: Organization, name: str = "Elektro Kessler GmbH") -> Supplier:
    return Supplier.objects.create(
        organization=organization,
        name=name,
        normalised_name=name.lower(),
        first_seen_at=RECEIVED,
        last_seen_at=RECEIVED,
    )


def add_iban(supplier: Supplier, iban: str, invoice: Invoice) -> SupplierIban:
    return SupplierIban.objects.create(
        supplier=supplier,
        iban=iban,
        first_seen_invoice=invoice,
        first_seen_at=invoice.document.received_at,
        last_seen_at=invoice.document.received_at,
    )


def add_check(document: Document, check_id: str = "C05", severity: str = "block") -> Check:
    return Check.objects.create(
        document=document,
        check_id=check_id,
        code="BANK_DETAILS_CHANGED",
        severity=severity,
        message="The bank account differs from earlier invoices from this supplier.",
        details={},
    )

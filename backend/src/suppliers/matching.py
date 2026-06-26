"""Finding or creating an invoice's supplier, and its IBAN history (HANDOFF section 10).

`match_supplier` runs on every invoice that has a seller VAT ID or a seller name: after XML
parsing, after LLM extraction, after every edit and in the seed. It is idempotent, so it can
run again on the same invoice at any time.
"""

import re
import unicodedata
from uuid import UUID

from django.db import transaction
from django.db.models import Count, Max, Min

from invoices.models import Invoice
from suppliers.models import Supplier, SupplierIban

LEGAL_FORMS = ("gmbh", "ug", "ag", "kg", "ohg", "gbr", "e.k.", "mbh", "& co.", "ltd", "sarl", "sas")

# A legal form counts only as a whole token: it starts the name or follows whitespace, and it
# ends the name or is followed by whitespace, optionally after trailing punctuation ("Ltd.",
# "GmbH,"). Multi-word forms ("& co.") match across any run of whitespace.
_LEGAL_FORM = re.compile(
    "|".join(
        r"(?<!\S)" + r"\s+".join(re.escape(part) for part in form.split()) + r"(?=[^\w\s]*(?:\s|$))"
        for form in LEGAL_FORMS
    )
)
_PUNCTUATION = re.compile(r"[^\w\s]")


def normalise_name(name: str) -> str:
    """Lower-case; legal forms and punctuation removed; spaces collapsed."""
    lowered = " ".join(name.lower().split())
    without_forms = _LEGAL_FORM.sub(" ", lowered)
    without_punctuation = _PUNCTUATION.sub("", without_forms)
    return " ".join(without_punctuation.split())


def normalise_number(number: str | None) -> str | None:
    """Upper-case with spaces, dashes and slashes removed (also used by check C02)."""
    if number is None:
        return None
    kept = (
        char
        for char in number.upper()
        if not char.isspace() and char != "/" and unicodedata.category(char) != "Pd"
    )
    return "".join(kept) or None


def match_supplier(invoice: Invoice) -> Supplier | None:
    """Find or create the invoice's supplier and record its IBAN.

    Sets `invoice.supplier` and `invoice.normalised_number` and saves them. Returns None,
    and leaves the invoice without a supplier, when it has neither a seller VAT ID nor a
    seller name. When the invoice moves to another supplier, both are recounted.
    """
    with transaction.atomic():
        previous_id: UUID | None = invoice.supplier_id
        supplier = _find_or_create(invoice)
        invoice.supplier = supplier
        invoice.normalised_number = normalise_number(invoice.invoice_number)
        invoice.save(update_fields=["supplier", "normalised_number", "updated_at"])
        if supplier is not None:
            _refresh_counts(supplier)
            _record_iban(supplier, invoice)
        if previous_id is not None and (supplier is None or previous_id != supplier.id):
            previous = Supplier.objects.filter(id=previous_id).first()
            if previous is not None:
                _refresh_counts(previous)
    return supplier


def _present(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return value


def _find_or_create(invoice: Invoice) -> Supplier | None:
    vat_id = _present(invoice.seller_vat_id)
    name = _present(invoice.seller_name)
    if vat_id is None and name is None:
        return None
    received_at = invoice.document.received_at
    normalised = normalise_name(name or "")
    if vat_id is not None:
        supplier, _ = Supplier.objects.get_or_create(
            organization_id=invoice.organization_id,
            vat_id=vat_id,
            defaults={
                "name": name or "",
                "normalised_name": normalised,
                "first_seen_at": received_at,
                "last_seen_at": received_at,
            },
        )
        return supplier
    existing = (
        Supplier.objects.filter(organization_id=invoice.organization_id, normalised_name=normalised)
        .order_by("created_at", "id")
        .first()
    )
    if existing is not None:
        return existing
    return Supplier.objects.create(
        organization_id=invoice.organization_id,
        name=name or "",
        normalised_name=normalised,
        first_seen_at=received_at,
        last_seen_at=received_at,
    )


def _refresh_counts(supplier: Supplier) -> None:
    """Recount the supplier's non-deleted invoices and their first and last receipt."""
    stats = supplier.invoices.filter(document__deleted_at__isnull=True).aggregate(
        count=Count("id"),
        first=Min("document__received_at"),
        last=Max("document__received_at"),
    )
    supplier.invoice_count = stats["count"]
    if stats["first"] is not None:
        supplier.first_seen_at = stats["first"]
    if stats["last"] is not None:
        supplier.last_seen_at = stats["last"]
    supplier.save(update_fields=["invoice_count", "first_seen_at", "last_seen_at", "updated_at"])


def _record_iban(supplier: Supplier, invoice: Invoice) -> None:
    iban = _present(invoice.payee_iban)
    if iban is None:
        return
    received_at = invoice.document.received_at
    entry, created = SupplierIban.objects.get_or_create(
        supplier=supplier,
        iban=iban,
        defaults={
            "first_seen_invoice": invoice,
            "first_seen_at": received_at,
            "last_seen_at": received_at,
        },
    )
    if created:
        return
    fields = []
    if received_at > entry.last_seen_at:
        entry.last_seen_at = received_at
        fields.append("last_seen_at")
    if received_at < entry.first_seen_at:
        # Processed out of order: the earliest received invoice is the first sighting, so
        # trust ("on the supplier's first invoice") never depends on processing order.
        entry.first_seen_invoice = invoice
        entry.first_seen_at = received_at
        fields += ["first_seen_invoice", "first_seen_at"]
    if fields:
        entry.save(update_fields=[*fields, "updated_at"])

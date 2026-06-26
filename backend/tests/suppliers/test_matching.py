from datetime import timedelta

import pytest

from accounts.models import Organization
from invoices.models import Document, Invoice
from suppliers.matching import match_supplier, normalise_name, normalise_number
from suppliers.models import Supplier, SupplierIban
from tests.factories import RECEIVED, make_document

pytestmark = pytest.mark.django_db

IBAN = "DE89370400440532013000"
OTHER_IBAN = "DE02120300000000202051"
VAT_ID = "DE100000016"


def invoice_for(
    organization: Organization,
    *,
    minutes: int,
    name: str | None = "Elektro Kessler GmbH",
    vat_id: str | None = None,
    number: str | None = "RE-2026/0412",
    iban: str | None = None,
) -> Invoice:
    document = make_document(organization, received_minutes=minutes)
    return Invoice.objects.create(
        document=document,
        organization=organization,
        extraction_method=Invoice.ExtractionMethod.XML,
        invoice_number=number,
        seller_name=name,
        seller_vat_id=vat_id,
        payee_iban=iban,
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Elektro Kessler GmbH", "elektro kessler"),
        ("Müller Bau GmbH & Co. KG", "müller bau"),
        ("Müller  Bau   GmbH  &  Co.  KG", "müller bau"),
        ("Atelier Moreau SARL", "atelier moreau"),
        ("Bürobedarf Nord KG", "bürobedarf nord"),
        ("Hausmeisterservice Pohl e.K.", "hausmeisterservice pohl"),
        ("Acme Ltd.", "acme"),
        ("Kessler, GmbH", "kessler"),
        ("Sommer UG (haftungsbeschränkt)", "sommer haftungsbeschränkt"),
        ("Lagerhaus AG", "lagerhaus"),
        ("Brandt OHG", "brandt"),
        ("Brandt GbR", "brandt"),
        ("Brandt mbH", "brandt"),
        ("Moreau SAS", "moreau"),
        # Legal forms only count as whole tokens.
        ("Agrarhandel Kugler", "agrarhandel kugler"),
        ("AG-Bau Service", "agbau service"),
        ("Ludwig's Werkstatt", "ludwigs werkstatt"),
    ],
)
def test_normalise_name(name: str, expected: str) -> None:
    assert normalise_name(name) == expected


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        ("re-2026/0412", "RE20260412"),
        ("RE 2026 0412", "RE20260412"),
        ("SA/26/1160", "SA261160"),
        ("RE\u20132026\u20130412", "RE20260412"),  # en dashes
        ("2026-1043", "20261043"),
        (" - / ", None),
        (None, None),
    ],
)
def test_normalise_number(number: str | None, expected: str | None) -> None:
    assert normalise_number(number) == expected


def test_creates_a_supplier_by_name_and_sets_the_invoice_fields(
    organization: Organization,
) -> None:
    invoice = invoice_for(organization, minutes=5, iban=IBAN)
    supplier = match_supplier(invoice)
    assert supplier is not None
    invoice.refresh_from_db()
    assert invoice.supplier_id == supplier.id
    assert invoice.normalised_number == "RE20260412"
    assert supplier.name == "Elektro Kessler GmbH"
    assert supplier.normalised_name == "elektro kessler"
    assert supplier.vat_id is None
    assert supplier.invoice_count == 1
    assert supplier.first_seen_at == RECEIVED + timedelta(minutes=5)
    assert supplier.last_seen_at == RECEIVED + timedelta(minutes=5)
    entry = SupplierIban.objects.get(supplier=supplier)
    assert entry.iban == IBAN
    assert entry.first_seen_invoice_id == invoice.id
    assert entry.first_seen_at == RECEIVED + timedelta(minutes=5)


def test_matches_by_normalised_name(organization: Organization) -> None:
    first = match_supplier(invoice_for(organization, minutes=1, name="Elektro Kessler GmbH"))
    second = match_supplier(invoice_for(organization, minutes=2, name="ELEKTRO KESSLER, GmbH."))
    assert first is not None
    assert second == first
    assert Supplier.objects.count() == 1


def test_matches_by_vat_id_before_name(organization: Organization) -> None:
    first = match_supplier(invoice_for(organization, minutes=1, vat_id=VAT_ID))
    renamed = match_supplier(
        invoice_for(organization, minutes=2, name="Kessler Elektrotechnik GmbH", vat_id=VAT_ID)
    )
    other = match_supplier(
        invoice_for(organization, minutes=3, name="Elektro Kessler GmbH", vat_id="DE200000021")
    )
    assert first is not None
    assert first.vat_id == VAT_ID
    assert renamed == first
    assert other is not None
    assert other != first


def test_suppliers_are_per_organisation(
    organization: Organization, other_organization: Organization
) -> None:
    ours = match_supplier(invoice_for(organization, minutes=1, vat_id=VAT_ID))
    theirs = match_supplier(invoice_for(other_organization, minutes=2, vat_id=VAT_ID))
    assert ours is not None
    assert theirs is not None
    assert ours != theirs


def test_no_seller_vat_id_and_no_seller_name_means_no_supplier(
    organization: Organization,
) -> None:
    invoice = invoice_for(organization, minutes=1, name=None, vat_id=None, number="A 1")
    assert match_supplier(invoice) is None
    invoice.refresh_from_db()
    assert invoice.supplier_id is None
    assert invoice.normalised_number == "A1"
    assert not Supplier.objects.exists()


def test_counts_and_dates_cover_every_non_deleted_invoice(organization: Organization) -> None:
    early = invoice_for(organization, minutes=1)
    late = invoice_for(organization, minutes=30)
    middle = invoice_for(organization, minutes=10)
    for invoice in (late, early, middle):
        match_supplier(invoice)
    supplier = Supplier.objects.get()
    assert supplier.invoice_count == 3
    assert supplier.first_seen_at == RECEIVED + timedelta(minutes=1)
    assert supplier.last_seen_at == RECEIVED + timedelta(minutes=30)

    Document.objects.filter(id=late.document_id).update(deleted_at=RECEIVED)
    match_supplier(middle)
    supplier.refresh_from_db()
    assert supplier.invoice_count == 2
    assert supplier.last_seen_at == RECEIVED + timedelta(minutes=10)


def test_running_twice_gives_the_same_state(organization: Organization) -> None:
    invoice = invoice_for(organization, minutes=1, iban=IBAN)
    first = match_supplier(invoice)
    second = match_supplier(invoice)
    assert first == second
    assert second is not None
    second.refresh_from_db()
    assert second.invoice_count == 1
    assert Supplier.objects.count() == 1
    assert SupplierIban.objects.count() == 1


def test_iban_history_keeps_first_seen_and_the_latest_last_seen(
    organization: Organization,
) -> None:
    first = invoice_for(organization, minutes=1, iban=IBAN)
    later = invoice_for(organization, minutes=20, iban=IBAN)
    changed = invoice_for(organization, minutes=40, iban=OTHER_IBAN)
    for invoice in (first, later, changed):
        match_supplier(invoice)
    match_supplier(first)  # re-running an older invoice does not move last_seen_at back
    known = SupplierIban.objects.get(iban=IBAN)
    assert known.first_seen_invoice_id == first.id
    assert known.first_seen_at == RECEIVED + timedelta(minutes=1)
    assert known.last_seen_at == RECEIVED + timedelta(minutes=20)
    new = SupplierIban.objects.get(iban=OTHER_IBAN)
    assert new.first_seen_invoice_id == changed.id
    assert new.first_seen_at == new.last_seen_at == RECEIVED + timedelta(minutes=40)


def test_an_edit_that_changes_the_seller_recounts_both_suppliers(
    organization: Organization,
) -> None:
    kept = invoice_for(organization, minutes=1, name="Elektro Kessler GmbH")
    moved = invoice_for(organization, minutes=2, name="Elektro Kessler GmbH")
    match_supplier(kept)
    old = match_supplier(moved)
    assert old is not None
    old.refresh_from_db()
    assert old.invoice_count == 2

    moved.seller_name = "Druckerei Sommer GmbH"
    moved.save()
    new = match_supplier(moved)
    assert new is not None
    assert new != old
    old.refresh_from_db()
    new.refresh_from_db()
    assert old.invoice_count == 1
    assert new.invoice_count == 1


def test_an_edit_that_removes_the_seller_recounts_the_old_supplier(
    organization: Organization,
) -> None:
    invoice = invoice_for(organization, minutes=1)
    old = match_supplier(invoice)
    assert old is not None
    invoice.seller_name = None
    invoice.save()
    assert match_supplier(invoice) is None
    old.refresh_from_db()
    assert old.invoice_count == 0
    invoice.refresh_from_db()
    assert invoice.supplier_id is None


def test_iban_first_sighting_follows_received_order_not_processing_order(
    organization: Organization,
) -> None:
    from suppliers.matching import match_supplier
    from suppliers.models import SupplierIban
    from tests.factories import make_document, make_invoice

    iban = "DE89370400440532013000"
    later = make_invoice(make_document(organization, received_minutes=20), iban=iban)
    earlier = make_invoice(make_document(organization, received_minutes=10), iban=iban)
    match_supplier(later)  # processed first, although received second
    match_supplier(earlier)
    entry = SupplierIban.objects.get(iban=iban)
    assert entry.first_seen_invoice_id == earlier.id
    assert entry.first_seen_at == earlier.document.received_at

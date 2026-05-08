from datetime import UTC, datetime

import pytest
from django.db import IntegrityError, transaction

from accounts.models import Organization
from suppliers.models import Supplier

SEEN_AT = datetime(2026, 3, 10, 9, 30, tzinfo=UTC)


def make_supplier(organization: Organization, vat_id: str | None) -> Supplier:
    return Supplier.objects.create(
        organization=organization,
        name="Papier & Co. KG",
        normalised_name="papier",
        vat_id=vat_id,
        first_seen_at=SEEN_AT,
        last_seen_at=SEEN_AT,
    )


@pytest.mark.django_db
def test_supplier_vat_id_is_unique_per_organization() -> None:
    organization = Organization.objects.create(name="Holzwerk Brandt GmbH", slug="holzwerk")
    make_supplier(organization, "DE123456789")
    with transaction.atomic(), pytest.raises(IntegrityError):
        make_supplier(organization, "DE123456789")


@pytest.mark.django_db
def test_supplier_vat_id_uniqueness_ignores_nulls() -> None:
    organization = Organization.objects.create(name="Holzwerk Brandt GmbH", slug="holzwerk")
    make_supplier(organization, None)
    make_supplier(organization, None)
    assert Supplier.objects.filter(organization=organization, vat_id__isnull=True).count() == 2

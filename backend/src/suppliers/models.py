"""Suppliers and the bank accounts seen on their invoices (HANDOFF "Database")."""

from typing import ClassVar

from django.db import models
from django.db.models import Q

from accounts.models import Organization, User
from eingang.db import BaseModel


class Supplier(BaseModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="suppliers"
    )
    name = models.CharField(max_length=500)
    normalised_name = models.CharField(max_length=500)
    vat_id = models.CharField(max_length=32, null=True, blank=True)
    invoice_count = models.PositiveIntegerField(default=0)
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()

    class Meta:
        db_table = "suppliers"
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["organization", "vat_id"],
                condition=Q(vat_id__isnull=False),
                name="suppliers_org_vat_id_uniq",
            )
        ]
        indexes: ClassVar = [
            models.Index(fields=["organization", "normalised_name"], name="suppliers_org_name_idx")
        ]

    def __str__(self) -> str:
        return str(self.id)


class SupplierIban(BaseModel):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="ibans")
    iban = models.CharField(max_length=34)
    first_seen_invoice = models.ForeignKey(
        "invoices.Invoice", on_delete=models.CASCADE, related_name="+"
    )
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmation_note = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "supplier_ibans"
        constraints: ClassVar = [
            models.UniqueConstraint(fields=["supplier", "iban"], name="supplier_ibans_iban_uniq")
        ]

    def __str__(self) -> str:
        return str(self.id)

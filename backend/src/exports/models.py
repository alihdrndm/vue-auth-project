"""Export batches of approved invoices (HANDOFF "Database")."""

from django.db import models

from accounts.models import Organization, User
from eingang.db import BaseModel


class ExportBatch(BaseModel):
    class Format(models.TextChoices):
        CSV_INVOICES = "csv_invoices"
        CSV_LINES = "csv_lines"
        ZIP_BUNDLE = "zip_bundle"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="export_batches"
    )
    # RESTRICT: a user with exports cannot be deleted alone, but an organisation can.
    created_by = models.ForeignKey(User, on_delete=models.RESTRICT)
    format = models.CharField(max_length=16, choices=Format.choices)
    document_ids = models.JSONField(default=list)
    storage_key = models.CharField(max_length=500)
    row_count = models.PositiveIntegerField()

    class Meta:
        db_table = "export_batches"

    def __str__(self) -> str:
        return str(self.id)

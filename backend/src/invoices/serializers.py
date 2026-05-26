"""Response shapes for documents (HTTP API: "document summaries")."""

from typing import Any

from django.db.models import Count, Q, QuerySet
from rest_framework import serializers

from accounts.models import User
from eingang.serializers import Serializer
from invoices.actions import allowed_actions
from invoices.models import Check, Document, Invoice
from suppliers.models import SupplierIban
from suppliers.trust import IbanStatus, first_invoice_id, iban_status


class AllowedActionSerializer(Serializer):
    action = serializers.CharField()
    enabled = serializers.BooleanField()
    reason_code = serializers.CharField(required=False)
    reason = serializers.CharField(required=False)


class DocumentSummarySerializer(Serializer):
    id = serializers.UUIDField()
    original_filename = serializers.CharField()
    kind = serializers.CharField(required=False)
    syntax = serializers.CharField(required=False)
    profile = serializers.CharField(required=False)
    format_label = serializers.CharField(required=False)
    type_code = serializers.IntegerField(required=False)
    status = serializers.ChoiceField(choices=Document.Status.choices)
    processing_step = serializers.CharField(required=False)
    received_at = serializers.DateTimeField()
    invoice_number = serializers.CharField(required=False)
    supplier_name = serializers.CharField(required=False)
    gross_total = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)
    currency = serializers.CharField(required=False)
    due_date = serializers.DateField(required=False)
    is_einvoice = serializers.BooleanField(required=False)
    validation_status = serializers.CharField(required=False)
    open_block_checks = serializers.IntegerField()
    open_warn_checks = serializers.IntegerField()
    payee_iban_last4 = serializers.CharField(required=False)
    iban_status = serializers.ChoiceField(choices=["known", "confirmed", "new"], required=False)
    reviewed_by_name = serializers.CharField(required=False)
    allowed_actions = AllowedActionSerializer(many=True)


def with_summary_data(documents: QuerySet[Document]) -> QuerySet[Document]:
    """Everything a summary reads, fetched in the list's own queries."""
    unresolved = Q(checks__resolved_at__isnull=True)
    return documents.select_related(
        "invoice", "invoice__supplier", "validation_report", "reviewed_by", "organization"
    ).annotate(
        open_block_count=Count(
            "checks", filter=unresolved & Q(checks__severity=Check.Severity.BLOCK), distinct=True
        ),
        open_warn_count=Count(
            "checks", filter=unresolved & Q(checks__severity=Check.Severity.WARN), distinct=True
        ),
    )


def _invoice_of(document: Document) -> Invoice | None:
    try:
        return document.invoice
    except Invoice.DoesNotExist:
        return None


def payee_iban_status(invoice: Invoice) -> IbanStatus | None:
    if not invoice.payee_iban:
        return None
    if invoice.supplier is None:
        return "new"
    entry = SupplierIban.objects.filter(supplier=invoice.supplier, iban=invoice.payee_iban).first()
    if entry is None:
        return "new"
    return iban_status(entry, first_invoice_id(invoice.supplier))


def document_summary(document: Document, user: User) -> dict[str, Any]:  # boundary: drf data
    """A document as the list shows it; needs `with_summary_data` on the queryset."""
    invoice = _invoice_of(document)
    blocking: int = getattr(document, "open_block_count", 0)
    summary: dict[str, Any] = {  # boundary: drf data
        "id": document.id,
        "original_filename": document.original_filename,
        "kind": document.kind,
        "format_label": document.format_label,
        "status": document.status,
        "processing_step": document.processing_step or None,
        "received_at": document.received_at,
        "open_block_checks": blocking,
        "open_warn_checks": getattr(document, "open_warn_count", 0),
        "reviewed_by_name": document.reviewed_by.name if document.reviewed_by else None,
        "allowed_actions": [
            action.__dict__ for action in allowed_actions(document, user, blocking)
        ],
    }
    if invoice is not None:
        summary.update(
            {
                "syntax": invoice.syntax,
                "profile": invoice.profile,
                "type_code": invoice.type_code,
                "invoice_number": invoice.invoice_number,
                "supplier_name": invoice.supplier.name if invoice.supplier else invoice.seller_name,
                "gross_total": invoice.gross_total,
                "currency": invoice.currency,
                "due_date": invoice.due_date,
                "is_einvoice": invoice.is_einvoice,
                "payee_iban_last4": invoice.payee_iban[-4:] if invoice.payee_iban else None,
                "iban_status": payee_iban_status(invoice),
            }
        )
    report = getattr(document, "validation_report", None)
    if report is not None:
        summary["validation_status"] = report.status
    data: dict[str, Any] = DocumentSummarySerializer(summary).data  # boundary: drf data
    data["allowed_actions"] = [
        {key: value for key, value in action.items() if value is not None}
        for action in data["allowed_actions"]
    ]
    return data

"""Response shapes for documents (HTTP API: "document summaries")."""

from typing import Any

from django.db.models import Count, Q, QuerySet
from rest_framework import serializers

from accounts.models import User
from eingang.serializers import Serializer
from invoices.actions import allowed_actions, check_resolvable
from invoices.models import Check, Document, Invoice, RuleExplanation
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


class DocumentPageSerializer(Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = DocumentSummarySerializer(many=True)


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
    return data


# --- Detail ------------------------------------------------------------------------

INVOICE_TEXT_FIELDS = (
    "syntax", "profile", "spec_id", "extraction_method", "invoice_number", "currency",
    "buyer_reference", "order_reference", "seller_name", "seller_vat_id", "seller_tax_number",
    "seller_street", "seller_postcode", "seller_city", "seller_country_code", "seller_email",
    "buyer_name", "buyer_vat_id", "buyer_tax_number", "buyer_street", "buyer_postcode",
    "buyer_city", "buyer_country_code", "buyer_email", "payee_iban", "payee_bic", "payment_terms",
)  # fmt: skip
INVOICE_MONEY_FIELDS = (
    "line_total", "allowance_total", "charge_total", "net_total", "tax_total", "gross_total",
    "prepaid_amount", "payable_amount",
)  # fmt: skip


def _money(required: bool = False) -> serializers.DecimalField:
    return serializers.DecimalField(max_digits=18, decimal_places=2, required=required)


class InvoiceDetailSerializer(Serializer):
    is_einvoice = serializers.BooleanField()
    type_code = serializers.IntegerField(required=False)
    issue_date = serializers.DateField(required=False)
    due_date = serializers.DateField(required=False)
    notes = serializers.ListField(child=serializers.CharField())
    tax_breakdown = serializers.ListField(child=serializers.DictField())
    field_confidence = serializers.DictField(child=serializers.CharField())
    field_evidence = serializers.DictField(child=serializers.CharField(allow_null=True))

    def get_fields(self) -> dict[str, serializers.Field[object, object, object, object]]:
        fields = super().get_fields()
        for name in INVOICE_TEXT_FIELDS:
            fields[name] = serializers.CharField(required=False)
        for name in INVOICE_MONEY_FIELDS:
            fields[name] = _money()
        return fields


class LineSerializer(Serializer):
    position = serializers.IntegerField()
    line_id = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4, required=False)
    unit_code = serializers.CharField(required=False)
    unit_price = serializers.DecimalField(max_digits=18, decimal_places=6, required=False)
    net_amount = _money()
    tax_category = serializers.CharField(required=False)
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)


class ExplanationSerializer(Serializer):
    plain_text = serializers.CharField()
    fix_hint = serializers.CharField()


class IssueSerializer(Serializer):
    rule_id = serializers.CharField()
    severity = serializers.ChoiceField(choices=["fatal", "warning", "information"])
    message = serializers.CharField()
    location = serializers.CharField(allow_blank=True)
    test = serializers.CharField(allow_blank=True)
    source = serializers.CharField()  # type: ignore[assignment]  # DRF removes declared fields from the class
    explanation = ExplanationSerializer(required=False)


class ValidationSerializer(Serializer):
    status = serializers.ChoiceField(choices=["valid", "warnings", "invalid", "not_applicable"])
    engine = serializers.CharField()
    xsd_ok = serializers.BooleanField(required=False)
    fatal_count = serializers.IntegerField()
    warning_count = serializers.IntegerField()
    issues = IssueSerializer(many=True)


class ResolveSerializer(Serializer):
    enabled = serializers.BooleanField()
    reason_code = serializers.CharField(required=False)
    reason = serializers.CharField(required=False)


class CheckSerializer(Serializer):
    id = serializers.UUIDField()
    check_id = serializers.CharField()
    code = serializers.CharField()
    severity = serializers.ChoiceField(choices=Check.Severity.choices)
    message = serializers.CharField()
    details = serializers.DictField()
    resolved_by_name = serializers.CharField(required=False)
    resolved_at = serializers.DateTimeField(required=False)
    resolution_note = serializers.CharField(required=False)
    resolve = ResolveSerializer()


class ApprovalSerializer(Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    decided_by_name = serializers.CharField()
    comment = serializers.CharField(allow_blank=True)
    decided_at = serializers.DateTimeField()


class EventSerializer(Serializer):
    type = serializers.CharField()
    actor_name = serializers.CharField(required=False)
    data = serializers.DictField()  # type: ignore[assignment]  # DRF removes declared fields from the class
    created_at = serializers.DateTimeField()


class DocumentDetailSerializer(DocumentSummarySerializer):
    source = serializers.CharField()  # type: ignore[assignment]  # DRF removes declared fields from the class
    size_bytes = serializers.IntegerField()
    failure_reason = serializers.CharField(required=False)
    text_truncated = serializers.BooleanField()
    invoice = InvoiceDetailSerializer(required=False)
    lines = LineSerializer(many=True)
    validation = ValidationSerializer(required=False)
    checks = CheckSerializer(many=True)
    approvals = ApprovalSerializer(many=True)
    events = EventSerializer(many=True)


def _name(user: User | None) -> str | None:
    return user.name if user is not None else None


def _invoice_detail(invoice: Invoice) -> dict[str, Any]:  # boundary: drf data
    data: dict[str, Any] = {  # boundary: drf data
        "is_einvoice": invoice.is_einvoice,
        "type_code": invoice.type_code,
        "issue_date": invoice.issue_date,
        "due_date": invoice.due_date,
        "notes": invoice.notes or [],
        "tax_breakdown": invoice.tax_breakdown or [],
        "field_confidence": invoice.field_confidence or {},
        "field_evidence": invoice.field_evidence or {},
    }
    for name in (*INVOICE_TEXT_FIELDS, *INVOICE_MONEY_FIELDS):
        data[name] = getattr(invoice, name)
    return data


def _validation(document: Document) -> dict[str, Any] | None:  # boundary: drf data
    report = getattr(document, "validation_report", None)
    if report is None:
        return None
    rule_ids = {issue.get("rule_id") for issue in report.issues}
    explanations = {
        explanation.rule_id: explanation
        for explanation in RuleExplanation.objects.filter(rule_id__in=rule_ids)
    }
    issues = []
    for issue in report.issues:
        entry = dict(issue)
        explanation = explanations.get(issue.get("rule_id", ""))
        if explanation is not None:
            entry["explanation"] = {
                "plain_text": explanation.plain_text,
                "fix_hint": explanation.fix_hint,
            }
        issues.append(entry)
    return {
        "status": report.status,
        "engine": report.engine,
        "xsd_ok": report.xsd_ok,
        "fatal_count": report.fatal_count,
        "warning_count": report.warning_count,
        "issues": issues,
    }


def check_entry(check: Check, document: Document, user: User) -> dict[str, Any]:  # boundary
    return {
        "id": check.id,
        "check_id": check.check_id,
        "code": check.code,
        "severity": check.severity,
        "message": check.message,
        "details": check.details,
        "resolved_by_name": _name(check.resolved_by),
        "resolved_at": check.resolved_at,
        "resolution_note": check.resolution_note,
        "resolve": check_resolvable(check, document, user).__dict__,
    }


def document_detail(document: Document, user: User) -> dict[str, Any]:  # boundary: drf data
    """Everything the review screen shows; needs `with_summary_data` on the queryset."""
    data = document_summary(document, user)
    invoice = _invoice_of(document)
    checks = document.checks.select_related("resolved_by").order_by("check_id", "created_at")
    detail: dict[str, Any] = {  # boundary: drf data
        **data,
        "source": document.source,
        "size_bytes": document.size_bytes,
        "failure_reason": document.failure_reason,
        "text_truncated": invoice.text_truncated if invoice else False,
        "invoice": _invoice_detail(invoice) if invoice else None,
        "lines": list(invoice.lines.order_by("position").values(*LINE_FIELDS)) if invoice else [],
        "validation": _validation(document),
        "checks": [check_entry(check, document, user) for check in checks],
        "approvals": [
            {
                "decision": approval.decision,
                "decided_by_name": approval.decided_by.name,
                "comment": approval.comment,
                "decided_at": approval.decided_at,
            }
            for approval in document.approvals.select_related("decided_by").order_by("decided_at")
        ],
        "events": [
            {
                "type": event.type,
                "actor_name": _name(event.actor),
                "data": event.data,
                "created_at": event.created_at,
            }
            for event in document.events.select_related("actor").order_by("-created_at", "-id")
        ],
    }
    result: dict[str, Any] = DocumentDetailSerializer(detail).data  # boundary: drf data
    return result


LINE_FIELDS = (
    "position", "line_id", "description", "quantity", "unit_code", "unit_price", "net_amount",
    "tax_category", "tax_rate",
)  # fmt: skip

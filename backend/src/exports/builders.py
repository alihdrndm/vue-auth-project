"""The export files of HANDOFF section 11: invoices CSV, lines CSV and the ZIP bundle.

The builders read documents loaded with `export_queryset` and return the file's bytes.
"""

import io
import json
import re
import zipfile
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from django.db.models import Prefetch, QuerySet

from eingang import storage
from eingang.clock import BUSINESS_TIME_ZONE
from exports import csv_format as fmt
from exports.models import ExportBatch
from invoices.models import Approval, Check, Document, Invoice, InvoiceLine, ValidationReport
from invoices.serializers import INVOICE_MONEY_FIELDS, INVOICE_TEXT_FIELDS, LINE_FIELDS

Format = ExportBatch.Format

INVOICE_COLUMNS = (
    "Belegdatum", "Rechnungsnummer", "Lieferant", "USt-IdNr", "IBAN", "Netto", "USt", "Brutto",
    "Zahlbetrag", "Währung", "Fällig", "Format", "E-Rechnung", "Validierung",
    "Freigegeben von", "Freigegeben am", "Eingang-ID",
)  # fmt: skip
LINE_COLUMNS = (
    "Eingang-ID", "Rechnungsnummer", "Position", "Beschreibung", "Menge", "Einheit",
    "Einzelpreis", "Netto", "Steuersatz",
)  # fmt: skip

FILE_PREFIX: dict[str, str] = {
    Format.CSV_INVOICES: "eingang-invoices",
    Format.CSV_LINES: "eingang-lines",
    Format.ZIP_BUNDLE: "eingang-bundle",
}
EXTENSION: dict[str, str] = {
    Format.CSV_INVOICES: "csv",
    Format.CSV_LINES: "csv",
    Format.ZIP_BUNDLE: "zip",
}
CONTENT_TYPE: dict[str, str] = {
    Format.CSV_INVOICES: "text/csv; charset=utf-8",
    Format.CSV_LINES: "text/csv; charset=utf-8",
    Format.ZIP_BUNDLE: "application/zip",
}
UNSAFE_NAME_CHARACTERS = re.compile(r"[^A-Za-z0-9._-]")


def filename(export_format: str, moment: datetime) -> str:
    """`eingang-<kind>-<YYYYMMDD-HHMM>.<ext>`, from the export's moment (UTC)."""
    stamp = moment.astimezone(UTC).strftime("%Y%m%d-%H%M")
    return f"{FILE_PREFIX[export_format]}-{stamp}.{EXTENSION[export_format]}"


def export_queryset(documents: QuerySet[Document]) -> QuerySet[Document]:
    """Everything the builders read, fetched up front (oldest received first)."""
    return (
        documents.select_related("invoice", "invoice__supplier", "validation_report")
        .prefetch_related(
            Prefetch("invoice__lines", queryset=InvoiceLine.objects.order_by("position")),
            Prefetch(
                "approvals",
                queryset=Approval.objects.select_related("decided_by").order_by("decided_at"),
            ),
            Prefetch(
                "checks",
                queryset=Check.objects.select_related("resolved_by").order_by(
                    "check_id", "created_at"
                ),
            ),
        )
        .order_by("received_at", "id")
    )


def _invoice(document: Document) -> Invoice | None:
    try:
        return document.invoice
    except Invoice.DoesNotExist:
        return None


def _report(document: Document) -> ValidationReport | None:
    try:
        return document.validation_report
    except ValidationReport.DoesNotExist:
        return None


def approval_of(document: Document) -> Approval | None:
    """The decision that approved the document (the latest, if it was approved again)."""
    approved = [a for a in document.approvals.all() if a.decision == Approval.Decision.APPROVED]
    return approved[-1] if approved else None


def _invoice_row(document: Document) -> list[str]:
    invoice = _invoice(document)
    report = _report(document)
    approval = approval_of(document)
    approved_on = approval.decided_at.astimezone(BUSINESS_TIME_ZONE).date() if approval else None
    if invoice is None:
        amounts = ["", "", "", ""]
        head = ["", "", "", "", ""]
        tail = ["", "", fmt.text(document.format_label), ""]
    else:
        credit = fmt.is_credit_note(invoice.type_code)
        supplier = invoice.supplier.name if invoice.supplier else invoice.seller_name
        head = [
            fmt.day(invoice.issue_date),
            fmt.text(invoice.invoice_number),
            fmt.text(supplier),
            fmt.text(invoice.seller_vat_id),
            fmt.text(invoice.payee_iban),
        ]
        amounts = [
            fmt.money(invoice.net_total, credit_note=credit),
            fmt.money(invoice.tax_total, credit_note=credit),
            fmt.money(invoice.gross_total, credit_note=credit),
            fmt.money(invoice.payable_amount, credit_note=credit),
        ]
        tail = [
            fmt.text(invoice.currency),
            fmt.day(invoice.due_date),
            fmt.text(document.format_label),
            fmt.yes_no(invoice.is_einvoice),
        ]
    return [
        *head,
        *amounts,
        *tail,
        fmt.text(report.status if report else None),
        fmt.text(approval.decided_by.name if approval else None),
        fmt.day(approved_on),
        fmt.text(str(document.id)),
    ]


def csv_invoices(documents: Sequence[Document]) -> bytes:
    return fmt.write_csv(INVOICE_COLUMNS, [_invoice_row(document) for document in documents])


def _line_rows(document: Document) -> list[list[str]]:
    invoice = _invoice(document)
    if invoice is None:
        return []
    credit = fmt.is_credit_note(invoice.type_code)
    return [
        [
            fmt.text(str(document.id)),
            fmt.text(invoice.invoice_number),
            str(line.position),
            fmt.text(line.description),
            fmt.number(line.quantity),
            fmt.text(line.unit_code),
            fmt.number(line.unit_price),
            fmt.money(line.net_amount, credit_note=credit),
            fmt.number(line.tax_rate),
        ]
        for line in invoice.lines.all()
    ]


def csv_lines(documents: Sequence[Document]) -> bytes:
    rows = [row for document in documents for row in _line_rows(document)]
    return fmt.write_csv(LINE_COLUMNS, rows)


def safe_name(name: str) -> str:
    """An original file name reduced to `[A-Za-z0-9._-]`, never hidden or empty."""
    cleaned = UNSAFE_NAME_CHARACTERS.sub("_", name).lstrip(".")
    return cleaned or "original"


def _json_value(value: object) -> object:
    """JSON for the report: money as strings, dates ISO, timestamps RFC 3339 UTC."""
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"not JSON serialisable: {type(value).__name__}")


def report(document: Document) -> dict[str, object]:
    """`reports/<Eingang-ID>.json`: canonical invoice, validation issues, checks, approval."""
    invoice = _invoice(document)
    canonical: dict[str, object] | None = None
    if invoice is not None:
        canonical = {
            "is_einvoice": invoice.is_einvoice,
            "type_code": invoice.type_code,
            "issue_date": invoice.issue_date,
            "due_date": invoice.due_date,
            **{
                name: getattr(invoice, name)
                for name in (*INVOICE_TEXT_FIELDS, *INVOICE_MONEY_FIELDS)
            },
            "notes": invoice.notes or [],
            "tax_breakdown": invoice.tax_breakdown or [],
            "lines": [
                {name: getattr(line, name) for name in LINE_FIELDS} for line in invoice.lines.all()
            ],
        }
    validation = _report(document)
    approval = approval_of(document)
    return {
        "eingang_id": document.id,
        "original_filename": document.original_filename,
        "format": document.format_label,
        "invoice": canonical,
        "validation": None
        if validation is None
        else {
            "status": validation.status,
            "engine": validation.engine,
            "xsd_ok": validation.xsd_ok,
            "fatal_count": validation.fatal_count,
            "warning_count": validation.warning_count,
            "issues": validation.issues,
        },
        "checks": [
            {
                "check_id": check.check_id,
                "code": check.code,
                "severity": check.severity,
                "message": check.message,
                "details": check.details,
                "resolved_by": check.resolved_by.name if check.resolved_by else None,
                "resolved_at": check.resolved_at,
                "resolution_note": check.resolution_note,
            }
            for check in document.checks.all()
        ],
        "approval": None
        if approval is None
        else {
            "decision": approval.decision,
            "decided_by": approval.decided_by.name,
            "comment": approval.comment,
            "decided_at": approval.decided_at,
        },
    }


def _add(archive: zipfile.ZipFile, name: str, data: bytes, moment: datetime) -> None:
    stamp = moment.astimezone(UTC)
    entry = zipfile.ZipInfo(
        name, (stamp.year, stamp.month, stamp.day, stamp.hour, stamp.minute, stamp.second)
    )
    entry.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(entry, data)


def zip_bundle(documents: Sequence[Document], moment: datetime) -> bytes:
    """Both CSVs, every original and one JSON report per invoice."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        _add(archive, filename(Format.CSV_INVOICES, moment), csv_invoices(documents), moment)
        _add(archive, filename(Format.CSV_LINES, moment), csv_lines(documents), moment)
        for document in documents:
            original = f"originals/{document.id}-{safe_name(document.original_filename)}"
            _add(archive, original, storage.read(document.storage_key), moment)
        for document in documents:
            body = json.dumps(report(document), default=_json_value, ensure_ascii=False, indent=2)
            _add(archive, f"reports/{document.id}.json", body.encode("utf-8"), moment)
    return buffer.getvalue()


def build(export_format: str, documents: Sequence[Document], moment: datetime) -> bytes:
    if export_format == Format.CSV_INVOICES:
        return csv_invoices(documents)
    if export_format == Format.CSV_LINES:
        return csv_lines(documents)
    return zip_bundle(documents, moment)

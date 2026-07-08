"""Activities of ProcessInvoiceWorkflow: all the I/O of processing one document.

Each activity is idempotent (running it twice leaves the same state), reads current state
from the database rather than trusting its input, and raises PermanentError for input that
retrying cannot fix. The LLM activities refuse with BudgetExceededError until the LLM layer
exists (M5).
"""

import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

from django.db import close_old_connections, transaction
from temporalio import activity

from eingang import clock, storage
from eingang.temporal_errors import BudgetExceededError, PermanentError
from eingang.workflows import contracts as c
from einvoice.detect import Detection, Kind, Profile, Syntax, detect, format_label
from einvoice.errors import CorruptPdfError, InvoiceParseError, UnsupportedFileError
from einvoice.model import CanonicalInvoice
from einvoice.namespaces import UBL_CREDIT_NOTE_ROOT
from einvoice.parse_cii import parse_cii
from einvoice.parse_ubl import parse_ubl
from einvoice.pdf import extract_text
from einvoice.validate import validate_xml
from einvoice.visualize import applies_to, to_html
from einvoice.xmlsafe import parse_xml
from invoices import checks
from invoices.models import Document, Event, Invoice, InvoiceLine, RuleExplanation, ValidationReport
from invoices.status import processing_outcome, transition
from suppliers import matching

logger = logging.getLogger(__name__)
Status = Document.Status


def _document(document_id: UUID) -> Document:
    # Activities run on worker threads; drop connections Django considers stale first.
    close_old_connections()
    return Document.objects.select_related("organization").get(id=document_id)


def _xml_of(document: Document) -> bytes:
    return storage.read(storage.derived_key(document.organization_id, document.id, "invoice.xml"))


@activity.defn(name=c.ACT_BEGIN_PROCESSING)
def begin_processing(ref: c.DocumentRef) -> None:
    document = _document(ref.document_id)
    if document.status == Status.RECEIVED:
        transition(document, Status.PROCESSING, None)


@activity.defn(name=c.ACT_SET_STEP)
def set_step(step: c.StepInput) -> None:
    document = _document(step.document_id)
    if document.processing_step == step.step:
        return
    with transaction.atomic():
        document.processing_step = step.step
        document.save(update_fields=["processing_step", "updated_at"])
        Event.objects.create(
            organization=document.organization,
            document=document,
            type=Event.Type.PROCESSING_STEP,
            data={"step": step.step},
        )


def _summary(detection: Detection) -> c.DetectionSummary:
    return c.DetectionSummary(
        kind=detection.kind.value,
        syntax=detection.syntax.value if detection.syntax else None,
        profile=detection.profile.value if detection.profile else None,
        profile_version=detection.profile_version,
        spec_id=detection.spec_id,
        has_text_layer=detection.has_text_layer,
        page_count=detection.page_count,
        is_einvoice=detection.is_einvoice,
    )


@activity.defn(name=c.ACT_DETECT_DOCUMENT)
def detect_document(ref: c.DocumentRef) -> c.DetectionSummary:
    document = _document(ref.document_id)
    data = storage.read(document.storage_key)
    try:
        detection = detect(data, document.original_filename)
    except UnsupportedFileError as error:
        raise PermanentError(f"Unsupported file: {error.reason}") from error
    except CorruptPdfError as error:
        raise PermanentError("The PDF cannot be read.") from error
    if detection.xml is not None and detection.kind in (Kind.XML, Kind.HYBRID_PDF):
        key = storage.derived_key(document.organization_id, document.id, "invoice.xml")
        storage.write(key, detection.xml)
    fields = ["kind", "format_label", "updated_at"]
    if detection.page_count is not None:
        # The whole text of the first six pages, not truncated (HANDOFF section 5).
        text_key = storage.derived_key(document.organization_id, document.id, "text.txt")
        storage.write(text_key, extract_text(data).as_text().encode("utf-8"))
        document.text_storage_key = text_key
        fields.append("text_storage_key")
    document.kind = detection.kind.value
    document.format_label = format_label(detection, None)
    document.save(update_fields=fields)
    return _summary(detection)


@activity.defn(name=c.ACT_VALIDATE_DOCUMENT)
def validate_document(detected: c.DetectedDocument) -> str:
    document = _document(detected.document_id)
    summary = detected.detection
    if summary.syntax is None or summary.profile is None:
        raise PermanentError("Validation needs a structured invoice.")
    try:
        report = validate_xml(
            _xml_of(document), Syntax(summary.syntax), Profile(summary.profile),
            summary.profile_version,
        )  # fmt: skip
    except UnsupportedFileError as error:
        raise PermanentError(f"Unsupported XML: {error.reason}") from error
    ValidationReport.objects.update_or_create(
        document=document,
        defaults={
            "status": report.status,
            "engine": report.engine,
            "xsd_ok": report.xsd_ok,
            "issues": [issue.__dict__ for issue in report.issues],
            "fatal_count": report.fatal_count,
            "warning_count": report.warning_count,
            "ran_at": clock.now(),
        },
    )
    return report.status


def _invoice_columns(invoice: CanonicalInvoice) -> dict[str, Any]:  # boundary: model fields
    columns: dict[str, Any] = {  # boundary: model fields
        "invoice_number": invoice.invoice_number,
        "type_code": invoice.type_code,
        "issue_date": invoice.issue_date,
        "due_date": invoice.due_date,
        "currency": invoice.currency,
        "buyer_reference": invoice.buyer_reference,
        "order_reference": invoice.order_reference,
        "payee_iban": invoice.payee_iban,
        "payee_bic": invoice.payee_bic,
        "payment_terms": invoice.payment_terms,
        "notes": invoice.notes,
        "tax_breakdown": [row.model_dump(mode="json") for row in invoice.tax_breakdown],
    }
    for party_name, party in (("seller", invoice.seller), ("buyer", invoice.buyer)):
        for field in ("name", "vat_id", "street", "postcode", "city", "country_code", "email"):
            columns[f"{party_name}_{field}"] = getattr(party, field)
    columns["seller_tax_number"] = invoice.seller.tax_number
    for field in (
        "line_total", "allowance_total", "charge_total", "net_total", "tax_total",
        "gross_total", "prepaid_amount", "payable_amount",
    ):  # fmt: skip
        columns[field] = getattr(invoice, field)
    return columns


@activity.defn(name=c.ACT_PARSE_STRUCTURED)
def parse_structured(detected: c.DetectedDocument) -> None:
    document = _document(detected.document_id)
    summary = detected.detection
    xml = _xml_of(document)
    try:
        root = parse_xml(xml)
        canonical = parse_cii(xml) if summary.syntax == Syntax.CII else parse_ubl(xml)
    except (InvoiceParseError, UnsupportedFileError) as error:
        raise PermanentError(f"The invoice XML cannot be read: {error}") from error
    with transaction.atomic():
        invoice, _created = Invoice.objects.update_or_create(
            document=document,
            defaults={
                "organization": document.organization,
                "syntax": summary.syntax,
                "profile": summary.profile,
                "spec_id": summary.spec_id,
                "is_einvoice": summary.is_einvoice,
                "extraction_method": Invoice.ExtractionMethod.XML,
                **_invoice_columns(canonical),
            },
        )
        invoice.lines.all().delete()
        InvoiceLine.objects.bulk_create(
            [
                InvoiceLine(invoice=invoice, position=position, **line.model_dump())
                for position, line in enumerate(canonical.lines, start=1)
            ]
        )
        detection = Detection(
            kind=Kind(summary.kind),
            syntax=Syntax(summary.syntax) if summary.syntax else None,
            profile=Profile(summary.profile) if summary.profile else None,
            ubl_credit_note=root.tag == UBL_CREDIT_NOTE_ROOT,
        )
        document.format_label = format_label(detection, canonical.type_code)
        document.save(update_fields=["format_label", "updated_at"])


@activity.defn(name=c.ACT_RENDER_VISUALIZATION)
def render_visualization(detected: c.DetectedDocument) -> bool:
    """Store the HTML page; when it cannot be rendered, store nothing (section 4)."""
    document = _document(detected.document_id)
    summary = detected.detection
    xml = _xml_of(document)
    detection = Detection(
        kind=Kind(summary.kind),
        syntax=Syntax(summary.syntax) if summary.syntax else None,
        profile=Profile(summary.profile) if summary.profile else None,
        xml=xml,
    )
    if not applies_to(detection) or detection.syntax is None:
        return False
    try:
        page = to_html(xml, detection.syntax)
    except Exception:  # broad on purpose: the UI falls back to the XML view
        logger.warning("Visualisation failed for document %s", document.id)
        return False
    key = storage.derived_key(document.organization_id, document.id, "visualization.html")
    storage.write(key, page.encode("utf-8"))
    return True


@activity.defn(name=c.ACT_COMPARE_PDF_TO_XML)
def compare_pdf_to_xml(ref: c.DocumentRef) -> c.ComparisonResult:
    # The LLM layer arrives in M5; until then every LLM call is refused as disabled.
    raise BudgetExceededError("disabled")


@activity.defn(name=c.ACT_EXTRACT_WITH_LLM)
def extract_with_llm(ref: c.DocumentRef) -> None:
    # The LLM layer arrives in M5; until then every LLM call is refused as disabled.
    raise BudgetExceededError("disabled")


@activity.defn(name=c.ACT_CREATE_EMPTY_INVOICE)
def create_empty_invoice(request: c.EmptyInvoiceInput) -> None:
    """An invoice without data, for a person to fill in (scans, refused extraction)."""
    document = _document(request.document_id)
    Invoice.objects.get_or_create(
        document=document,
        defaults={
            "organization": document.organization,
            "extraction_method": Invoice.ExtractionMethod.MANUAL,
            "is_einvoice": request.is_einvoice,
        },
    )


@activity.defn(name=c.ACT_RECORD_NOTE)
def record_note(request: c.NoteInput) -> None:
    document = _document(request.document_id)
    already = Event.objects.filter(
        document=document, type=Event.Type.PROCESSING_STEP, data__note=request.note
    ).exists()
    if not already:
        Event.objects.create(
            organization=document.organization,
            document=document,
            type=Event.Type.PROCESSING_STEP,
            data={"note": request.note},
        )


@activity.defn(name=c.ACT_MATCH_SUPPLIER)
def match_supplier(ref: c.DocumentRef) -> None:
    document = _document(ref.document_id)
    invoice = Invoice.objects.filter(document=document).first()
    if invoice is not None:
        matching.match_supplier(invoice)


@activity.defn(name=c.ACT_RUN_CHECKS)
def run_checks(request: c.ChecksInput) -> int:
    document = _document(request.document_id)
    context = checks.CheckContext(
        pdf_xml_differences=[difference.model_dump() for difference in request.pdf_xml_differences],
        extraction_unavailable_reason=request.extraction_unavailable_reason,
        today=clock.today(),
    )
    findings = checks.evaluate(document, context)
    checks.apply_findings(document, findings)
    return len(findings)


@activity.defn(name=c.ACT_EXPLAIN_RULES)
def explain_rules(ref: c.DocumentRef) -> int:
    """Rule IDs of the report without a stored explanation; explaining them needs the LLM."""
    document = _document(ref.document_id)
    report = ValidationReport.objects.filter(document=document).first()
    if report is None:
        return 0
    rule_ids = {issue.get("rule_id") for issue in report.issues if issue.get("rule_id")}
    known = set(
        RuleExplanation.objects.filter(rule_id__in=rule_ids).values_list("rule_id", flat=True)
    )
    if rule_ids - known:
        raise BudgetExceededError("disabled")
    return 0


@activity.defn(name=c.ACT_FINISH_PROCESSING)
def finish_processing(ref: c.DocumentRef) -> str:
    document = _document(ref.document_id)
    if document.processing_step != "done":
        document.processing_step = "done"
        document.save(update_fields=["processing_step", "updated_at"])
    if document.status == Status.PROCESSING:
        document = transition(document, processing_outcome(document), None)
    return str(document.status)


@activity.defn(name=c.ACT_READ_STATUS)
def read_status(ref: c.DocumentRef) -> c.StatusSnapshot:
    document = _document(ref.document_id)
    return c.StatusSnapshot(
        status=document.status,
        reminder_after_days=document.organization.reminder_after_days,
        deleted=document.deleted_at is not None,
    )


@activity.defn(name=c.ACT_SEND_REMINDER)
def send_reminder(request: c.ReminderInput) -> None:
    document = _document(request.document_id)
    already = Event.objects.filter(
        document=document, type=Event.Type.REMINDER_SENT, data__number=request.reminder_number
    ).exists()
    if not already:
        Event.objects.create(
            organization=document.organization,
            document=document,
            type=Event.Type.REMINDER_SENT,
            data={"number": request.reminder_number},
        )


@activity.defn(name=c.ACT_MARK_FAILED)
def mark_failed(request: c.FailInput) -> None:
    document = _document(request.document_id)
    if document.status == Status.PROCESSING:
        transition(document, Status.FAILED, None, failure_reason=request.reason)


PROCESS_INVOICE_ACTIVITIES: list[Callable[..., object]] = [
    begin_processing,
    set_step,
    detect_document,
    validate_document,
    parse_structured,
    render_visualization,
    compare_pdf_to_xml,
    extract_with_llm,
    create_empty_invoice,
    record_note,
    match_supplier,
    run_checks,
    explain_rules,
    finish_processing,
    read_status,
    send_reminder,
    mark_failed,
]

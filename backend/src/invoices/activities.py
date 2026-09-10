"""Activities of ProcessInvoiceWorkflow: all the I/O of processing one document.

Each activity is idempotent (running it twice leaves the same state), reads current state
from the database rather than trusting its input, and raises PermanentError for input that
retrying cannot fix. The LLM activities refuse with BudgetExceededError until the LLM layer
exists (M5).
"""

import logging
from collections.abc import Callable
from uuid import UUID

from django.db import close_old_connections, transaction
from temporalio import activity

from eingang import clock, storage
from eingang.config import get_settings
from eingang.temporal_errors import PermanentError
from eingang.workflows import contracts as c
from einvoice.detect import Detection, Kind, Profile, Syntax, detect, format_label
from einvoice.errors import CorruptPdfError, InvoiceParseError, UnsupportedFileError
from einvoice.namespaces import UBL_CREDIT_NOTE_ROOT
from einvoice.parse_cii import parse_cii
from einvoice.parse_ubl import parse_ubl
from einvoice.pdf import extract_text
from einvoice.validate import validate_xml
from einvoice.visualize import applies_to, to_html
from einvoice.xmlsafe import parse_xml
from invoices import checks, extraction, persist
from invoices.models import Document, Event, Invoice, RuleExplanation, ValidationReport
from invoices.status import processing_outcome, transition
from llm import client as llm_client
from llm import prompts
from llm.schemas import ComparedValues, ExtractedInvoice, RuleExplanationOut
from suppliers import matching

logger = logging.getLogger(__name__)
# max_output_tokens per LLM feature (HANDOFF "LLM features in Eingang").
EXTRACT_MAX_OUTPUT_TOKENS = 2500
COMPARE_MAX_OUTPUT_TOKENS = 600
EXPLAIN_MAX_OUTPUT_TOKENS = 400
Status = Document.Status


def _find(document_id: UUID) -> Document | None:
    # Activities run on worker threads; drop connections Django considers stale first.
    close_old_connections()
    return Document.objects.select_related("organization").filter(id=document_id).first()


def _document(document_id: UUID) -> Document:
    """The document; gone for good (its sandbox expired) is a permanent error, not retried."""
    document = _find(document_id)
    if document is None:
        raise PermanentError("The document no longer exists.")
    return document


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
        persist.save_structured(
            document,
            canonical,
            syntax=summary.syntax,
            profile=summary.profile,
            spec_id=summary.spec_id,
            is_einvoice=summary.is_einvoice,
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


def _visible_text(document: Document) -> tuple[str, bool]:
    """The stored PDF text (first six pages), cut at 12,000 characters, and whether it was cut."""
    if not document.text_storage_key:
        raise PermanentError("The document has no extracted text.")
    text = storage.read(document.text_storage_key).decode("utf-8")
    return text[: extraction.TEXT_LIMIT], len(text) > extraction.TEXT_LIMIT


@activity.defn(name=c.ACT_COMPARE_PDF_TO_XML)
def compare_pdf_to_xml(ref: c.DocumentRef) -> c.ComparisonResult:
    """Read five values from the visible PDF and list where they differ from the XML (section 6)."""
    if not get_settings().COMPARE_HYBRID_PDF:
        return c.ComparisonResult(compared=False)
    document = _document(ref.document_id)
    text, _truncated = _visible_text(document)
    xml = _xml_of(document)
    try:
        canonical = parse_cii(xml)  # hybrid PDFs carry CII (detection rule D2)
    except (InvoiceParseError, UnsupportedFileError) as error:
        raise PermanentError(f"The invoice XML cannot be read: {error}") from error
    shown = llm_client.call(
        llm_client.Request(
            purpose="compare",
            prompt=prompts.load("compare_pdf_xml", 1),
            data=prompts.fenced("document", text),
            output=ComparedValues,
            max_output_tokens=COMPARE_MAX_OUTPUT_TOKENS,
            organization=document.organization,
        )
    )
    differences = extraction.compare(canonical, shown, text)
    return c.ComparisonResult(
        differences=[c.FieldDifference(**difference) for difference in differences]
    )


@activity.defn(name=c.ACT_EXTRACT_WITH_LLM)
def extract_with_llm(ref: c.DocumentRef) -> None:
    """Read the invoice fields from the PDF text and grade each one (section 5)."""
    document = _document(ref.document_id)
    text, truncated = _visible_text(document)
    prompt = prompts.load("extract_invoice", 1)
    answer = llm_client.call(
        llm_client.Request(
            purpose="extract",
            prompt=prompt,
            data=prompts.fenced("document", text),
            output=ExtractedInvoice,
            max_output_tokens=EXTRACT_MAX_OUTPUT_TOKENS,
            organization=document.organization,
        )
    )
    persist.save_extracted(
        document,
        extraction.post_process(answer, text),
        truncated=truncated,
        prompt_version=prompt.label,
    )


@activity.defn(name=c.ACT_CREATE_EMPTY_INVOICE)
def create_empty_invoice(request: c.EmptyInvoiceInput) -> None:
    """An invoice without data, for a person to fill in (scans, refused extraction)."""
    persist.save_empty(_document(request.document_id), is_einvoice=request.is_einvoice)


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
    """Explain, once ever, each rule of the report that has no stored explanation (section 7).

    Each explanation is stored as soon as it arrives, so a refusal part-way keeps the
    earlier ones; a refused or failed call ends the activity (the official message is
    shown alone).
    """
    document = _document(ref.document_id)
    report = ValidationReport.objects.filter(document=document).first()
    if report is None:
        return 0
    issues = {issue["rule_id"]: issue for issue in report.issues if issue.get("rule_id")}
    known = set(
        RuleExplanation.objects.filter(rule_id__in=issues).values_list("rule_id", flat=True)
    )
    prompt = prompts.load("explain_rule", 1)
    explained = 0
    for rule_id in sorted(set(issues) - known):
        issue = issues[rule_id]
        rule = "\n".join(
            [
                f"Rule ID: {rule_id}",
                f"Official message: {issue.get('message', '')}",
                f"Source: {issue.get('source', '')}",
            ]
        )
        answer = llm_client.call(
            llm_client.Request(
                purpose="explain",
                prompt=prompt,
                data=prompts.fenced("rule", rule),
                output=RuleExplanationOut,
                max_output_tokens=EXPLAIN_MAX_OUTPUT_TOKENS,
                organization=document.organization,
            )
        ).clipped()
        _created = RuleExplanation.objects.get_or_create(
            rule_id=rule_id,
            defaults={
                "plain_text": answer.plain_text,
                "fix_hint": answer.fix_hint,
                "source": RuleExplanation.Source.LLM,
                "prompt_version": prompt.label,
            },
        )
        explained += 1
    return explained


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
    document = _find(ref.document_id)
    if document is None:  # removed with its expired sandbox: the workflow ends
        return c.StatusSnapshot(status="", reminder_after_days=1, deleted=True)
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
    document = _find(request.document_id)
    if document is not None and document.status == Status.PROCESSING:
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

"""The sample documents of a sandbox or the local organisation (section 12, "How the seed works").

Used by `POST /sandbox`, `seed_dev` (`pnpm seed`) and the e2e setup. It runs in the API
process, so it reads the precomputed detection, validation and invoice of each sample
instead of running validation or PDF code, then runs supplier matching, the checks and the
status rule with the same functions the workflow activities use. It makes no LLM call and
starts no workflow: seeded documents have an empty `workflow_id`.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction

from accounts.models import Organization, User
from eingang import clock, storage
from eingang.workflows.contracts import NOTE_PDF_NOT_COMPARED
from einvoice.model import CanonicalInvoice
from invoices import checks, extraction, persist
from invoices.models import Approval, Document, Event, ValidationReport
from invoices.status import SYSTEM, processing_outcome, transition
from llm.schemas import ComparedValues, ExtractedInvoice
from suppliers.matching import match_supplier

Status = Document.Status
Kind = Document.Kind

STRUCTURED_KINDS = frozenset({Kind.XML, Kind.HYBRID_PDF})
EXTRACTED_KINDS = frozenset({Kind.PDF_TEXT, Kind.LEGACY_ZUGFERD1, Kind.HYBRID_PDF_UNSUPPORTED})
# Without a precomputed answer, extraction is refused as disabled and leaves check C12.
EXTRACTION_REASON = "disabled"
# The two sample decisions of the sandbox table, made a day after the invoice arrived.
DECISIONS = {
    "S11": (Status.APPROVED, ""),
    "S12": (Status.REJECTED, "Wrong cost centre, please ask for a corrected invoice."),
}
DECISION_DELAY = timedelta(days=1)


@dataclass(frozen=True)
class Sample:
    id: str
    file: str
    sha256: str
    received_offset_minutes: int
    format_label: str
    expected_checks: tuple[str, ...]
    expected_status: str


@dataclass(frozen=True)
class SamplePeople:
    """Who appears in the history: the accountant reviews, the approver decides."""

    accountant: User
    approver: User


def samples_dir() -> Path:
    path: Path = settings.SAMPLES_DIR
    return path


@cache
def manifest() -> tuple[Sample, ...]:
    data = json.loads((samples_dir() / "manifest.json").read_text(encoding="utf-8"))
    return tuple(
        Sample(
            id=entry["id"],
            file=entry["file"],
            sha256=entry["sha256"],
            received_offset_minutes=int(entry["received_offset_minutes"]),
            format_label=entry["format_label"],
            expected_checks=tuple(entry["expected_checks"]),
            expected_status=entry["expected_status"],
        )
        for entry in data["samples"]
    )


def _precomputed(sample: Sample) -> dict[str, Any]:  # boundary: JSON file
    path = samples_dir() / "precomputed" / f"{sample.id}.json"
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))  # boundary: JSON
    return data


def _optional(name: str) -> bytes | None:
    path = samples_dir() / "precomputed" / name
    return path.read_bytes() if path.exists() else None


def seed_samples(organization: Organization, people: SamplePeople) -> list[Document]:
    """Add the twelve samples to `organization`, processed as a real run would leave them."""
    moment = clock.now()
    ordered = sorted(manifest(), key=lambda sample: -sample.received_offset_minutes)
    with transaction.atomic():
        seeded = [_store(organization, sample, moment) for sample in ordered]
        # In received order, so each document is checked only against earlier ones.
        for sample, document in seeded:
            _process(document, _precomputed(sample))
        for sample, document in seeded:
            if sample.id in DECISIONS:
                _decide(document, people, *DECISIONS[sample.id])
        for _sample, document in seeded:
            _date_history(document)
    return [document for _sample, document in seeded]


def _store(organization: Organization, sample: Sample, moment: datetime) -> tuple[Sample, Document]:
    data = (samples_dir() / sample.file).read_bytes()
    precomputed = _precomputed(sample)
    extension = sample.file.rsplit(".", 1)[-1]
    document = Document(
        organization=organization,
        source=Document.Source.SAMPLE,
        original_filename=sample.file,
        content_type="application/pdf" if extension == "pdf" else "application/xml",
        size_bytes=len(data),
        sha256=sample.sha256,
        received_at=moment - timedelta(minutes=sample.received_offset_minutes),
        kind=precomputed["detection"]["kind"],
        format_label=sample.format_label,
        status=Status.RECEIVED,
        workflow_id="",
    )
    document.storage_key = storage.original_key(
        organization.id, document.id, sample.sha256, extension
    )
    storage.write(document.storage_key, data)
    xml = data if document.kind == Kind.XML else _optional(f"{sample.id}.xml")
    if xml is not None:
        storage.write(storage.derived_key(organization.id, document.id, "invoice.xml"), xml)
    if precomputed.get("text") is not None:
        document.text_storage_key = storage.derived_key(organization.id, document.id, "text.txt")
        storage.write(document.text_storage_key, str(precomputed["text"]).encode("utf-8"))
    page = _optional(f"{sample.id}.visualization.html")
    if page is not None:
        key = storage.derived_key(organization.id, document.id, "visualization.html")
        storage.write(key, page)
    document.save()
    _event(document, Event.Type.DOCUMENT_RECEIVED, {"source": "sample", "size_bytes": len(data)})
    return sample, document


def _event(document: Document, kind: str, data: dict[str, object]) -> None:
    Event.objects.create(
        organization=document.organization, document=document, type=kind, data=data
    )


def _step(document: Document, step: str) -> None:
    document.processing_step = step
    document.save(update_fields=["processing_step", "updated_at"])
    _event(document, Event.Type.PROCESSING_STEP, {"step": step})


def _process(document: Document, precomputed: dict[str, Any]) -> None:  # boundary: JSON
    """Steps 1-5 of ProcessInvoiceWorkflow, from the precomputed results."""
    document = transition(document, Status.PROCESSING, SYSTEM)
    detection = precomputed["detection"]
    _step(document, "detect")
    reason: str | None = None
    differences: list[dict[str, str]] | None = None
    if document.kind in STRUCTURED_KINDS:
        _step(document, "validate")
        report = precomputed["validation"]
        ValidationReport.objects.create(
            document=document,
            status=report["status"],
            engine=report["engine"],
            xsd_ok=report["xsd_ok"],
            issues=report["issues"],
            fatal_count=report["fatal_count"],
            warning_count=report["warning_count"],
            ran_at=clock.now(),
        )
        invoice_xml = CanonicalInvoice.model_validate(precomputed["invoice"])
        invoice = persist.save_structured(
            document,
            invoice_xml,
            syntax=detection["syntax"],
            profile=detection["profile"],
            spec_id=detection["spec_id"],
            is_einvoice=detection["is_einvoice"],
        )
        if document.kind == Kind.HYBRID_PDF:
            differences = _precomputed_differences(precomputed, invoice_xml)
            if differences is None:
                # Not precomputed: a real run without the LLM records that it was skipped.
                _event(document, Event.Type.PROCESSING_STEP, {"note": NOTE_PDF_NOT_COMPARED})
    elif document.kind in EXTRACTED_KINDS:
        _step(document, "extract")
        stored = precomputed.get("extraction")
        if stored is None:
            invoice = persist.save_empty(document)
            reason = EXTRACTION_REASON
        else:
            # The precomputed LLM answer (`precompute-samples`), graded like a live one.
            text = str(precomputed.get("text") or "")
            cut = text[: extraction.TEXT_LIMIT]
            invoice = persist.save_extracted(
                document,
                extraction.post_process(ExtractedInvoice.model_validate(stored["answer"]), cut),
                truncated=len(text) > extraction.TEXT_LIMIT,
                prompt_version=str(stored["prompt_version"]),
            )
    else:  # a scan: a person types the fields in (check C10)
        invoice = persist.save_empty(document)
    _step(document, "check")
    match_supplier(invoice)
    context = checks.CheckContext(
        pdf_xml_differences=differences or [],
        extraction_unavailable_reason=reason,
        today=clock.today(),
    )
    checks.apply_findings(document, checks.evaluate(document, context))
    _step(document, "done")
    transition(document, processing_outcome(document), SYSTEM)


def _precomputed_differences(
    precomputed: dict[str, Any],
    invoice_xml: CanonicalInvoice,  # boundary: JSON file
) -> list[dict[str, str]] | None:
    """The C09 differences from the precomputed comparison, or None when there is none."""
    stored = precomputed.get("comparison")
    if stored is None:
        return None
    shown = ComparedValues.model_validate(stored["answer"])
    text = str(precomputed.get("text") or "")[: extraction.TEXT_LIMIT]
    return extraction.compare(invoice_xml, shown, text)


def _decide(document: Document, people: SamplePeople, decision: str, comment: str) -> None:
    if document.status == Status.NEEDS_REVIEW:
        transition(document, Status.AWAITING_APPROVAL, people.accountant)
    transition(document, decision, people.approver, comment=comment or None)


def _date_history(document: Document) -> None:
    """Date the history after the arrival, as a real run would have written it.

    Rows are created now; their dates move to a second apart from `received_at`, and the
    sample decision a day later. Only the seed rewrites dates, and only of rows it just made.
    """
    start = document.received_at
    events = Event.objects.filter(document=document).order_by("created_at", "id")
    for offset, event in enumerate(events):
        when = start + timedelta(seconds=offset)
        if event.type == Event.Type.APPROVAL_DECIDED:
            when += DECISION_DELAY
        Event.objects.filter(id=event.id).update(created_at=when)
    Approval.objects.filter(document=document).update(decided_at=start + DECISION_DELAY)

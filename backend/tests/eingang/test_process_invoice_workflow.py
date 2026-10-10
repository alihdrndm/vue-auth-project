"""ProcessInvoiceWorkflow on Temporal's time-skipping test server, with fake activities.

The fakes keep the document's status in memory, so the tests can play the API's part
(changing the status, then signalling) and check what the workflow did.
"""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from temporalio import activity
from temporalio.client import Client, WorkflowHandle
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from eingang.temporal_errors import BudgetExceededError, PermanentError
from eingang.workflows import contracts as c
from eingang.workflows.process_invoice import ProcessInvoiceWorkflow


@dataclass
class FakeDocument:
    kind: str = "xml"
    status: str = "received"
    reminder_after_days: int = 3
    deleted: bool = False
    extraction: str = "ok"  # ok | refused | broken
    comparison_switched_off: bool = False
    fail_detection_times: int = 0
    calls: list[str] = field(default_factory=list)
    checks_input: c.ChecksInput | None = None
    reminders: list[int] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def fake_activities(
    doc: FakeDocument,
) -> list[Callable[..., Awaitable[Any]]]:  # boundary: temporalio
    def record(name: str) -> None:
        doc.calls.append(name)

    @activity.defn(name=c.ACT_BEGIN_PROCESSING)
    async def begin(ref: c.DocumentRef) -> None:
        record("begin")
        if doc.status == "received":
            doc.status = "processing"

    @activity.defn(name=c.ACT_SET_STEP)
    async def set_step(step: c.StepInput) -> None:
        record(f"step:{step.step}")

    @activity.defn(name=c.ACT_DETECT_DOCUMENT)
    async def detect(ref: c.DocumentRef) -> c.DetectionSummary:
        record("detect")
        if doc.fail_detection_times > 0:
            doc.fail_detection_times -= 1
            raise PermanentError("The PDF cannot be read.")
        structured = doc.kind in ("xml", "hybrid_pdf")
        return c.DetectionSummary(
            kind=doc.kind, syntax="ubl" if structured else None,
            profile="XRECHNUNG" if structured else None, is_einvoice=structured,
        )  # fmt: skip

    @activity.defn(name=c.ACT_VALIDATE_DOCUMENT)
    async def validate(detected: c.DetectedDocument) -> str:
        record("validate")
        return "valid"

    @activity.defn(name=c.ACT_PARSE_STRUCTURED)
    async def parse(detected: c.DetectedDocument) -> None:
        record("parse")

    @activity.defn(name=c.ACT_RENDER_VISUALIZATION)
    async def render(detected: c.DetectedDocument) -> bool:
        record("render")
        return True

    @activity.defn(name=c.ACT_COMPARE_PDF_TO_XML)
    async def compare(ref: c.DocumentRef) -> c.ComparisonResult:
        record("compare")
        if doc.comparison_switched_off:
            return c.ComparisonResult(compared=False)
        raise BudgetExceededError("disabled")

    @activity.defn(name=c.ACT_EXTRACT_WITH_LLM)
    async def extract(ref: c.DocumentRef) -> None:
        record("extract")
        if doc.extraction == "refused":
            raise BudgetExceededError("budget_daily_public")
        if doc.extraction == "broken":
            raise PermanentError("The model's answer did not parse.")

    @activity.defn(name=c.ACT_CREATE_EMPTY_INVOICE)
    async def empty(request: c.EmptyInvoiceInput) -> None:
        record("empty_invoice")

    @activity.defn(name=c.ACT_RECORD_NOTE)
    async def note(request: c.NoteInput) -> None:
        doc.notes.append(request.note)

    @activity.defn(name=c.ACT_MATCH_SUPPLIER)
    async def match(ref: c.DocumentRef) -> None:
        record("match")

    @activity.defn(name=c.ACT_RUN_CHECKS)
    async def run_checks(request: c.ChecksInput) -> int:
        record("checks")
        doc.checks_input = request
        return 0

    @activity.defn(name=c.ACT_EXPLAIN_RULES)
    async def explain(ref: c.DocumentRef) -> int:
        record("explain")
        raise BudgetExceededError("disabled")

    @activity.defn(name=c.ACT_FINISH_PROCESSING)
    async def finish(ref: c.DocumentRef) -> str:
        record("finish")
        straight = doc.kind == "xml"
        doc.status = "awaiting_approval" if straight else "needs_review"
        return doc.status

    @activity.defn(name=c.ACT_READ_STATUS)
    async def read_status(ref: c.DocumentRef) -> c.StatusSnapshot:
        return c.StatusSnapshot(
            status=doc.status, reminder_after_days=doc.reminder_after_days, deleted=doc.deleted
        )

    @activity.defn(name=c.ACT_SEND_REMINDER)
    async def remind(request: c.ReminderInput) -> None:
        doc.reminders.append(request.reminder_number)

    @activity.defn(name=c.ACT_MARK_FAILED)
    async def failed(request: c.FailInput) -> None:
        record(f"failed:{request.reason}")
        doc.status = "failed"

    return [
        begin, set_step, detect, validate, parse, render, compare, extract, empty, note,
        match, run_checks, explain, finish, read_status, remind, failed,
    ]  # fmt: skip


Handle = WorkflowHandle[Any, str]  # boundary: temporalio, workflow class not needed here
Scenario = Callable[[Handle, FakeDocument, WorkflowEnvironment], Awaitable[None]]


def run(doc: FakeDocument, scenario: Scenario) -> str:
    """Start the workflow for `doc`, let `scenario` play the API, return the result."""

    async def main() -> str:
        async with await WorkflowEnvironment.start_time_skipping(
            data_converter=pydantic_data_converter
        ) as env:
            client: Client = env.client
            async with Worker(
                client,
                task_queue=c.TASK_QUEUE,
                workflows=[ProcessInvoiceWorkflow],
                activities=fake_activities(doc),
            ):
                document_id = uuid.uuid4()
                handle = await client.start_workflow(
                    c.WF_PROCESS_INVOICE,
                    c.ProcessInvoiceInput(document_id=document_id),
                    id=c.process_invoice_workflow_id(document_id),
                    task_queue=c.TASK_QUEUE,
                    result_type=str,
                )
                await scenario(handle, doc, env)
                result: str = await handle.result()
                return result

    return asyncio.run(main())


async def until(condition: Callable[[], bool], env: WorkflowEnvironment) -> None:
    for _ in range(200):
        if condition():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("condition not reached")


async def export_when_awaiting(handle: Handle, doc: FakeDocument, env: WorkflowEnvironment) -> None:
    await until(lambda: doc.status == "awaiting_approval", env)
    doc.status = "exported"
    await handle.signal(c.SIG_EXPORTED)


def test_valid_xml_goes_to_awaiting_approval() -> None:
    doc = FakeDocument(kind="xml")
    assert run(doc, export_when_awaiting) == "exported"
    assert doc.calls[:8] == [
        "begin", "step:detect", "detect", "step:validate", "validate", "parse", "render",
        "step:check",
    ]  # fmt: skip
    assert "extract" not in doc.calls
    assert doc.checks_input is not None
    assert doc.checks_input.extraction_unavailable_reason is None


async def delete_when_reviewable(
    handle: Handle, doc: FakeDocument, env: WorkflowEnvironment
) -> None:
    await until(lambda: doc.status == "needs_review", env)
    doc.deleted = True
    await handle.signal(c.SIG_DELETED)


def test_plain_pdf_with_llm_needs_review() -> None:
    doc = FakeDocument(kind="pdf_text", extraction="ok")
    assert run(doc, delete_when_reviewable) == "deleted"
    assert "extract" in doc.calls
    assert "empty_invoice" not in doc.calls
    assert doc.checks_input is not None
    assert doc.checks_input.extraction_unavailable_reason is None


def test_C12_budget_refused_creates_an_empty_invoice_with_the_reason() -> None:
    doc = FakeDocument(kind="pdf_text", extraction="refused")
    run(doc, delete_when_reviewable)
    assert "empty_invoice" in doc.calls
    assert doc.checks_input is not None
    assert doc.checks_input.extraction_unavailable_reason == "budget_daily_public"


def test_C12_failed_extraction_reason_is_error() -> None:
    doc = FakeDocument(kind="legacy_zugferd1", extraction="broken")
    run(doc, delete_when_reviewable)
    assert doc.checks_input is not None
    assert doc.checks_input.extraction_unavailable_reason == "error"
    assert doc.status == "needs_review"  # extraction failure never fails the document


def test_C10_scan_gets_an_empty_manual_invoice() -> None:
    doc = FakeDocument(kind="pdf_no_text")
    run(doc, delete_when_reviewable)
    assert "empty_invoice" in doc.calls
    assert "extract" not in doc.calls


def test_hybrid_pdf_not_compared_is_noted_on_the_timeline() -> None:
    doc = FakeDocument(kind="hybrid_pdf")
    run(doc, delete_when_reviewable)  # the fake sends hybrid PDFs to needs_review
    assert doc.notes == [c.NOTE_PDF_NOT_COMPARED]


def test_comparison_switched_off_is_skipped_without_a_note() -> None:
    doc = FakeDocument(kind="hybrid_pdf", comparison_switched_off=True)
    run(doc, delete_when_reviewable)
    assert "compare" in doc.calls
    assert doc.notes == []


def test_a_wake_up_does_not_move_the_next_reminder() -> None:
    doc = FakeDocument(kind="xml", reminder_after_days=3)

    async def scenario(handle: Handle, doc: FakeDocument, env: WorkflowEnvironment) -> None:
        await until(lambda: doc.status == "awaiting_approval", env)
        await env.sleep(timedelta(days=2))
        await handle.signal(c.SIG_SYNC)
        await env.sleep(timedelta(days=1, hours=12))
        assert doc.reminders == [1]  # day 3, not day 5
        doc.status = "exported"
        await handle.signal(c.SIG_EXPORTED)

    assert run(doc, scenario) == "exported"


def test_retry_is_recovered_by_sync_when_the_retry_signal_is_lost() -> None:
    doc = FakeDocument(kind="xml", fail_detection_times=1)

    async def scenario(handle: Handle, doc: FakeDocument, env: WorkflowEnvironment) -> None:
        await until(lambda: doc.status == "failed", env)
        doc.status = "processing"  # the API committed the retry; its signal never arrived
        await handle.signal(c.SIG_SYNC)  # the daily maintenance
        await export_when_awaiting(handle, doc, env)

    assert run(doc, scenario) == "exported"
    assert doc.calls.count("detect") == 2


def test_reminder_fires_three_times_and_stops() -> None:
    doc = FakeDocument(kind="xml", reminder_after_days=3)

    async def scenario(handle: Handle, doc: FakeDocument, env: WorkflowEnvironment) -> None:
        await until(lambda: doc.status == "awaiting_approval", env)
        await env.sleep(timedelta(days=30))
        assert doc.reminders == [1, 2, 3]
        doc.status = "exported"
        await handle.signal(c.SIG_EXPORTED)

    assert run(doc, scenario) == "exported"
    assert doc.reminders == [1, 2, 3]


def test_reject_reopen_review_approve_export_completes_the_workflow() -> None:
    doc = FakeDocument(kind="xml")

    async def scenario(handle: Handle, doc: FakeDocument, env: WorkflowEnvironment) -> None:
        await until(lambda: doc.status == "awaiting_approval", env)
        for status, name in [
            ("rejected", c.SIG_DECIDED),
            ("needs_review", c.SIG_REOPENED),
            ("awaiting_approval", c.SIG_REVIEWED),
            ("approved", c.SIG_DECIDED),
        ]:
            doc.status = status  # the API changes the database, then signals
            await handle.signal(name)
            await phase_becomes(handle, status)
        doc.status = "exported"
        await handle.signal(c.SIG_EXPORTED)

    assert run(doc, scenario) == "exported"


async def phase_becomes(handle: Handle, status: str) -> None:
    for _ in range(200):
        if await handle.query(c.QUERY_PHASE) == status:
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"phase never became {status}")


def test_permanent_failure_waits_for_retry_then_processes_again() -> None:
    doc = FakeDocument(kind="xml", fail_detection_times=1)

    async def scenario(handle: Handle, doc: FakeDocument, env: WorkflowEnvironment) -> None:
        await until(lambda: doc.status == "failed", env)
        assert "failed:The PDF cannot be read." in doc.calls
        # The API moves failed -> processing, then signals retry.
        doc.status = "processing"
        await handle.signal(c.SIG_RETRY)
        await export_when_awaiting(handle, doc, env)

    assert run(doc, scenario) == "exported"
    assert doc.calls.count("detect") == 2


def test_180_days_without_a_signal_ends_the_workflow() -> None:
    doc = FakeDocument(kind="pdf_no_text")

    async def scenario(handle: Handle, doc: FakeDocument, env: WorkflowEnvironment) -> None:
        await until(lambda: doc.status == "needs_review", env)
        await env.sleep(timedelta(days=181))

    assert run(doc, scenario) == "abandoned"


def test_phase_query_reports_the_status_last_acted_on() -> None:
    doc = FakeDocument(kind="xml")

    async def scenario(handle: Handle, doc: FakeDocument, env: WorkflowEnvironment) -> None:
        await until(lambda: doc.status == "awaiting_approval", env)
        await asyncio.sleep(0.3)
        assert await handle.query(c.QUERY_PHASE) == "awaiting_approval"
        doc.status = "exported"
        await handle.signal(c.SIG_EXPORTED)

    run(doc, scenario)

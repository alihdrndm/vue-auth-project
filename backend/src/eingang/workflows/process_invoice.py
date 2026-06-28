"""ProcessInvoiceWorkflow: process one document, then wait for people (HANDOFF "Temporal").

Deterministic: it imports only the standard library, temporalio and the contracts module,
and calls activities by name. Every signal only wakes the waiting loop, which then re-reads
the document's status from the database, so a lost or duplicated signal cannot corrupt
state; the query `phase` returns the status it last acted on.
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

with workflow.unsafe.imports_passed_through():
    from eingang.workflows import contracts as c

NON_RETRYABLE = [c.PERMANENT_ERROR_TYPE, c.BUDGET_EXCEEDED_ERROR_TYPE]
DEFAULT_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=5,
    non_retryable_error_types=NON_RETRYABLE,
)
LLM_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=2,
    non_retryable_error_types=NON_RETRYABLE,
)
DEFAULT_TIMEOUT = timedelta(seconds=60)
HEAVY_TIMEOUT = timedelta(seconds=90)  # validation and visualisation
LLM_TIMEOUT = timedelta(seconds=120)
MAX_REMINDERS = 3
MAX_WAIT = timedelta(days=180)
STRUCTURED_KINDS = frozenset({"xml", "hybrid_pdf"})
EXTRACTED_KINDS = frozenset({"pdf_text", "legacy_zugferd1", "hybrid_pdf_unsupported"})
END_STATUSES = frozenset({"exported"})


def _expect[T](value: object, kind: type[T]) -> T:
    if not isinstance(value, kind):
        raise TypeError(f"expected {kind.__name__}, got {type(value).__name__}")
    return value


def _cause_type(error: ActivityError) -> str | None:
    cause = error.cause
    return cause.type if isinstance(cause, ApplicationError) else None


def _unavailable_reason(error: ActivityError) -> str:
    """The C12 reason: the budget refusal's reason, or `error` for any other failure."""
    cause = error.cause
    if isinstance(cause, ApplicationError) and cause.type == c.BUDGET_EXCEEDED_ERROR_TYPE:
        details = cause.details
        if details and isinstance(details[0], str):
            return details[0]
    return "error"


def _failure_reason(error: ActivityError) -> str:
    cause = error.cause
    if isinstance(cause, ApplicationError) and cause.type == c.PERMANENT_ERROR_TYPE:
        return cause.message
    return "Processing failed after several attempts."


@workflow.defn(name=c.WF_PROCESS_INVOICE)
class ProcessInvoiceWorkflow:
    def __init__(self) -> None:
        self._phase = "received"
        self._woken = False
        self._retry = False

    # --- signals and query ------------------------------------------------------

    def _wake(self) -> None:
        self._woken = True

    @workflow.signal(name=c.SIG_REVIEWED)
    def reviewed(self) -> None:
        self._wake()

    @workflow.signal(name=c.SIG_SENT_BACK)
    def sent_back(self) -> None:
        self._wake()

    @workflow.signal(name=c.SIG_DECIDED)
    def decided(self) -> None:
        self._wake()

    @workflow.signal(name=c.SIG_REOPENED)
    def reopened(self) -> None:
        self._wake()

    @workflow.signal(name=c.SIG_EXPORTED)
    def exported(self) -> None:
        self._wake()

    @workflow.signal(name=c.SIG_DELETED)
    def deleted(self) -> None:
        self._wake()

    @workflow.signal(name=c.SIG_SYNC)
    def sync(self) -> None:
        self._wake()

    @workflow.signal(name=c.SIG_RETRY)
    def retry(self) -> None:
        self._retry = True
        self._wake()

    @workflow.query(name=c.QUERY_PHASE)
    def phase(self) -> str:
        return self._phase

    # --- run --------------------------------------------------------------------

    @workflow.run
    async def run(self, request: c.ProcessInvoiceInput) -> str:
        ref = c.DocumentRef(document_id=request.document_id)
        while True:
            self._retry = False
            self._phase = await self._process(ref)
            outcome = await self._wait(ref)
            if outcome != "retry":
                return outcome

    async def _activity(
        self,
        name: str,
        argument: object,
        result_type: type | None = None,
        limit: timedelta = DEFAULT_TIMEOUT,
        retry: RetryPolicy = DEFAULT_RETRY,
    ) -> object:
        return await workflow.execute_activity(
            name,
            argument,
            result_type=result_type,
            start_to_close_timeout=limit,
            retry_policy=retry,
        )

    async def _step(self, ref: c.DocumentRef, step: str) -> None:
        await self._activity(c.ACT_SET_STEP, c.StepInput(document_id=ref.document_id, step=step))

    async def _process(self, ref: c.DocumentRef) -> str:
        """Steps 1-5; any permanent failure ends in `failed` (step 7)."""
        document_id = ref.document_id
        try:
            await self._activity(c.ACT_BEGIN_PROCESSING, ref)
            await self._step(ref, "detect")
            detection = await self._activity(
                c.ACT_DETECT_DOCUMENT, ref, result_type=c.DetectionSummary
            )
            detection = _expect(detection, c.DetectionSummary)
            detected = c.DetectedDocument(document_id=document_id, detection=detection)
            differences: list[c.FieldDifference] = []
            unavailable_reason: str | None = None
            if detection.kind in STRUCTURED_KINDS:
                await self._step(ref, "validate")
                await self._activity(c.ACT_VALIDATE_DOCUMENT, detected, str, HEAVY_TIMEOUT)
                await self._activity(c.ACT_PARSE_STRUCTURED, detected)
                await self._activity(c.ACT_RENDER_VISUALIZATION, detected, bool, HEAVY_TIMEOUT)
                if detection.kind == "hybrid_pdf":
                    differences = await self._compare(ref)
            elif detection.kind in EXTRACTED_KINDS:
                await self._step(ref, "extract")
                unavailable_reason = await self._extract(ref)
            else:  # pdf_no_text: a person types the fields in (check C10)
                await self._activity(
                    c.ACT_CREATE_EMPTY_INVOICE, c.EmptyInvoiceInput(document_id=document_id)
                )
            await self._step(ref, "check")
            await self._activity(c.ACT_MATCH_SUPPLIER, ref)
            await self._activity(
                c.ACT_RUN_CHECKS,
                c.ChecksInput(
                    document_id=document_id,
                    pdf_xml_differences=differences,
                    extraction_unavailable_reason=unavailable_reason,
                ),
                int,
            )
            await self._explain(ref)
            await self._step(ref, "done")
            status = await self._activity(c.ACT_FINISH_PROCESSING, ref, str)
            return str(status)
        except ActivityError as error:
            await self._activity(
                c.ACT_MARK_FAILED,
                c.FailInput(document_id=document_id, reason=_failure_reason(error)),
            )
            return "failed"

    async def _compare(self, ref: c.DocumentRef) -> list[c.FieldDifference]:
        try:
            result = await self._activity(
                c.ACT_COMPARE_PDF_TO_XML, ref, c.ComparisonResult, LLM_TIMEOUT, LLM_RETRY
            )
        except ActivityError:
            workflow.logger.info("PDF-versus-XML comparison skipped")
            await self._activity(
                c.ACT_RECORD_NOTE,
                c.NoteInput(document_id=ref.document_id, note=c.NOTE_PDF_NOT_COMPARED),
            )
            return []
        return list(_expect(result, c.ComparisonResult).differences)

    async def _extract(self, ref: c.DocumentRef) -> str | None:
        """None when extraction worked; otherwise the reason for check C12."""
        try:
            await self._activity(c.ACT_EXTRACT_WITH_LLM, ref, None, LLM_TIMEOUT, LLM_RETRY)
        except ActivityError as error:
            await self._activity(
                c.ACT_CREATE_EMPTY_INVOICE, c.EmptyInvoiceInput(document_id=ref.document_id)
            )
            return _unavailable_reason(error)
        return None

    async def _explain(self, ref: c.DocumentRef) -> None:
        try:
            await self._activity(c.ACT_EXPLAIN_RULES, ref, int, LLM_TIMEOUT, LLM_RETRY)
        except ActivityError as error:
            # The official rule message is shown alone (HANDOFF "LLM features").
            workflow.logger.info("Rule explanations skipped: %s", _cause_type(error))

    async def _wait(self, ref: c.DocumentRef) -> str:
        """Step 6: wait for signals; remind while awaiting approval; end on export/delete."""
        reminders = 0
        status_since = workflow.now()
        last_status = ""
        while True:
            self._woken = False
            snapshot = await self._activity(c.ACT_READ_STATUS, ref, c.StatusSnapshot)
            snapshot = _expect(snapshot, c.StatusSnapshot)
            if snapshot.status != last_status:
                last_status = snapshot.status
                status_since = workflow.now()
                reminders = 0
            self._phase = snapshot.status
            if snapshot.deleted:
                return "deleted"
            if snapshot.status in END_STATUSES:
                return snapshot.status
            if self._retry and snapshot.status == "processing":
                return "retry"
            self._retry = False
            remaining = MAX_WAIT - (workflow.now() - status_since)
            if remaining <= timedelta(0):
                workflow.logger.info("Stopped waiting after 180 days")
                return "abandoned"
            remind = snapshot.status == "awaiting_approval" and reminders < MAX_REMINDERS
            timeout = remaining
            if remind:
                timeout = min(remaining, timedelta(days=snapshot.reminder_after_days))
            try:
                await workflow.wait_condition(lambda: self._woken, timeout=timeout)
            except TimeoutError:
                if remind and timeout < remaining:
                    reminders += 1
                    await self._activity(
                        c.ACT_SEND_REMINDER,
                        c.ReminderInput(document_id=ref.document_id, reminder_number=reminders),
                    )
                # Otherwise 180 days have passed; the next turn of the loop ends it.

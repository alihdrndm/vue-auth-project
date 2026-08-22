"""Names and payloads shared by the API, the workflows and the activities.

Imports only pydantic and the standard library (HANDOFF "Temporal conventions"), so the
deterministic workflow code may import it. Payloads carry IDs and small summaries, never
file contents or personal data.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

TASK_QUEUE = "eingang-main"

# Workflows
WF_PROCESS_INVOICE = "ProcessInvoiceWorkflow"
WF_MAINTENANCE = "MaintenanceWorkflow"
WF_MAILBOX_POLL = "MailboxPollWorkflow"

# Schedules (their actions get short fixed IDs; runs are named <id>-<timestamp>)
SCHEDULE_DAILY_MAINTENANCE = "daily-maintenance"
SCHEDULE_ACTION_MAINTENANCE = "maintenance"
SCHEDULE_MAILBOX_POLL = "mailbox-poll"
SCHEDULE_ACTION_MAILBOX_POLL = "mailbox-poll"

# Activities of ProcessInvoiceWorkflow
ACT_BEGIN_PROCESSING = "begin_processing"
ACT_SET_STEP = "set_step"
ACT_DETECT_DOCUMENT = "detect_document"
ACT_VALIDATE_DOCUMENT = "validate_document"
ACT_PARSE_STRUCTURED = "parse_structured"
ACT_RENDER_VISUALIZATION = "render_visualization"
ACT_COMPARE_PDF_TO_XML = "compare_pdf_to_xml"
ACT_EXTRACT_WITH_LLM = "extract_with_llm"
ACT_CREATE_EMPTY_INVOICE = "create_empty_invoice"
ACT_RECORD_NOTE = "record_note"
ACT_MATCH_SUPPLIER = "match_supplier"
ACT_RUN_CHECKS = "run_checks"
ACT_EXPLAIN_RULES = "explain_rules"
ACT_FINISH_PROCESSING = "finish_processing"
ACT_READ_STATUS = "read_status"
ACT_SEND_REMINDER = "send_reminder"
ACT_MARK_FAILED = "mark_failed"

# Activities of MaintenanceWorkflow and MailboxPollWorkflow
ACT_DELETE_EXPIRED_SANDBOXES = "delete_expired_sandboxes"
ACT_START_UNSTARTED_DOCUMENTS = "start_unstarted_documents"
ACT_RESIGNAL_INCONSISTENT_DOCUMENTS = "resignal_inconsistent_documents"
ACT_LOG_DAILY_STATS = "log_daily_stats"
ACT_FETCH_MAIL = "fetch_mail"

# Signals and the query of ProcessInvoiceWorkflow
SIG_REVIEWED = "reviewed"
SIG_SENT_BACK = "sent_back"
SIG_DECIDED = "decided"
SIG_REOPENED = "reopened"
SIG_EXPORTED = "exported"
SIG_DELETED = "deleted"
SIG_RETRY = "retry"
SIG_SYNC = "sync"
QUERY_PHASE = "phase"

# ApplicationError types the workflow recognises (err.cause.type)
PERMANENT_ERROR_TYPE = "PermanentError"
BUDGET_EXCEEDED_ERROR_TYPE = "BudgetExceededError"

# Timeline note when the visible PDF of a hybrid PDF was not compared
NOTE_PDF_NOT_COMPARED = "Visible PDF not compared"


def process_invoice_workflow_id(document_id: UUID) -> str:
    """Deterministic, so starting the same document twice while it runs is rejected."""
    return f"invoice-{document_id}"


class _Payload(BaseModel):
    model_config = ConfigDict(frozen=True)


class ProcessInvoiceInput(_Payload):
    document_id: UUID


class DocumentRef(_Payload):
    document_id: UUID


class StepInput(_Payload):
    document_id: UUID
    step: str  # detect, validate, extract, check, done


class DetectionSummary(_Payload):
    """What detection found; no XML bytes (they stay in storage)."""

    kind: str
    syntax: str | None = None
    profile: str | None = None
    profile_version: str | None = None
    spec_id: str | None = None
    has_text_layer: bool | None = None
    page_count: int | None = None
    is_einvoice: bool = False


class DetectedDocument(_Payload):
    document_id: UUID
    detection: DetectionSummary


class EmptyInvoiceInput(_Payload):
    document_id: UUID
    is_einvoice: bool = False


class NoteInput(_Payload):
    document_id: UUID
    note: str


class FieldDifference(_Payload):
    field: str
    xml: str | None
    pdf: str | None


class ComparisonResult(_Payload):
    differences: list[FieldDifference] = []
    # False when COMPARE_HYBRID_PDF is off: nothing was compared and nothing is noted.
    compared: bool = True


class ChecksInput(_Payload):
    document_id: UUID
    pdf_xml_differences: list[FieldDifference] = []
    extraction_unavailable_reason: str | None = None


class FailInput(_Payload):
    document_id: UUID
    reason: str


class StatusSnapshot(_Payload):
    status: str
    reminder_after_days: int
    deleted: bool = False


class ReminderInput(_Payload):
    document_id: UUID
    reminder_number: int


class ResyncSummary(_Payload):
    """What `resignal_inconsistent_documents` did.

    `abandoned_workflows` counts open documents whose workflow is no longer running
    (for example after the 180-day wait ended), so the daily maintenance can log them.
    """

    resignalled_documents: int = 0
    abandoned_workflows: int = 0


class MaintenanceSummary(_Payload):
    deleted_sandboxes: int = 0
    started_documents: int = 0
    resignalled_documents: int = 0
    abandoned_workflows: int = 0
    document_count: int = 0
    failed_steps: list[str] = []


class MailboxResult(_Payload):
    document_ids: list[UUID] = []

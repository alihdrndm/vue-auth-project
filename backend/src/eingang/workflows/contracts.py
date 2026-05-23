"""Names and payloads shared by the API, the workflows and the activities.

Imports only pydantic and the standard library (HANDOFF "Temporal conventions"), so the
deterministic workflow code may import it.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

TASK_QUEUE = "eingang-main"

WF_PROCESS_INVOICE = "ProcessInvoiceWorkflow"


def process_invoice_workflow_id(document_id: UUID) -> str:
    """Deterministic, so starting the same document twice while it runs is rejected."""
    return f"invoice-{document_id}"


class ProcessInvoiceInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: UUID

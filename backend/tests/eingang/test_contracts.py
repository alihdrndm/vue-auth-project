import uuid

from eingang.workflows.contracts import (
    TASK_QUEUE,
    WF_PROCESS_INVOICE,
    ProcessInvoiceInput,
    process_invoice_workflow_id,
)


def test_workflow_ids_are_deterministic_per_document() -> None:
    document_id = uuid.UUID("01900000-0000-7000-8000-000000000001")
    assert process_invoice_workflow_id(document_id) == f"invoice-{document_id}"


def test_names_and_payload() -> None:
    assert TASK_QUEUE == "eingang-main"
    assert WF_PROCESS_INVOICE == "ProcessInvoiceWorkflow"
    payload = ProcessInvoiceInput(document_id=uuid.UUID(int=1))
    assert payload.model_dump(mode="json") == {"document_id": str(uuid.UUID(int=1))}

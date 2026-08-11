"""MailboxPollWorkflow: the optional IMAP intake (HANDOFF "Temporal workflows").

Run by schedule `mailbox-poll`. Deterministic: it imports only the standard library,
temporalio and the contracts module, and calls the activity and the child workflows by name.
Each stored attachment gets its own ProcessInvoiceWorkflow, started as an abandoned child so
it outlives this short poll run.
"""

from datetime import timedelta
from uuid import UUID

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.workflow import ParentClosePolicy

with workflow.unsafe.imports_passed_through():
    from eingang.workflows import contracts as c

# The default retry policy of HANDOFF "Temporal conventions".
DEFAULT_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=5,
    non_retryable_error_types=[c.PERMANENT_ERROR_TYPE, c.BUDGET_EXCEEDED_ERROR_TYPE],
)
# Longer than the default 60 s: one poll logs in over the network and downloads up to
# MAX_MESSAGES_PER_POLL messages, each socket operation bounded by its own 30 s timeout.
FETCH_MAIL_TIMEOUT = timedelta(seconds=120)


@workflow.defn(name=c.WF_MAILBOX_POLL)
class MailboxPollWorkflow:
    @workflow.run
    async def run(self) -> c.MailboxResult:
        result: c.MailboxResult = await workflow.execute_activity(
            c.ACT_FETCH_MAIL,
            result_type=c.MailboxResult,
            start_to_close_timeout=FETCH_MAIL_TIMEOUT,
            retry_policy=DEFAULT_RETRY,
        )
        for document_id in result.document_ids:
            await self._start_processing(document_id)
        return result

    async def _start_processing(self, document_id: UUID) -> None:
        workflow_id = c.process_invoice_workflow_id(document_id)
        try:
            await workflow.start_child_workflow(
                c.WF_PROCESS_INVOICE,
                c.ProcessInvoiceInput(document_id=document_id),
                id=workflow_id,
                task_queue=c.TASK_QUEUE,
                parent_close_policy=ParentClosePolicy.ABANDON,
            )
        except WorkflowAlreadyStartedError:
            # Already running (for example started by the maintenance); nothing to do.
            workflow.logger.info("Processing of document %s already started", document_id)

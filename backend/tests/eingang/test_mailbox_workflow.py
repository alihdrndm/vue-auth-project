"""MailboxPollWorkflow on Temporal's time-skipping test server, with a fake activity."""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any
from uuid import UUID

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from eingang.workflows import contracts as c
from eingang.workflows.mailbox import MailboxPollWorkflow

# Filled by an activity: workflow code runs in a sandbox with its own copy of this module.
started_children: list[tuple[str, UUID]] = []
ACT_RECORD_CHILD = "test_record_child"


class ChildRun(c.DocumentRef):
    workflow_id: str


@activity.defn(name=ACT_RECORD_CHILD)
async def record_child(child: ChildRun) -> None:
    started_children.append((child.workflow_id, child.document_id))


@workflow.defn(name=c.WF_PROCESS_INVOICE)
class FakeProcessInvoiceWorkflow:
    """Records its workflow ID and input, then ends."""

    @workflow.run
    async def run(self, data: c.ProcessInvoiceInput) -> None:
        child = ChildRun(workflow_id=workflow.info().workflow_id, document_id=data.document_id)
        await workflow.execute_activity(
            ACT_RECORD_CHILD, child, start_to_close_timeout=timedelta(seconds=10)
        )


def fake_fetch_mail(document_ids: list[UUID]) -> Callable[..., Awaitable[Any]]:
    @activity.defn(name=c.ACT_FETCH_MAIL)
    async def fetch_mail() -> c.MailboxResult:
        return c.MailboxResult(document_ids=document_ids)

    return fetch_mail


def run(document_ids: list[UUID], *, already_running: UUID | None = None) -> c.MailboxResult:
    started_children.clear()

    async def main() -> c.MailboxResult:
        async with await WorkflowEnvironment.start_time_skipping(
            data_converter=pydantic_data_converter
        ) as env:
            client: Client = env.client
            async with Worker(
                client,
                task_queue=c.TASK_QUEUE,
                workflows=[MailboxPollWorkflow, FakeProcessInvoiceWorkflow],
                activities=[fake_fetch_mail(document_ids), record_child],
            ):
                if already_running is not None:
                    await _start_blocking_run(client, already_running)
                result: c.MailboxResult = await client.execute_workflow(
                    c.WF_MAILBOX_POLL,
                    id=f"{c.SCHEDULE_ACTION_MAILBOX_POLL}-{uuid.uuid4()}",
                    task_queue=c.TASK_QUEUE,
                    result_type=c.MailboxResult,
                )
                # Abandoned children run on after the poll ends; wait for the ones it started.
                for document_id in document_ids:
                    if document_id != already_running:
                        workflow_id = c.process_invoice_workflow_id(document_id)
                        await client.get_workflow_handle(workflow_id).result()
                return result

    return asyncio.run(main())


async def _start_blocking_run(client: Client, document_id: UUID) -> None:
    """A run under the document's workflow ID on a queue no worker polls, so it stays open."""
    await client.start_workflow(
        c.WF_PROCESS_INVOICE,
        c.ProcessInvoiceInput(document_id=document_id),
        id=c.process_invoice_workflow_id(document_id),
        task_queue="nobody-polls-this",
    )


def test_starts_one_processing_child_per_stored_document() -> None:
    first, second = uuid.uuid4(), uuid.uuid4()
    result = run([first, second])
    assert result.document_ids == [first, second]
    assert sorted(started_children) == sorted(
        [
            (c.process_invoice_workflow_id(first), first),
            (c.process_invoice_workflow_id(second), second),
        ]
    )


def test_an_empty_mailbox_starts_nothing() -> None:
    result = run([])
    assert result.document_ids == []
    assert started_children == []


def test_a_document_whose_processing_already_runs_is_accepted() -> None:
    running, new = uuid.uuid4(), uuid.uuid4()
    result = run([running, new], already_running=running)
    assert result.document_ids == [running, new]
    assert started_children == [(c.process_invoice_workflow_id(new), new)]

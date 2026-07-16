"""MaintenanceWorkflow on Temporal's time-skipping test server, with fake activities."""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from temporalio import activity
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from eingang.temporal_errors import PermanentError
from eingang.workflows import contracts as c
from eingang.workflows.maintenance import MaintenanceWorkflow


def fake_activities(
    calls: list[str], failing: str | None = None
) -> list[Callable[..., Awaitable[Any]]]:  # boundary: temporalio
    def record(name: str) -> None:
        calls.append(name)
        if name == failing:
            raise PermanentError("The step broke.")

    @activity.defn(name=c.ACT_DELETE_EXPIRED_SANDBOXES)
    async def delete_sandboxes() -> int:
        record(c.ACT_DELETE_EXPIRED_SANDBOXES)
        return 2

    @activity.defn(name=c.ACT_START_UNSTARTED_DOCUMENTS)
    async def start_unstarted() -> int:
        record(c.ACT_START_UNSTARTED_DOCUMENTS)
        return 3

    @activity.defn(name=c.ACT_RESIGNAL_INCONSISTENT_DOCUMENTS)
    async def resignal() -> c.ResyncSummary:
        record(c.ACT_RESIGNAL_INCONSISTENT_DOCUMENTS)
        return c.ResyncSummary(resignalled_documents=4, abandoned_workflows=1)

    @activity.defn(name=c.ACT_LOG_DAILY_STATS)
    async def stats() -> int:
        record(c.ACT_LOG_DAILY_STATS)
        return 17

    return [delete_sandboxes, start_unstarted, resignal, stats]


def run(calls: list[str], failing: str | None = None) -> c.MaintenanceSummary:
    async def main() -> c.MaintenanceSummary:
        async with await WorkflowEnvironment.start_time_skipping(
            data_converter=pydantic_data_converter
        ) as env:
            client: Client = env.client
            async with Worker(
                client,
                task_queue=c.TASK_QUEUE,
                workflows=[MaintenanceWorkflow],
                activities=fake_activities(calls, failing),
            ):
                summary: c.MaintenanceSummary = await client.execute_workflow(
                    c.WF_MAINTENANCE,
                    id=f"{c.SCHEDULE_ACTION_MAINTENANCE}-{uuid.uuid4()}",
                    task_queue=c.TASK_QUEUE,
                    result_type=c.MaintenanceSummary,
                )
                return summary

    return asyncio.run(main())


ORDER = [
    c.ACT_DELETE_EXPIRED_SANDBOXES,
    c.ACT_START_UNSTARTED_DOCUMENTS,
    c.ACT_RESIGNAL_INCONSISTENT_DOCUMENTS,
    c.ACT_LOG_DAILY_STATS,
]


def test_runs_the_four_steps_in_order_and_summarises_them() -> None:
    calls: list[str] = []
    summary = run(calls)
    assert calls == ORDER
    assert summary == c.MaintenanceSummary(
        deleted_sandboxes=2,
        started_documents=3,
        resignalled_documents=4,
        abandoned_workflows=1,
        document_count=17,
        failed_steps=[],
    )


def test_a_failing_step_does_not_stop_the_others() -> None:
    calls: list[str] = []
    summary = run(calls, failing=c.ACT_START_UNSTARTED_DOCUMENTS)
    assert calls == ORDER  # PermanentError is not retried; the next steps still run
    assert summary.failed_steps == [c.ACT_START_UNSTARTED_DOCUMENTS]
    assert summary.started_documents == 0
    assert summary.deleted_sandboxes == 2
    assert summary.document_count == 17


def test_a_failing_resync_step_counts_nothing() -> None:
    calls: list[str] = []
    summary = run(calls, failing=c.ACT_RESIGNAL_INCONSISTENT_DOCUMENTS)
    assert calls == ORDER
    assert summary.resignalled_documents == 0
    assert summary.abandoned_workflows == 0
    assert summary.failed_steps == [c.ACT_RESIGNAL_INCONSISTENT_DOCUMENTS]

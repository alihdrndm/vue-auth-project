"""temporal_client.query_phase against Temporal's time-skipping test server."""

import asyncio
import uuid
from typing import cast

import pytest
from temporalio import workflow
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from eingang import temporal_client
from eingang.workflows import contracts as c


@workflow.defn(name="PhaseProbeWorkflow")
class PhaseProbeWorkflow:
    def __init__(self) -> None:
        self._done = False

    @workflow.signal(name="finish")
    def finish(self) -> None:
        self._done = True

    @workflow.query(name=c.QUERY_PHASE)
    def phase(self) -> str:
        return "needs_review"

    @workflow.run
    async def run(self) -> None:
        await workflow.wait_condition(lambda: self._done)


class EnvLoopThread:
    """Stands in for the client thread: hands out the test environment's client."""

    def __init__(self, client: Client) -> None:
        self._client = client

    async def client(self) -> Client:
        return self._client


def test_phase_of_running_finished_and_unknown_workflows() -> None:
    async def main() -> tuple[str | None, str | None, str | None]:
        async with await WorkflowEnvironment.start_time_skipping(
            data_converter=pydantic_data_converter
        ) as env:
            loop_thread = cast(temporal_client._LoopThread, EnvLoopThread(env.client))
            async with Worker(env.client, task_queue=c.TASK_QUEUE, workflows=[PhaseProbeWorkflow]):
                handle = await env.client.start_workflow(
                    "PhaseProbeWorkflow", id=f"probe-{uuid.uuid4()}", task_queue=c.TASK_QUEUE
                )
                running = await temporal_client._query_phase(loop_thread, handle.id)
                await handle.signal("finish")
                await handle.result()
                finished = await temporal_client._query_phase(loop_thread, handle.id)
                unknown = await temporal_client._query_phase(loop_thread, "invoice-unknown")
                return running, finished, unknown

    assert asyncio.run(main()) == ("needs_review", None, None)


def test_query_phase_raises_unavailable_when_temporal_does_not_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenLoopThread:
        forgotten = False

        def run(self, coroutine: object, timeout: float) -> object:
            if asyncio.iscoroutine(coroutine):
                coroutine.close()
            raise TimeoutError

        def forget_client(self) -> None:
            self.forgotten = True

    broken = BrokenLoopThread()
    monkeypatch.setattr(temporal_client, "_get_loop_thread", lambda: broken)
    with pytest.raises(temporal_client.TemporalUnavailableError):
        temporal_client.query_phase("invoice-1")
    assert broken.forgotten

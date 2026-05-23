"""Synchronous access to Temporal for the Django process.

Django views are synchronous. One background thread per process runs an asyncio
loop that owns the connected `temporalio.client.Client`, so views never create
event loops themselves. The client is created lazily and recreated after a failure.
"""

import asyncio
import threading
from collections.abc import Coroutine
from concurrent.futures import TimeoutError as FutureTimeoutError
from uuid import UUID

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.exceptions import WorkflowAlreadyStartedError

from eingang.config import get_settings
from eingang.workflows.contracts import (
    TASK_QUEUE,
    WF_PROCESS_INVOICE,
    ProcessInvoiceInput,
    process_invoice_workflow_id,
)


class _LoopThread:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="temporal-client", daemon=True
        )
        self._thread.start()
        self._client: Client | None = None

    def run[T](self, coroutine: Coroutine[object, object, T], timeout: float) -> T:
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            future.cancel()
            raise TimeoutError from None

    async def client(self) -> Client:
        if self._client is None:
            settings = get_settings()
            self._client = await Client.connect(
                settings.TEMPORAL_ADDRESS,
                namespace=settings.TEMPORAL_NAMESPACE,
                data_converter=pydantic_data_converter,
            )
        return self._client

    def forget_client(self) -> None:
        self._client = None


_lock = threading.Lock()
_loop_thread: _LoopThread | None = None


def _get_loop_thread() -> _LoopThread:
    global _loop_thread  # one loop thread per process, created on first use
    with _lock:
        if _loop_thread is None:
            _loop_thread = _LoopThread()
        return _loop_thread


async def _check_health(loop_thread: _LoopThread) -> bool:
    client = await loop_thread.client()
    return await client.service_client.check_health()


def is_healthy(timeout: float) -> bool:
    """True when the Temporal frontend answers its health check within `timeout` seconds."""
    loop_thread = _get_loop_thread()
    try:
        healthy = loop_thread.run(_check_health(loop_thread), timeout)
    except Exception:  # any failure means "not reachable"
        loop_thread.forget_client()
        return False
    if not healthy:
        loop_thread.forget_client()
    return healthy


START_TIMEOUT_SECONDS = 5.0


class TemporalUnavailableError(Exception):
    """Temporal did not accept the request; the caller stores the work and retries later."""


async def _start_processing(loop_thread: _LoopThread, document_id: UUID) -> None:
    client = await loop_thread.client()
    try:
        await client.start_workflow(
            WF_PROCESS_INVOICE,
            ProcessInvoiceInput(document_id=document_id),
            id=process_invoice_workflow_id(document_id),
            task_queue=TASK_QUEUE,
        )
    except WorkflowAlreadyStartedError:
        # Already running for this document: nothing to do (deterministic workflow IDs).
        return


def start_processing(document_id: UUID) -> None:
    """Start `ProcessInvoiceWorkflow` for a stored document, or raise TemporalUnavailableError."""
    loop_thread = _get_loop_thread()
    try:
        loop_thread.run(_start_processing(loop_thread, document_id), START_TIMEOUT_SECONDS)
    except Exception as error:  # any failure: the maintenance workflow starts it later
        loop_thread.forget_client()
        raise TemporalUnavailableError from error

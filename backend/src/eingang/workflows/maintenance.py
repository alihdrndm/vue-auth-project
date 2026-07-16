"""MaintenanceWorkflow: the daily clean-up run by schedule `daily-maintenance` (HANDOFF "Temporal").

Deterministic: it imports only the standard library, temporalio and the contracts module,
and calls activities by name. The four steps are independent, so one failing step is
logged and the others still run.
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

with workflow.unsafe.imports_passed_through():
    from eingang.workflows import contracts as c

# The default activity options of HANDOFF "Temporal conventions".
DEFAULT_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=5,
    non_retryable_error_types=[c.PERMANENT_ERROR_TYPE, c.BUDGET_EXCEEDED_ERROR_TYPE],
)
DEFAULT_TIMEOUT = timedelta(seconds=60)


def _cause_type(error: ActivityError) -> str | None:
    cause = error.cause
    return cause.type if isinstance(cause, ApplicationError) else None


@workflow.defn(name=c.WF_MAINTENANCE)
class MaintenanceWorkflow:
    def __init__(self) -> None:
        self._failed_steps: list[str] = []

    @workflow.run
    async def run(self) -> c.MaintenanceSummary:
        deleted = await self._count(c.ACT_DELETE_EXPIRED_SANDBOXES)
        started = await self._count(c.ACT_START_UNSTARTED_DOCUMENTS)
        resync = await self._step(c.ACT_RESIGNAL_INCONSISTENT_DOCUMENTS, c.ResyncSummary)
        if not isinstance(resync, c.ResyncSummary):
            resync = c.ResyncSummary()
        if resync.abandoned_workflows:
            workflow.logger.info(
                "Open documents without a running workflow: %d", resync.abandoned_workflows
            )
        documents = await self._count(c.ACT_LOG_DAILY_STATS)
        return c.MaintenanceSummary(
            deleted_sandboxes=deleted,
            started_documents=started,
            resignalled_documents=resync.resignalled_documents,
            abandoned_workflows=resync.abandoned_workflows,
            document_count=documents,
            failed_steps=list(self._failed_steps),
        )

    async def _step(self, name: str, result_type: type) -> object:
        """Run one activity; a failure is logged and recorded, never raised."""
        try:
            return await workflow.execute_activity(
                name,
                result_type=result_type,
                start_to_close_timeout=DEFAULT_TIMEOUT,
                retry_policy=DEFAULT_RETRY,
            )
        except ActivityError as error:
            workflow.logger.warning("Maintenance step %s failed: %s", name, _cause_type(error))
            self._failed_steps.append(name)
            return None

    async def _count(self, name: str) -> int:
        result = await self._step(name, int)
        return result if isinstance(result, int) else 0

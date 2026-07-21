"""Temporal schedules, created or updated by `ensure_schedules` (HANDOFF "Temporal workflows").

Every schedule uses overlap policy SKIP and starts its workflow under a short fixed action
ID, so its runs are named `<id>-<timestamp>`. Running the command twice leaves the same
schedules: an existing schedule is updated in place instead of failing.
"""

import logging
from datetime import timedelta

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleAlreadyRunningError,
    ScheduleIntervalSpec,
    ScheduleOverlapPolicy,
    SchedulePolicy,
    ScheduleSpec,
    ScheduleUpdate,
    ScheduleUpdateInput,
)
from temporalio.service import RPCError, RPCStatusCode

from eingang.config import Settings
from eingang.workflows import contracts as c

logger = logging.getLogger(__name__)

MAINTENANCE_CRON = "10 3 * * *"  # 03:10 UTC every day (schedules default to UTC)
MAILBOX_POLL_EVERY = timedelta(minutes=5)


def _schedule(workflow_name: str, action_id: str, spec: ScheduleSpec) -> Schedule:
    return Schedule(
        action=ScheduleActionStartWorkflow(workflow_name, id=action_id, task_queue=c.TASK_QUEUE),
        spec=spec,
        policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
    )


def maintenance_schedule() -> Schedule:
    return _schedule(
        c.WF_MAINTENANCE,
        c.SCHEDULE_ACTION_MAINTENANCE,
        ScheduleSpec(cron_expressions=[MAINTENANCE_CRON]),
    )


def mailbox_poll_schedule() -> Schedule:
    return _schedule(
        c.WF_MAILBOX_POLL,
        c.SCHEDULE_ACTION_MAILBOX_POLL,
        ScheduleSpec(intervals=[ScheduleIntervalSpec(every=MAILBOX_POLL_EVERY)]),
    )


def registered_workflow_names() -> set[str]:
    """Names of the workflows the worker runs; a schedule must not start an unknown one."""
    from temporalio import workflow

    from eingang.worker import registered_workflows

    names = (workflow._Definition.must_from_class(cls).name for cls in registered_workflows())
    return {name for name in names if name}


async def _create_or_update(client: Client, schedule_id: str, schedule: Schedule) -> None:
    try:
        await client.create_schedule(schedule_id, schedule)
    except ScheduleAlreadyRunningError:

        def replace(_current: ScheduleUpdateInput) -> ScheduleUpdate:
            return ScheduleUpdate(schedule=schedule)

        await client.get_schedule_handle(schedule_id).update(replace)
        logger.info("Updated schedule %s", schedule_id)
    else:
        logger.info("Created schedule %s", schedule_id)


async def _remove(client: Client, schedule_id: str) -> None:
    try:
        await client.get_schedule_handle(schedule_id).delete()
    except RPCError as error:
        if error.status != RPCStatusCode.NOT_FOUND:
            raise
    else:
        logger.info("Removed schedule %s", schedule_id)


async def ensure_schedules(client: Client, settings: Settings) -> list[str]:
    """Create or update every schedule; returns the IDs of the schedules that now exist."""
    await _create_or_update(client, c.SCHEDULE_DAILY_MAINTENANCE, maintenance_schedule())
    ensured = [c.SCHEDULE_DAILY_MAINTENANCE]
    mailbox_ready = c.WF_MAILBOX_POLL in registered_workflow_names()
    if settings.MAILBOX_ENABLED and mailbox_ready:
        await _create_or_update(client, c.SCHEDULE_MAILBOX_POLL, mailbox_poll_schedule())
        ensured.append(c.SCHEDULE_MAILBOX_POLL)
    else:
        if settings.MAILBOX_ENABLED:
            logger.warning(
                "Mailbox poll schedule skipped: the worker does not run %s", c.WF_MAILBOX_POLL
            )
        # Created only when MAILBOX_ENABLED=true; an earlier one is removed.
        await _remove(client, c.SCHEDULE_MAILBOX_POLL)
    return ensured

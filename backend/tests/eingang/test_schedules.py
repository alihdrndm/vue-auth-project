"""ensure_schedules against a recording fake client.

Temporal's time-skipping test server does not implement schedules, so the fake stands in
for the client: it keeps the schedules it holds and raises like the real server does.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import cast

import pytest
from django.core.management import call_command
from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleAlreadyRunningError,
    ScheduleOverlapPolicy,
    ScheduleUpdate,
    ScheduleUpdateInput,
)
from temporalio.service import RPCError, RPCStatusCode

from eingang import schedules
from eingang.config import Settings
from eingang.management.commands import ensure_schedules as command
from eingang.workflows import contracts as c

UpdateFn = object  # the updater callback; called with a stand-in input


@dataclass
class FakeHandle:
    client: "FakeScheduleClient"
    id: str

    async def update(self, updater: UpdateFn) -> None:
        assert callable(updater)
        current = cast(ScheduleUpdateInput, None)  # the updater ignores the current schedule
        result = updater(current)
        assert isinstance(result, ScheduleUpdate)
        self.client.calls.append(("update", self.id))
        self.client.schedules[self.id] = result.schedule

    async def delete(self) -> None:
        if self.id not in self.client.schedules:
            raise RPCError("not found", RPCStatusCode.NOT_FOUND, b"")
        self.client.calls.append(("delete", self.id))
        del self.client.schedules[self.id]


@dataclass
class FakeScheduleClient:
    schedules: dict[str, Schedule] = field(default_factory=dict)
    calls: list[tuple[str, str]] = field(default_factory=list)

    async def create_schedule(self, id: str, schedule: Schedule) -> FakeHandle:
        if id in self.schedules:
            raise ScheduleAlreadyRunningError
        self.calls.append(("create", id))
        self.schedules[id] = schedule
        return FakeHandle(self, id)

    def get_schedule_handle(self, id: str) -> FakeHandle:
        return FakeHandle(self, id)


def ensure(fake: FakeScheduleClient, *, mailbox: bool = False) -> list[str]:
    settings = Settings(
        _env_file=None,
        MAILBOX_ENABLED=mailbox,
        MAILBOX_HOST="imap.example.invalid",
        MAILBOX_USER="inbox@example.invalid",
        MAILBOX_PASSWORD="not-a-real-password",  # noqa: S106 - test value
        MAILBOX_ORG_SLUG="holzwerk-brandt",
    )
    return asyncio.run(schedules.ensure_schedules(cast(Client, fake), settings))


def _action(schedule: Schedule) -> ScheduleActionStartWorkflow:
    action = schedule.action
    assert isinstance(action, ScheduleActionStartWorkflow)
    return action


def test_daily_maintenance_runs_at_0310_utc_and_skips_overlaps() -> None:
    fake = FakeScheduleClient()
    assert ensure(fake) == [c.SCHEDULE_DAILY_MAINTENANCE]
    schedule = fake.schedules[c.SCHEDULE_DAILY_MAINTENANCE]
    assert schedule.spec.cron_expressions == ["10 3 * * *"]
    assert schedule.spec.time_zone_name in (None, "UTC")
    assert schedule.policy.overlap == ScheduleOverlapPolicy.SKIP
    action = _action(schedule)
    assert action.workflow == c.WF_MAINTENANCE
    assert action.id == c.SCHEDULE_ACTION_MAINTENANCE
    assert action.task_queue == "eingang-main"


def test_running_twice_updates_instead_of_failing() -> None:
    fake = FakeScheduleClient()
    ensure(fake)
    ensure(fake)
    assert fake.calls == [
        ("create", c.SCHEDULE_DAILY_MAINTENANCE),
        ("update", c.SCHEDULE_DAILY_MAINTENANCE),
    ]
    assert list(fake.schedules) == [c.SCHEDULE_DAILY_MAINTENANCE]
    assert fake.schedules[c.SCHEDULE_DAILY_MAINTENANCE].policy.overlap == (
        ScheduleOverlapPolicy.SKIP
    )


def test_mailbox_schedule_is_skipped_while_the_worker_lacks_its_workflow(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeScheduleClient()
    with caplog.at_level(logging.WARNING, logger="eingang.schedules"):
        assert ensure(fake, mailbox=True) == [c.SCHEDULE_DAILY_MAINTENANCE]
    assert c.SCHEDULE_MAILBOX_POLL not in fake.schedules
    assert "Mailbox poll schedule skipped" in caplog.text


def test_mailbox_schedule_follows_mailbox_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        schedules, "registered_workflow_names", lambda: {c.WF_MAINTENANCE, c.WF_MAILBOX_POLL}
    )
    fake = FakeScheduleClient()
    assert ensure(fake, mailbox=True) == [c.SCHEDULE_DAILY_MAINTENANCE, c.SCHEDULE_MAILBOX_POLL]
    schedule = fake.schedules[c.SCHEDULE_MAILBOX_POLL]
    assert [spec.every for spec in schedule.spec.intervals] == [timedelta(minutes=5)]
    assert schedule.policy.overlap == ScheduleOverlapPolicy.SKIP
    action = _action(schedule)
    assert (action.workflow, action.id) == (c.WF_MAILBOX_POLL, c.SCHEDULE_ACTION_MAILBOX_POLL)

    ensure(fake, mailbox=False)  # turned off again: the schedule is removed
    assert c.SCHEDULE_MAILBOX_POLL not in fake.schedules
    assert ("delete", c.SCHEDULE_MAILBOX_POLL) in fake.calls


def test_command_connects_and_reports_each_schedule(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = FakeScheduleClient()

    class FakeClientClass:
        @staticmethod
        async def connect(*args: object, **kwargs: object) -> FakeScheduleClient:
            return fake

    monkeypatch.setattr(command, "Client", FakeClientClass)
    call_command("ensure_schedules")
    assert c.SCHEDULE_DAILY_MAINTENANCE in fake.schedules
    assert f"Schedule '{c.SCHEDULE_DAILY_MAINTENANCE}' is up to date." in capsys.readouterr().out

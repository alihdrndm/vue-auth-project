import logging

import pytest
from temporalio import activity, workflow

from eingang import worker
from eingang.workflows import contracts as c


def test_worker_registers_every_workflow_and_every_activity_they_call() -> None:
    workflows = {
        workflow._Definition.must_from_class(cls).name for cls in worker.registered_workflows()
    }
    activities = {
        activity._Definition.must_from_callable(fn).name for fn in worker.registered_activities()
    }
    assert workflows == {c.WF_PROCESS_INVOICE, c.WF_MAINTENANCE, c.WF_MAILBOX_POLL}
    every_activity_name = {
        value
        for name, value in vars(c).items()
        if name.startswith("ACT_") and isinstance(value, str)
    }
    assert activities == every_activity_name
    assert worker.TASK_QUEUE == "eingang-main"


def test_worker_compiles_the_stylesheets_at_start_up(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="eingang.worker"):
        worker.prepare_stylesheets()
    assert "Stylesheets compiled" in caplog.text

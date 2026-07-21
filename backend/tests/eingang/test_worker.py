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
    assert workflows == {c.WF_PROCESS_INVOICE, c.WF_MAINTENANCE}
    assert {
        c.ACT_BEGIN_PROCESSING,
        c.ACT_DETECT_DOCUMENT,
        c.ACT_VALIDATE_DOCUMENT,
        c.ACT_RUN_CHECKS,
        c.ACT_FINISH_PROCESSING,
        c.ACT_READ_STATUS,
        c.ACT_SEND_REMINDER,
        c.ACT_MARK_FAILED,
        c.ACT_DELETE_EXPIRED_SANDBOXES,
        c.ACT_START_UNSTARTED_DOCUMENTS,
        c.ACT_RESIGNAL_INCONSISTENT_DOCUMENTS,
        c.ACT_LOG_DAILY_STATS,
    } <= activities
    assert worker.TASK_QUEUE == "eingang-main"


def test_worker_compiles_the_stylesheets_at_start_up(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="eingang.worker"):
        worker.prepare_stylesheets()
    assert "Stylesheets compiled" in caplog.text

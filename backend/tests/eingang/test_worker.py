import logging

import pytest
from temporalio import activity, workflow

from eingang import worker
from eingang.workflows import contracts as c


def test_worker_registers_the_processing_workflow_and_every_activity_it_calls() -> None:
    workflows = {
        workflow._Definition.must_from_class(cls).name for cls in worker.registered_workflows()
    }
    activities = {
        activity._Definition.must_from_callable(fn).name for fn in worker.registered_activities()
    }
    assert workflows == {c.WF_PROCESS_INVOICE}
    assert {
        c.ACT_BEGIN_PROCESSING,
        c.ACT_DETECT_DOCUMENT,
        c.ACT_VALIDATE_DOCUMENT,
        c.ACT_RUN_CHECKS,
        c.ACT_FINISH_PROCESSING,
        c.ACT_READ_STATUS,
        c.ACT_SEND_REMINDER,
        c.ACT_MARK_FAILED,
    } <= activities
    assert worker.TASK_QUEUE == "eingang-main"


def test_worker_compiles_the_stylesheets_at_start_up(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="eingang.worker"):
        worker.prepare_stylesheets()
    assert "Stylesheets compiled" in caplog.text

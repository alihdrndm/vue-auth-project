import asyncio
import logging

import pytest

from eingang import worker


def test_worker_does_not_start_without_registered_workflows_or_activities(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="eingang.worker"):
        asyncio.run(worker.run())
    assert "not started" in caplog.text
    assert worker.TASK_QUEUE == "eingang-main"

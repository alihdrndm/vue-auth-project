"""Temporal worker entry point: `python -m eingang.worker`."""

import asyncio
import logging
import os
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

TASK_QUEUE = "eingang-main"

logger = logging.getLogger("eingang.worker")


def registered_workflows() -> Sequence[type]:
    from eingang.workflows.process_invoice import ProcessInvoiceWorkflow

    return (ProcessInvoiceWorkflow,)


def registered_activities() -> Sequence[Callable[..., object]]:
    # Activities touch the database, so they are imported after `django.setup()`.
    from invoices.activities import PROCESS_INVOICE_ACTIVITIES

    return tuple(PROCESS_INVOICE_ACTIVITIES)


async def run() -> None:
    from eingang.config import get_settings

    settings = get_settings()
    workflows = registered_workflows()
    activities = registered_activities()
    client = await Client.connect(
        settings.TEMPORAL_ADDRESS,
        namespace=settings.TEMPORAL_NAMESPACE,
        data_converter=pydantic_data_converter,
    )
    with ThreadPoolExecutor(max_workers=4) as executor:
        worker = Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=workflows,
            activities=activities,
            activity_executor=executor,
            max_concurrent_activities=4,
        )
        await worker.run()


def main() -> None:
    # The process entry point names its settings module; this is not configuration.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eingang.settings")
    import django

    django.setup()
    prepare_stylesheets()
    asyncio.run(run())


def prepare_stylesheets() -> None:
    """Compile the Schematron and visualisation stylesheets once, before the first document."""
    from einvoice import validate, visualize

    started = time.perf_counter()
    validate.warm_up()
    visualize.warm_up()
    logger.info("Stylesheets compiled in %.1f s", time.perf_counter() - started)


if __name__ == "__main__":
    main()

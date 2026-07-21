"""`uv run poe ensure-schedules`: create or update every Temporal schedule (idempotent)."""

import asyncio
from typing import Any

from django.core.management.base import BaseCommand
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from eingang.config import get_settings
from eingang.schedules import ensure_schedules


async def _ensure() -> list[str]:
    settings = get_settings()
    client = await Client.connect(
        settings.TEMPORAL_ADDRESS,
        namespace=settings.TEMPORAL_NAMESPACE,
        data_converter=pydantic_data_converter,
    )
    return await ensure_schedules(client, settings)


class Command(BaseCommand):
    help = "Create or update the Temporal schedules (daily maintenance, mailbox poll)."

    def handle(self, *args: Any, **options: Any) -> None:  # boundary: django command options
        for schedule_id in asyncio.run(_ensure()):
            self.stdout.write(f"Schedule '{schedule_id}' is up to date.")

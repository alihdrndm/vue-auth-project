"""`uv run poe llm-spend`: this database's LLM ledger total, for LLM_SPENT_ELSEWHERE_USD."""

from typing import Any

from django.core.management.base import BaseCommand

from llm.client import spent_total
from llm.models import LlmCall


class Command(BaseCommand):
    help = "Print the total cost of every LLM call recorded in this database (USD)."

    def handle(self, *args: Any, **options: Any) -> None:  # boundary: django command options
        calls = LlmCall.objects.count()
        self.stdout.write(f"{spent_total():.6f}")
        self.stderr.write(
            f"{calls} ledger rows. Set LLM_SPENT_ELSEWHERE_USD in the other database."
        )

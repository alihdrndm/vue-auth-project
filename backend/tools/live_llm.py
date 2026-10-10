"""Shared parts of the tools that make live LLM calls (`llm-smoke`, `precompute-samples`).

Both spend real money, so both refuse to run while the LLM is switched off, print the
model, its prices and the estimated maximum cost first, and ask for an explicit `yes`
(HANDOFF "When you may make live calls"). Every call goes through `llm.client.call`, so it
is budgeted, cached and written to the ledger like any other.
"""

import os
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
SAMPLES_DIR = BACKEND_DIR.parent / "samples"
sys.path.insert(0, str(BACKEND_DIR / "src"))
# The process entry point names its settings module; this is not configuration.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eingang.settings")

import django  # noqa: E402 - after the path set-up above
from django.apps import apps  # noqa: E402

if not apps.ready:
    django.setup()

from pydantic import BaseModel  # noqa: E402

from eingang.config import Settings, get_settings  # noqa: E402
from eingang.temporal_errors import BudgetExceededError, PermanentError  # noqa: E402
from llm import budget, client  # noqa: E402
from llm.models import LlmCall  # noqa: E402

Ask = Callable[[str], str]


@dataclass(frozen=True)
class Outcome[T: BaseModel]:
    """One finished call: its parsed answer and its ledger row."""

    answer: T
    row: LlmCall


def enabled_settings() -> Settings | None:
    """The settings when live calls may run; None (with the reason printed) otherwise.

    Invalid OpenAI settings make `get_settings` print every problem and exit.
    """
    settings = get_settings()
    if not settings.LLM_ENABLED:
        print(
            "Refusing to run: LLM_ENABLED is not true. These calls spend real money; "
            "switch the LLM on only for this run.",
            file=sys.stderr,
        )
        return None
    return settings


def estimate(settings: Settings, requests: Sequence[client.AnyRequest]) -> Decimal:
    """The deliberately high estimate of every request, as the budget check computes it."""
    prices = budget.Prices.from_settings(settings)
    return sum(
        (
            budget.estimate(prices, request.prompt.text + request.data, request.max_output_tokens)
            for request in requests
        ),
        Decimal(0),
    )


def confirm(
    settings: Settings,
    requests: Sequence[client.AnyRequest],
    *,
    assume_yes: bool,
    ask: Ask = input,
) -> bool:
    """Print what the run will cost at most, then ask for `yes` unless `--yes` was given."""
    print(f"Model: {settings.OPENAI_MODEL}")
    print(f"Reasoning effort: {settings.OPENAI_REASONING_EFFORT or '(not sent)'}")
    print(
        "Prices (USD per million tokens): "
        f"input {settings.OPENAI_PRICE_INPUT_PER_MTOK}, "
        f"cached input {settings.OPENAI_PRICE_CACHED_INPUT_PER_MTOK}, "
        f"output {settings.OPENAI_PRICE_OUTPUT_PER_MTOK}"
    )
    for request in requests:
        print(
            f"  {request.purpose:<8} {request.prompt.label:<20} "
            f"max_output_tokens {request.max_output_tokens}, "
            f"estimate {estimate(settings, [request]):.6f} USD"
        )
    print(f"Estimated maximum cost: {estimate(settings, requests):.6f} USD")
    print("(Cached requests cost nothing; the estimate assumes none are cached.)")
    if assume_yes:
        return True
    try:
        answer = ask("Type yes to make these calls: ")
    except EOFError:
        answer = ""
    if answer.strip().lower() != "yes":
        print("Aborted: nothing was called.")
        return False
    return True


class Caller:
    """Makes calls through the one LLM door and keeps the ledger rows they wrote."""

    def __init__(self) -> None:
        self._seen = set(LlmCall.objects.values_list("id", flat=True))
        self.rows: list[LlmCall] = []

    def call[T: BaseModel](self, request: client.Request[T]) -> Outcome[T] | str:
        """The answer and its ledger row, or a printable reason why there is none."""
        try:
            answer = client.call(request)
        except BudgetExceededError as error:
            self._collect()
            return f"refused by the budget ({error})"
        except PermanentError as error:
            self._collect()
            return (
                f"{error} The response was not 'completed' (for example because "
                f"max_output_tokens={request.max_output_tokens} was reached) or did not parse; "
                "its cost is on the ledger."
            )
        except Exception as error:  # any SDK failure is reported, not hidden
            self._collect()
            return f"the call failed: {type(error).__name__}: {error}"
        rows = self._collect()
        return Outcome(answer=answer, row=rows[-1])

    def _collect(self) -> list[LlmCall]:
        fresh = list(LlmCall.objects.exclude(id__in=self._seen).order_by("created_at"))
        self._seen.update(row.id for row in fresh)
        self.rows += fresh
        return fresh

    def spent(self) -> Decimal:
        return sum((row.cost for row in self.rows), Decimal(0))


def report_cost(caller: Caller) -> None:
    print(f"Actual cost of this run: {caller.spent():.6f} USD ({len(caller.rows)} ledger rows)")
    print(f"Ledger total of this database: {client.spent_total():.6f} USD")

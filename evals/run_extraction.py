"""Run one extraction system over the dataset and publish its scores (HANDOFF "Evaluation").

`uv run poe eval-baseline` runs the regex baseline (free). `uv run poe eval-llm` runs the
LLM through the application's one LLM door: it prints the estimate, asks for `yes`, stops
before `EVAL_BUDGET_USD` would be exceeded, and allows at most two live runs per prompt
version (cached answers make a rerun of finished documents free).
"""

import argparse
import dataclasses
import json
import math
import sys
import time
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from einvoice.model import CanonicalInvoice
from evals import DATA_DIR, metrics, setup_django
from evals.baseline_regex import extract as regex_extract
from evals.build_dataset import DatasetDocument, load_documents, load_manifest
from evals.report import load_latest, update_latest, write_run_report
from evals.schema import CriticalCorrect, Dataset, FieldScore, RunResult

RUNS_FILE = DATA_DIR / "llm-runs.json"  # live runs per prompt version (committed)
MAX_LIVE_RUNS = 2
BASELINE_ID = "regex-baseline"
# Invoice columns (as the LLM extraction stores them) for each scored field.
COLUMNS = {
    "invoice_number": "invoice_number", "issue_date": "issue_date", "due_date": "due_date",
    "currency": "currency", "seller.name": "seller_name", "seller.vat_id": "seller_vat_id",
    "payee_iban": "payee_iban", "buyer.name": "buyer_name", "net_total": "net_total",
    "tax_total": "tax_total", "gross_total": "gross_total", "payable_amount": "payable_amount",
}  # fmt: skip


def _text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def flatten(truth: CanonicalInvoice) -> metrics.Values:
    """The scored fields of the ground truth, as strings (dates ISO, amounts as written)."""
    parties = {"seller": truth.seller, "buyer": truth.buyer}
    values: metrics.Values = {}
    for field in metrics.FIELDS:
        if "." in field:
            party, attribute = field.split(".")
            values[field] = _text(getattr(parties[party], attribute))
        else:
            values[field] = _text(getattr(truth, field))
    return values


@dataclasses.dataclass
class Outcome:
    predictions: list[metrics.Values]
    truths: list[metrics.Values]
    latencies_ms: list[float]
    cost: Decimal = Decimal(0)
    stopped: str | None = None  # why the run ended early


def run_baseline(documents: Iterable[DatasetDocument]) -> Outcome:
    outcome = Outcome([], [], [])
    for document in documents:
        started = time.perf_counter()
        outcome.predictions.append(regex_extract(document.text))
        outcome.latencies_ms.append((time.perf_counter() - started) * 1000)
        outcome.truths.append(flatten(document.truth))
    return outcome


# --- the LLM system ---------------------------------------------------------------------


def estimate(documents: list[DatasetDocument], prompt_chars: int, prices: object) -> Decimal:
    """HANDOFF: sum of ceil((text_chars + prompt_chars) / 3) x input + docs x 2,500 x output."""
    from llm.budget import MILLION, Prices
    from llm.requests import EXTRACT_MAX_OUTPUT_TOKENS

    assert isinstance(prices, Prices)  # noqa: S101 - narrowing the lazily imported type
    input_tokens = sum(math.ceil((len(doc.text) + prompt_chars) / 3) for doc in documents)
    output_tokens = len(documents) * EXTRACT_MAX_OUTPUT_TOKENS
    return (input_tokens * prices.input + output_tokens * prices.output) / MILLION


def live_runs() -> dict[str, int]:
    if not RUNS_FILE.is_file():
        return {}
    runs: dict[str, int] = json.loads(RUNS_FILE.read_text(encoding="utf-8"))
    return runs


def record_live_run(prompt_version: str) -> None:
    runs = live_runs()
    runs[prompt_version] = runs.get(prompt_version, 0) + 1
    RUNS_FILE.write_text(json.dumps(runs, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_llm(
    documents: list[DatasetDocument], budget_usd: Decimal, ask: Callable[[str], str] = input
) -> tuple[Outcome, str, str]:
    """(outcome, model, prompt version). Each document is one budgeted, cached, ledgered call."""
    from eingang.config import get_settings
    from eingang.temporal_errors import BudgetExceededError
    from invoices.extraction import post_process
    from llm import budget, client
    from llm.requests import extraction_request

    settings = get_settings()
    if not settings.LLM_ENABLED:
        raise SystemExit("eval-llm: LLM_ENABLED is not true; refusing to spend money.")
    prompt = extraction_request("").prompt
    runs = live_runs().get(prompt.label, 0)
    if runs >= MAX_LIVE_RUNS:
        raise SystemExit(
            f"eval-llm: {prompt.label} already had {runs} live runs; a third needs the "
            "owner's explicit yes with the reason (pass --third-run-approved)."
        )
    prices = budget.Prices.from_settings(settings)
    estimated = estimate(documents, len(prompt.text), prices)
    print(f"Model {settings.OPENAI_MODEL}, prompt {prompt.label}, {len(documents)} documents.")
    print(f"Estimated maximum cost: ${estimated:.4f} (cap EVAL_BUDGET_USD ${budget_usd}).")
    if ask("Type yes to run: ").strip().lower() != "yes":
        raise SystemExit("eval-llm: not confirmed; nothing was spent.")
    record_live_run(prompt.label)
    outcome = Outcome([], [], [])
    start_total = budget.spent()
    for document in documents:
        request = dataclasses.replace(extraction_request(document.text), purpose="eval")
        next_call = budget.estimate(prices, prompt.text + request.data, request.max_output_tokens)
        if outcome.cost + next_call > budget_usd:
            outcome.stopped = f"EVAL_BUDGET_USD reached after {len(outcome.predictions)} documents"
            break
        started = time.perf_counter()
        try:
            answer = client.call(request)
            columns = post_process(answer, document.text).columns
            predicted = {field: _text(columns.get(column)) for field, column in COLUMNS.items()}
        except BudgetExceededError as error:
            outcome.stopped = f"refused: {error.reason}"
            break
        except Exception:
            predicted = dict.fromkeys(metrics.FIELDS)
        outcome.latencies_ms.append((time.perf_counter() - started) * 1000)
        outcome.predictions.append(predicted)
        outcome.truths.append(flatten(document.truth))
        outcome.cost = budget.spent() - start_total
    return outcome, settings.OPENAI_MODEL, prompt.label


# --- publishing ---------------------------------------------------------------------------


def result_of(
    system_id: str, outcome: Outcome, dataset: Dataset, model: str | None, prompt: str | None
) -> RunResult:
    scores = metrics.score(outcome.truths, outcome.predictions)
    scored = len(outcome.predictions)
    return RunResult(
        id=system_id,
        model=model,
        prompt_version=prompt,
        critical_correct=CriticalCorrect(**dataclasses.asdict(scores.critical)),
        fields={
            name: FieldScore(**dataclasses.asdict(score)) for name, score in scores.fields.items()
        },
        cost_usd=outcome.cost,
        usd_per_doc=(outcome.cost / scored).quantize(Decimal("0.000001")) if scored else Decimal(0),
        latency_p50_ms=metrics.percentile(outcome.latencies_ms, 0.5) or 0.0,
        latency_p95_ms=metrics.percentile(outcome.latencies_ms, 0.95) or 0.0,
        generated_at=datetime.now(UTC),
        dataset=dataset,
        documents=scored,
    )


def publish(result: RunResult) -> tuple[Path, Path]:
    update_latest(result)
    return write_run_report(result, latest=load_latest())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("system", choices=["baseline", "llm"])
    parser.add_argument("--yes", action="store_true", help="skip the interactive confirmation")
    parser.add_argument("--third-run-approved", action="store_true")
    options = parser.parse_args(argv)
    setup_django()
    manifest = load_manifest()
    dataset = Dataset(
        name=manifest.name, documents=manifest.documents, corpus_commit=manifest.corpus_commit
    )
    documents = list(load_documents())
    if options.system == "baseline":
        result = result_of(BASELINE_ID, run_baseline(documents), dataset, None, None)
        stopped = None
    else:
        from eingang.config import get_settings

        if options.third_run_approved:
            global MAX_LIVE_RUNS
            MAX_LIVE_RUNS = sys.maxsize
        outcome, model, prompt = run_llm(
            documents,
            get_settings().EVAL_BUDGET_USD,
            ask=(lambda _question: "yes") if options.yes else input,
        )
        result = result_of(f"llm:{model}", outcome, dataset, model, prompt)
        stopped = outcome.stopped
    markdown, _data = publish(result)
    print(
        f"{result.id}: critical fields correct {result.critical_correct.value:.1%} "
        f"(95% CI {result.critical_correct.ci_low:.1%}-{result.critical_correct.ci_high:.1%}) "
        f"on {result.documents} documents; cost ${result.cost_usd}. Report: {markdown.name}"
    )
    if stopped:
        print(f"Stopped early: {stopped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

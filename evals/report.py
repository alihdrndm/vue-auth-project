"""Write a run's report and keep `evals/latest.json` up to date (HANDOFF "Outputs").

- `write_run_report` writes `evals/reports/<YYYY-MM-DD>-<system>.md` and `.json` from a
  `RunResult`. The system ID is made file-name safe (`llm:gpt-x` becomes `llm-gpt-x`).
- `update_latest` replaces the entry of the run's system in `evals/latest.json`, keeps the
  other systems, and replaces the parity section when one is given.

Nothing here computes a metric; the numbers come from the run. Files are written with LF line
endings and validated against `LatestReport` / `RunResult` on every read and write.
"""

import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from evals import LATEST_PATH, REPORTS_DIR
from evals.schema import SCORED_FIELDS, LatestReport, Parity, RunResult, SystemResult

EVALS_DOC = "../../docs/EVALS.md"  # relative to evals/reports/
MISSING = "n/a"


class ReportError(Exception):
    """latest.json cannot take this update."""


# --- formatting -----------------------------------------------------------------------------


def system_slug(system_id: str) -> str:
    """The system ID as a file-name part: anything but letters, digits, `.`, `_`, `-` is `-`."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", system_id).strip("-")


def _percent(rate: float | None) -> str:
    return MISSING if rate is None else f"{rate * 100:.1f}%"


def _usd(amount: Decimal, places: int) -> str:
    return f"${amount:.{places}f}"


def _ms(value: float) -> str:
    return f"{value:,.0f} ms"


def _row(cells: Sequence[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _table(header: Sequence[str], rows: Sequence[Sequence[str]], align: str) -> list[str]:
    """A Markdown table; `align` has one character per column, `l` or `r`."""
    rule = ["---:" if side == "r" else "---" for side in align]
    return [_row(header), _row(rule), *(_row(row) for row in rows)]


def _critical(system: SystemResult) -> str:
    critical = system.critical_correct
    return (
        f"{_percent(critical.value)} ({_percent(critical.ci_low)} to {_percent(critical.ci_high)})"
    )


def headline_table(systems: Sequence[SystemResult]) -> list[str]:
    header = [
        "System",
        "Critical fields correct (95% CI)",
        "Cost",
        "Per document",
        "Latency p50",
        "Latency p95",
    ]
    rows = [
        [
            f"`{system.id}`",
            _critical(system),
            _usd(system.cost_usd, 4),
            _usd(system.usd_per_doc, 6),
            _ms(system.latency_p50_ms),
            _ms(system.latency_p95_ms),
        ]
        for system in systems
    ]
    return _table(header, rows, "lrrrrr")


def field_table(system: SystemResult) -> list[str]:
    rows = []
    for field in SCORED_FIELDS:
        score = system.fields.get(field)
        rows.append(
            [
                f"`{field}`",
                _percent(score.accuracy if score else None),
                _percent(score.hallucination if score else None),
                _percent(score.abstention if score else None),
            ]
        )
    return _table(["Field", "Accuracy", "Hallucination", "Abstention"], rows, "lrrr")


def parity_table(parity: Parity) -> list[str]:
    rows = [
        ["Files compared", str(parity.files)],
        ["Excluded", str(parity.excluded)],
        ["Verdict agreement", _percent(parity.verdict_agreement)],
        ["Fatal rule set agreement", _percent(parity.rule_set_agreement)],
    ]
    return _table(["Validation parity", ""], rows, "lr")


def render_markdown(result: RunResult, latest: LatestReport | None = None) -> str:
    """The run's report. With `latest`, the headline compares every system in it."""
    run = result.system()
    others = [system for system in latest.systems if system.id != run.id] if latest else []
    dataset = result.dataset
    lines = [
        f"# Extraction accuracy: `{run.id}`",
        "",
        f"Run of {result.generated_at.astimezone(UTC):%Y-%m-%d %H:%M} UTC on the dataset "
        f"`{dataset.name}` ({dataset.documents} documents, corpus commit "
        f"`{dataset.corpus_commit[:12]}`); {result.documents} documents scored.",
    ]
    details = [
        f"model `{run.model}`" if run.model else None,
        f"prompt `{run.prompt_version}`" if run.prompt_version else None,
    ]
    if any(details):
        lines.append("System: " + ", ".join(detail for detail in details if detail) + ".")
    lines += [
        "",
        "## Headline",
        "",
        *headline_table([run, *others]),
        "",
        "A document's critical fields are correct when its invoice number, issue date, gross "
        "total and (if the invoice has one) payee IBAN are all correct. The interval is a 95% "
        "bootstrap confidence interval.",
        "",
        "## Per field",
        "",
        *field_table(run),
        "",
        "Accuracy counts the documents whose truth has the field; hallucination, a value read "
        "where the truth has none; abstention, no value where the truth has one. "
        f"`{MISSING}`: the rate has no documents to count.",
    ]
    if latest and latest.parity:
        lines += ["", "## Validation parity", "", *parity_table(latest.parity)]
    lines += [
        "",
        "## Method",
        "",
        f"Dataset, scoring rules, statistics and limits: [docs/EVALS.md]({EVALS_DOC}).",
    ]
    return "\n".join(lines) + "\n"


# --- files ----------------------------------------------------------------------------------


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _json(document: dict[str, object]) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def report_stem(result: RunResult) -> str:
    return f"{result.generated_at.astimezone(UTC):%Y-%m-%d}-{system_slug(result.id)}"


def write_run_report(
    result: RunResult, reports_dir: Path = REPORTS_DIR, latest: LatestReport | None = None
) -> tuple[Path, Path]:
    """Write the run's `.md` and `.json` report; returns both paths."""
    stem = report_stem(result)
    markdown, data = reports_dir / f"{stem}.md", reports_dir / f"{stem}.json"
    _write(markdown, render_markdown(result, latest))
    _write(data, _json(result.model_dump(mode="json", exclude_none=True)))
    return markdown, data


def load_run_result(path: Path) -> RunResult:
    return RunResult.model_validate_json(path.read_bytes())


def load_latest(path: Path = LATEST_PATH) -> LatestReport | None:
    if not path.is_file():
        return None
    return LatestReport.model_validate_json(path.read_bytes())


def write_latest(report: LatestReport, path: Path = LATEST_PATH) -> None:
    # A round trip through the model checks the whole document, not only its parts.
    document = LatestReport.model_validate(report.model_dump()).model_dump(
        mode="json", exclude_none=True
    )
    _write(path, _json(document))


def merge_latest(
    existing: LatestReport | None,
    result: RunResult | None = None,
    parity: Parity | None = None,
    *,
    now: datetime | None = None,
) -> LatestReport:
    """The new latest report: the run's system replaced or added, parity replaced if given."""
    if result is None and parity is None:
        raise ReportError("nothing to update: pass a run result, parity, or both")
    if result is not None:
        dataset = result.dataset
        if existing is not None and existing.dataset != dataset:
            raise ReportError(
                f"latest.json holds results for another dataset ({existing.dataset}); "
                "run every system again on the new dataset, starting from an empty latest.json"
            )
    elif existing is not None:
        dataset = existing.dataset
    else:
        raise ReportError("latest.json does not exist yet; write a run result first")
    systems = list(existing.systems) if existing else []
    if result is not None:
        entry = result.system()
        index = next((i for i, system in enumerate(systems) if system.id == entry.id), None)
        if index is None:
            systems.append(entry)
        else:
            systems[index] = entry
    return LatestReport(
        generated_at=now or datetime.now(UTC),
        dataset=dataset,
        systems=systems,
        parity=parity if parity is not None else (existing.parity if existing else None),
    )


def update_latest(
    result: RunResult | None = None,
    parity: Parity | None = None,
    *,
    path: Path = LATEST_PATH,
    now: datetime | None = None,
) -> LatestReport:
    """Merge a run and/or parity into `latest.json` on disk and return the new report."""
    report = merge_latest(load_latest(path), result, parity, now=now)
    write_latest(report, path)
    return report

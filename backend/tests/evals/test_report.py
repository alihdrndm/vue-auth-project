"""report: the per-run Markdown/JSON report and the latest.json merge."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from evals.report import (
    ReportError,
    load_latest,
    load_run_result,
    merge_latest,
    render_markdown,
    system_slug,
    update_latest,
    write_run_report,
)
from evals.schema import (
    SCORED_FIELDS,
    CriticalCorrect,
    Dataset,
    FieldScore,
    LatestReport,
    Parity,
    RunResult,
)
from pydantic import ValidationError

DATASET = Dataset(name="zugferd-corpus-hybrid-cii", documents=104, corpus_commit="d891458e9822e3")
WHEN = datetime(2026, 10, 9, 13, 2, 11, tzinfo=UTC)
PARITY = Parity(files=180, excluded=12, verdict_agreement=1.0, rule_set_agreement=0.99)


def run(system_id: str = "llm:gpt-x", value: float = 0.8, **overrides: object) -> RunResult:
    fields = {
        field: FieldScore(accuracy=0.9, hallucination=0.05, abstention=0.1)
        for field in SCORED_FIELDS
    }
    fields["currency"] = FieldScore(accuracy=1.0, abstention=0.0)  # always present in the truth
    values: dict[str, object] = {
        "id": system_id,
        "model": "gpt-x",
        "prompt_version": "extract_invoice.v1",
        "critical_correct": CriticalCorrect(value=value, ci_low=value - 0.08, ci_high=value + 0.07),
        "fields": fields,
        "cost_usd": Decimal("0.123456"),
        "usd_per_doc": Decimal("0.001187"),
        "latency_p50_ms": 1830.4,
        "latency_p95_ms": 4210.0,
        "generated_at": WHEN,
        "dataset": DATASET,
        "documents": 104,
    }
    values.update(overrides)
    return RunResult.model_validate(values)


def regex_run() -> RunResult:
    return run(
        "regex-baseline",
        critical_correct=CriticalCorrect(value=0.4, ci_low=0.31, ci_high=0.5),
        model=None,
        prompt_version=None,
        cost_usd=Decimal(0),
        usd_per_doc=Decimal(0),
        latency_p50_ms=2.0,
        latency_p95_ms=5.0,
    )


# --- formatting ---


@pytest.mark.parametrize(
    ("system_id", "slug"),
    [
        ("regex-baseline", "regex-baseline"),
        ("llm:gpt-5-mini", "llm-gpt-5-mini"),
        ("a/b c", "a-b-c"),
    ],
)
def test_system_slug(system_id: str, slug: str) -> None:
    assert system_slug(system_id) == slug


def test_markdown_has_headline_fields_and_method_pointer() -> None:
    markdown = render_markdown(run())

    assert markdown.startswith("# Extraction accuracy: `llm:gpt-x`\n")
    assert "Run of 2026-10-09 13:02 UTC" in markdown
    assert "(104 documents, corpus commit `d891458e9822`); 104 documents scored." in markdown
    assert "System: model `gpt-x`, prompt `extract_invoice.v1`." in markdown
    assert (
        "| `llm:gpt-x` | 80.0% (72.0% to 87.0%) | $0.1235 | $0.001187 | 1,830 ms | 4,210 ms |"
        in markdown
    )
    for field in SCORED_FIELDS:
        assert f"| `{field}` |" in markdown
    assert "| `currency` | 100.0% | n/a | 0.0% |" in markdown
    assert "[docs/EVALS.md](../../docs/EVALS.md)" in markdown
    assert "Validation parity" not in markdown
    assert markdown.endswith("\n")
    assert "\r" not in markdown


def test_markdown_compares_with_the_other_systems_of_latest() -> None:
    latest = merge_latest(None, regex_run(), PARITY, now=WHEN)
    markdown = render_markdown(run(), latest)

    headline = markdown.split("## Headline")[1].split("## Per field")[0]
    assert headline.index("`llm:gpt-x`") < headline.index("`regex-baseline`")
    assert "| `regex-baseline` | 40.0% (31.0% to 50.0%) | $0.0000 | $0.000000 |" in headline
    assert "| Verdict agreement | 100.0% |" in markdown
    assert "| Fatal rule set agreement | 99.0% |" in markdown


def test_markdown_without_model_has_no_system_line() -> None:
    assert "System:" not in render_markdown(regex_run())


def test_missing_field_score_shows_a_dash() -> None:
    result = run()
    fields = dict(result.fields)
    del fields["due_date"]
    markdown = render_markdown(result.model_copy(update={"fields": fields}))
    assert "| `due_date` | n/a | n/a | n/a |" in markdown


def test_write_run_report_names_files_by_date_and_system(tmp_path: Path) -> None:
    markdown, data = write_run_report(run(), tmp_path)

    assert markdown == tmp_path / "2026-10-09-llm-gpt-x.md"
    assert data == tmp_path / "2026-10-09-llm-gpt-x.json"
    assert markdown.read_text(encoding="utf-8") == render_markdown(run())
    assert load_run_result(data) == run()
    assert json.loads(data.read_text(encoding="utf-8"))["cost_usd"] == "0.123456"


# --- latest.json ---


def test_update_latest_creates_the_file_in_the_handoff_shape(tmp_path: Path) -> None:
    path = tmp_path / "latest.json"
    update_latest(regex_run(), path=path, now=WHEN)

    document = json.loads(path.read_text(encoding="utf-8"))
    assert set(document) == {"generated_at", "dataset", "systems"}
    assert document["generated_at"] == "2026-10-09T13:02:11Z"
    assert document["dataset"] == {
        "name": "zugferd-corpus-hybrid-cii",
        "documents": 104,
        "corpus_commit": "d891458e9822e3",
    }
    (system,) = document["systems"]
    assert set(system) == {
        "id", "critical_correct", "fields", "cost_usd", "usd_per_doc",
        "latency_p50_ms", "latency_p95_ms",
    }  # fmt: skip
    assert system["critical_correct"] == {"value": 0.4, "ci_low": 0.31, "ci_high": 0.5}
    assert system["fields"]["currency"] == {"accuracy": 1.0, "abstention": 0.0}
    assert system["cost_usd"] == "0"


def test_update_latest_replaces_the_same_system_and_keeps_others(tmp_path: Path) -> None:
    path = tmp_path / "latest.json"
    update_latest(regex_run(), path=path, now=WHEN)
    update_latest(run(value=0.7), PARITY, path=path, now=WHEN)
    later = datetime(2026, 10, 10, 8, 0, tzinfo=UTC)
    report = update_latest(run(value=0.85), path=path, now=later)

    assert [system.id for system in report.systems] == ["regex-baseline", "llm:gpt-x"]
    assert report.systems[1].critical_correct.value == 0.85
    assert report.parity == PARITY
    assert report.generated_at == later
    assert load_latest(path) == report


def test_parity_alone_updates_only_parity(tmp_path: Path) -> None:
    path = tmp_path / "latest.json"
    update_latest(regex_run(), path=path, now=WHEN)
    newer = PARITY.model_copy(update={"rule_set_agreement": 1.0})
    report = update_latest(parity=newer, path=path, now=WHEN)

    assert [system.id for system in report.systems] == ["regex-baseline"]
    assert report.parity == newer


def test_parity_alone_needs_an_existing_report(tmp_path: Path) -> None:
    with pytest.raises(ReportError, match="does not exist yet"):
        update_latest(parity=PARITY, path=tmp_path / "latest.json")


def test_update_needs_something_to_write(tmp_path: Path) -> None:
    with pytest.raises(ReportError, match="nothing to update"):
        update_latest(path=tmp_path / "latest.json")


def test_results_for_another_dataset_are_refused(tmp_path: Path) -> None:
    path = tmp_path / "latest.json"
    update_latest(regex_run(), path=path, now=WHEN)
    other = run(dataset=DATASET.model_copy(update={"documents": 90}))

    with pytest.raises(ReportError, match="another dataset"):
        update_latest(other, path=path)


def test_load_latest_is_none_without_a_file(tmp_path: Path) -> None:
    assert load_latest(tmp_path / "latest.json") is None


def test_update_latest_refuses_an_invalid_file(tmp_path: Path) -> None:
    path = tmp_path / "latest.json"
    path.write_text('{"generated_at": "2026-10-09T13:02:11Z"}', encoding="utf-8")
    with pytest.raises(ValidationError):
        update_latest(regex_run(), path=path)


# --- the schema ---


def _latest(**overrides: object) -> dict[str, object]:
    document = merge_latest(None, run(), now=WHEN).model_dump(mode="json")
    document.update(overrides)
    return document


def test_latest_report_rejects_an_unknown_field() -> None:
    document = _latest()
    systems = document["systems"]
    assert isinstance(systems, list)
    systems[0]["fields"]["iban"] = {"accuracy": 1.0}
    with pytest.raises(ValidationError, match="not a scored field: iban"):
        LatestReport.model_validate(document)


def test_latest_report_rejects_a_system_twice() -> None:
    document = _latest()
    systems = document["systems"]
    assert isinstance(systems, list)
    with pytest.raises(ValidationError, match="each system appears once"):
        LatestReport.model_validate({**document, "systems": systems * 2})


@pytest.mark.parametrize(
    "overrides",
    [
        {"generated_at": "2026-10-09T13:02:11"},  # naive timestamp
        {"surprise": True},  # unknown key
        {"parity": {"files": 1, "excluded": 0, "verdict_agreement": 1.5, "rule_set_agreement": 1}},
    ],
)
def test_latest_report_rejects_invalid_documents(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        LatestReport.model_validate(_latest(**overrides))

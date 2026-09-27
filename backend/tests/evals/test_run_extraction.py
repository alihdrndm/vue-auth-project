"""The extraction runner: truth flattening, the baseline, and the guarded LLM run (no network)."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from evals.build_dataset import DatasetDocument
from evals.schema import Dataset

from einvoice.model import CanonicalInvoice
from evals import metrics, run_extraction
from llm.models import LlmCall
from llm.schemas import ExtractedInvoice
from tests.llm import fakes

TEXT = """--- page 1 ---
Druckerei Sommer GmbH
Rechnungsnummer: 2026-1043
Rechnungsdatum: 20.02.2026
Brutto: 1.547,00 EUR
"""
DATASET = Dataset(name="test", documents=2, corpus_commit="abc")


def truth() -> CanonicalInvoice:
    return CanonicalInvoice.model_validate(
        {
            "invoice_number": "2026-1043",
            "type_code": 380,
            "issue_date": "2026-02-20",
            "currency": "EUR",
            "seller": {"name": "Druckerei Sommer GmbH"},
            "buyer": {"name": "Holzwerk Brandt GmbH"},
            "gross_total": "1547.00",
        }
    )


def document(number: int = 1) -> DatasetDocument:
    return DatasetDocument(
        id=f"doc-{number}", path=f"doc-{number}.pdf", language="de", profile="EN 16931",
        text=TEXT, truth=truth(),
    )  # fmt: skip


def test_flatten_gives_strings_for_every_scored_field() -> None:
    values = run_extraction.flatten(truth())
    assert values["issue_date"] == "2026-02-20"
    assert values["gross_total"] == "1547.00"
    assert values["seller.name"] == "Druckerei Sommer GmbH"
    assert values["payee_iban"] is None
    assert set(values) == set(metrics.FIELDS)


def test_the_baseline_run_scores_without_cost() -> None:
    outcome = run_extraction.run_baseline([document(1), document(2)])
    result = run_extraction.result_of("regex-baseline", outcome, DATASET, None, None)
    assert result.documents == 2
    assert result.cost_usd == Decimal(0)
    assert result.critical_correct.value == 1.0
    assert result.fields["gross_total"].accuracy == 1.0


def test_the_estimate_follows_the_handoff_formula() -> None:
    from llm.budget import Prices

    prices = Prices(Decimal("0.05"), Decimal("0.005"), Decimal("0.40"))
    # ceil((len(TEXT) + 300) / 3) input tokens and 2,500 output tokens per document
    tokens_in = -(-(len(TEXT) + 300) // 3)
    expected = (tokens_in * Decimal("0.05") + 2500 * Decimal("0.40")) / Decimal(1_000_000)
    assert run_extraction.estimate([document()], 300, prices) == expected


@pytest.fixture
def runs_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "llm-runs.json"
    monkeypatch.setattr(run_extraction, "RUNS_FILE", path)
    return path


@pytest.mark.django_db
def test_the_llm_run_refuses_while_the_llm_is_off(runs_file: Path) -> None:
    with pytest.raises(SystemExit, match="LLM_ENABLED"):
        run_extraction.run_llm([document()], Decimal("0.75"), ask=lambda _q: "yes")


@pytest.mark.django_db
def test_the_llm_run_needs_a_typed_yes(runs_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sdk = fakes.install(monkeypatch)
    monkeypatch.setattr("eingang.config.get_settings", lambda: fakes.enabled_settings())
    with pytest.raises(SystemExit, match="not confirmed"):
        run_extraction.run_llm([document()], Decimal("0.75"), ask=lambda _q: "no")
    assert sdk.requests == []
    assert not runs_file.exists()


@pytest.mark.django_db
def test_a_third_live_run_is_refused(runs_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fakes.install(monkeypatch)
    monkeypatch.setattr("eingang.config.get_settings", lambda: fakes.enabled_settings())
    runs_file.write_text(json.dumps({"extract_invoice.v1": 2}), encoding="utf-8")
    with pytest.raises(SystemExit, match="third"):
        run_extraction.run_llm([document()], Decimal("0.75"), ask=lambda _q: "yes")


def answer() -> ExtractedInvoice:
    values: dict[str, object] = dict.fromkeys(ExtractedInvoice.model_fields)
    values.update(
        tax_breakdown=[],
        lines=[],
        invoice_number="2026-1043",
        invoice_number_evidence="Rechnungsnummer: 2026-1043",
        issue_date="2026-02-20",
        issue_date_evidence="Rechnungsdatum: 20.02.2026",
        gross_total="1547.00",
        gross_total_evidence="Brutto: 1.547,00 EUR",
    )
    return ExtractedInvoice.model_validate(values)


@pytest.mark.django_db
def test_the_llm_run_scores_ledgers_as_eval_and_counts_the_run(
    runs_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sdk = fakes.install(monkeypatch)
    monkeypatch.setattr("eingang.config.get_settings", lambda: fakes.enabled_settings())
    sdk.replies.append(fakes.reply(answer()))
    outcome, model, prompt = run_extraction.run_llm(
        [document()], Decimal("0.75"), ask=lambda _q: "yes"
    )
    assert (model, prompt) == ("test-model", "extract_invoice.v1")
    assert outcome.predictions[0]["invoice_number"] == "2026-1043"
    assert outcome.cost > 0
    assert LlmCall.objects.get().purpose == "eval"
    assert json.loads(runs_file.read_text(encoding="utf-8")) == {"extract_invoice.v1": 1}
    result = run_extraction.result_of("llm:test-model", outcome, DATASET, model, prompt)
    assert result.critical_correct.value == 1.0


@pytest.mark.django_db
def test_the_llm_run_stops_before_the_eval_budget(
    runs_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sdk = fakes.install(monkeypatch)
    monkeypatch.setattr("eingang.config.get_settings", lambda: fakes.enabled_settings())
    sdk.replies.append(fakes.reply(answer()))
    outcome, _model, _prompt = run_extraction.run_llm(
        [document(1), document(2)], Decimal("0.0011"), ask=lambda _q: "yes"
    )
    assert len(outcome.predictions) == 1
    assert outcome.stopped is not None
    assert "EVAL_BUDGET_USD" in outcome.stopped

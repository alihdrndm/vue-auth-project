"""The smoke-call tool, run against the fake SDK only (no test ever reaches the network)."""

import json
from pathlib import Path

import live_llm
import llm_smoke
import pytest

from llm.models import LlmCall
from llm.schemas import ComparedValues, ExtractedInvoice, RuleExplanationOut
from tests.llm import fakes

pytestmark = pytest.mark.django_db


def install(monkeypatch: pytest.MonkeyPatch, **overrides: object) -> fakes.FakeSdk:
    """The fake SDK, and the tool reading the same (fake) settings as the LLM client."""
    configured = fakes.enabled_settings(**overrides)
    monkeypatch.setattr(live_llm, "get_settings", lambda: configured)
    return fakes.install(monkeypatch, **overrides)


def extracted(**values: object) -> ExtractedInvoice:
    empty: dict[str, object] = dict.fromkeys(ExtractedInvoice.model_fields)
    empty.update(tax_breakdown=[], lines=[])
    return ExtractedInvoice.model_validate({**empty, **values})


def compared(**values: object) -> ComparedValues:
    return ComparedValues.model_validate({**dict.fromkeys(ComparedValues.model_fields), **values})


def never_asked(_prompt: str) -> str:
    raise AssertionError("--yes must not ask")


def queue_three(sdk: fakes.FakeSdk) -> None:
    sdk.replies += [
        fakes.reply(extracted(invoice_number="2026-1043"), input_tokens=900, output=700),
        fakes.reply(compared(gross_total="1190.00"), input_tokens=500, output=150),
        fakes.reply(
            RuleExplanationOut(plain_text="The buyer reference is missing.", fix_hint="Add it."),
            input_tokens=300,
            output=80,
        ),
    ]


def test_refuses_while_the_llm_is_off(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sdk = install(monkeypatch, LLM_ENABLED=False)
    assert llm_smoke.run(assume_yes=True, fixtures_dir=tmp_path, ask=never_asked) == 2
    assert "LLM_ENABLED is not true" in capsys.readouterr().err
    assert sdk.requests == []
    assert not LlmCall.objects.exists()


def test_asks_and_aborts_without_yes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sdk = install(monkeypatch)
    questions: list[str] = []

    def answer_no(prompt: str) -> str:
        questions.append(prompt)
        return "no"

    assert llm_smoke.run(assume_yes=False, fixtures_dir=tmp_path, ask=answer_no) == 1
    out = capsys.readouterr().out
    assert "Estimated maximum cost" in out
    assert "Aborted" in out
    assert len(questions) == 1
    assert sdk.requests == []
    assert list(tmp_path.iterdir()) == []


def test_records_three_fixtures_with_usage_and_no_prompt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sdk = install(monkeypatch)
    queue_three(sdk)
    assert llm_smoke.run(assume_yes=True, fixtures_dir=tmp_path, ask=never_asked) == 0
    assert [request["max_output_tokens"] for request in sdk.requests] == [2500, 600, 400]
    assert "Rechnungsnummer: 2026-1043" in sdk.requests[0]["input"][1]["content"]
    assert "SA/26/1160" in sdk.requests[1]["input"][1]["content"]
    assert "BR-DE-15" in sdk.requests[2]["input"][1]["content"]
    prompts = [request["input"][0]["content"] for request in sdk.requests]
    for feature, prompt in zip(["extract", "compare", "explain"], prompts, strict=True):
        text = (tmp_path / f"{feature}.json").read_text(encoding="utf-8")
        recorded = json.loads(text)
        assert recorded["feature"] == feature
        assert recorded["usage"]["status"] == "completed"
        assert recorded["usage"]["output_tokens"] <= recorded["max_output_tokens"]
        assert prompt[:200] not in text
        assert "<document>" not in text
        assert "<rule>" not in text
    extract = json.loads((tmp_path / "extract.json").read_text(encoding="utf-8"))
    assert extract["usage"]["input_tokens"] == 900
    assert extract["prompt_version"] == "extract_invoice.v1"
    assert extract["response"]["invoice_number"] == "2026-1043"
    out = capsys.readouterr().out
    assert "Estimated maximum cost" in out
    assert "Model: test-model" in out
    assert "Actual cost of this run" in out
    assert "Ledger total" in out
    assert LlmCall.objects.filter(status="ok").count() == 3


def test_an_incomplete_response_is_reported_and_not_recorded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sdk = install(monkeypatch)
    queue_three(sdk)
    sdk.replies[0] = fakes.reply(extracted(), status="incomplete", output=2500)
    assert llm_smoke.run(assume_yes=True, fixtures_dir=tmp_path, ask=never_asked) == 1
    err = capsys.readouterr().err
    assert "extract: FAILED" in err
    assert "max_output_tokens=2500" in err
    assert not (tmp_path / "extract.json").exists()
    assert (tmp_path / "compare.json").exists()
    assert (tmp_path / "explain.json").exists()
    assert LlmCall.objects.filter(status="error", output_tokens=2500).count() == 1


def test_estimate_covers_the_three_requests() -> None:
    planned = llm_smoke.smoke_requests(live_llm.SAMPLES_DIR)
    assert list(planned) == ["extract", "compare", "explain"]
    assert planned["explain"].data.startswith("<rule>\nRule ID: BR-DE-15\n")

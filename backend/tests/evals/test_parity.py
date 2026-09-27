"""Reading KoSIT reports and comparing them with Eingang's verdicts (evals/parity.py)."""

from pathlib import Path

import pytest

from evals import parity

SCENARIOS = """<scenarios>
<scenario><name>EN16931 XRechnung (UBL Invoice)</name>
  <customLevel level="information">BR-CO-16</customLevel>
  <customLevel level="error">UBL-CR-646</customLevel>
</scenario>
<scenario><name>Other</name></scenario>
</scenarios>"""


def report(tmp_path: Path, body: str, *, accept: bool = True, matched: bool = True) -> Path:
    head = (
        "<rep:scenarioMatched><s:scenario><s:name>EN16931 XRechnung (UBL Invoice)</s:name>"
        if matched
        else "<rep:noScenarioMatched>"
    )
    verdict = "<rep:accept/>" if accept else "<rep:reject/>"
    path = tmp_path / "r-report.xml"
    path.write_text(
        f"<rep:report>{head}{body}<rep:assessment>{verdict}</rep:assessment></rep:report>",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def levels(tmp_path: Path) -> dict[str, dict[str, str]]:
    (tmp_path / "scenarios.xml").write_text(SCENARIOS, encoding="utf-8")
    return parity.custom_levels(tmp_path)


def test_custom_levels_are_read_per_scenario(levels: dict[str, dict[str, str]]) -> None:
    assert levels["EN16931 XRechnung (UBL Invoice)"] == {
        "BR-CO-16": "information",
        "UBL-CR-646": "error",
    }
    assert levels["Other"] == {}


def test_fatal_rules_apply_the_scenarios_custom_levels(
    tmp_path: Path, levels: dict[str, dict[str, str]]
) -> None:
    body = (
        '<rep:validationStepResult id="val-xsd" valid="true"/>'
        '<rep:validationStepResult id="val-sch.1" valid="false">'
        '<rep:message level="error" code="BR-CO-16">x</rep:message>'
        '<rep:message level="error" code="BR-DE-15">x</rep:message>'
        '<rep:message level="warning" code="UBL-CR-646">x</rep:message>'
        '<rep:message level="warning" code="UBL-CR-470">x</rep:message>'
        "</rep:validationStepResult>"
    )
    verdict, fatal, excluded = parity.kosit_verdict(report(tmp_path, body, accept=False), levels)
    assert (verdict, fatal, excluded) == ("reject", ["BR-DE-15", "UBL-CR-646"], None)


def test_schema_errors_count_as_xsd(tmp_path: Path, levels: dict[str, dict[str, str]]) -> None:
    body = (
        '<rep:validationStepResult id="val-xsd" valid="false">'
        '<rep:message level="error">cvc-complex-type</rep:message>'
        "</rep:validationStepResult>"
    )
    assert parity.kosit_verdict(report(tmp_path, body, accept=False), levels)[1] == ["XSD"]


def test_unmatched_and_missing_reports_are_excluded(
    tmp_path: Path, levels: dict[str, dict[str, str]]
) -> None:
    assert parity.kosit_verdict(report(tmp_path, "", matched=False), levels)[2] == (
        "no KoSIT scenario"
    )
    assert parity.kosit_verdict(tmp_path / "missing.xml", levels)[2] == "no KoSIT report"


def test_agreement_counts_verdicts_and_rule_sets() -> None:
    same = parity.FileResult("a", "a", "warnings", "accept", ["X"], ["X"])
    other_rules = parity.FileResult("b", "b", "invalid", "reject", ["X"], ["Y"])
    assert same.verdict_agrees
    assert same.rules_agree
    assert other_rules.verdict_agrees
    assert not other_rules.rules_agree


def test_compare_excludes_and_summarises(
    tmp_path: Path, levels: dict[str, dict[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = [parity.Source("a.xml", "a", b"<a/>"), parity.Source("b.xml", "b", b"<b/>")]
    verdicts: dict[str, tuple[str | None, list[str], str | None]] = {
        "a.xml": ("valid", [], None),
        "b.xml": (None, [], "not applicable: BASIC WL"),
    }
    monkeypatch.setattr(parity, "eingang_verdict", lambda source: verdicts[source.name])
    accepted = report(tmp_path, "")
    result = parity.compare(sources, {"a.xml": accepted, "b.xml": accepted}, levels)
    assert (result.files, result.excluded) == (1, 1)
    assert result.verdict_agreement == result.rule_set_agreement == 1.0
    assert result.disagreements == []


def test_eingang_verdict_reads_a_real_sample() -> None:
    sample = parity.REPO / "samples" / "S05-RE-2026-0413.xml"
    source = parity.Source(sample.name, "samples/S05", sample.read_bytes())
    assert parity.eingang_verdict(source) == ("invalid", ["BR-DE-15"], None)

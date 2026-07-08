"""`manage.py seed_rules` (HANDOFF section 7; "Eingang deployment specifics")."""

import json
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from invoices.management.commands import seed_rules
from invoices.models import RuleExplanation

pytestmark = pytest.mark.django_db


def curated() -> dict[str, dict[str, str]]:
    data: dict[str, dict[str, str]] = json.loads(
        seed_rules.CURATED_RULES.read_text(encoding="utf-8")
    )
    return data


def test_seed_rules_loads_every_curated_text() -> None:
    call_command("seed_rules", stdout=StringIO())
    rows = {row.rule_id: row for row in RuleExplanation.objects.all()}
    assert set(rows) == set(curated())
    for rule_id, entry in curated().items():
        row = rows[rule_id]
        assert (row.plain_text, row.fix_hint) == (entry["plain_text"], entry["fix_hint"])
        assert (row.source, row.prompt_version) == ("curated", None)


def test_seed_rules_is_idempotent() -> None:
    call_command("seed_rules", stdout=StringIO())
    first = list(RuleExplanation.objects.order_by("rule_id").values())
    call_command("seed_rules", stdout=StringIO())
    assert list(RuleExplanation.objects.order_by("rule_id").values()) == first


def test_seed_rules_updates_a_changed_curated_row() -> None:
    RuleExplanation.objects.create(
        rule_id="BR-DE-15", plain_text="Old.", fix_hint="Old.", source="curated"
    )
    call_command("seed_rules", stdout=StringIO())
    row = RuleExplanation.objects.get(rule_id="BR-DE-15")
    assert row.plain_text == curated()["BR-DE-15"]["plain_text"]


def test_seed_rules_keeps_an_llm_explanation() -> None:
    RuleExplanation.objects.create(
        rule_id="BR-DE-15",
        plain_text="From the model.",
        fix_hint="Model hint.",
        source="llm",
        prompt_version="v1",
    )
    out = StringIO()
    call_command("seed_rules", stdout=out)
    row = RuleExplanation.objects.get(rule_id="BR-DE-15")
    assert (row.plain_text, row.fix_hint, row.source, row.prompt_version) == (
        "From the model.",
        "Model hint.",
        "llm",
        "v1",
    )
    assert f"Seeded {len(curated()) - 1} " in out.getvalue()
    assert "kept 1 from the LLM" in out.getvalue()


def test_seed_rules_curated_texts_fit_the_columns() -> None:
    for rule_id, entry in curated().items():
        assert len(entry["plain_text"]) <= 300, rule_id
        assert len(entry["fix_hint"]) <= 200, rule_id


def test_seed_rules_curated_file_is_sorted_by_rule_id() -> None:
    assert list(curated()) == sorted(curated())


@pytest.mark.parametrize(
    ("entry", "problem"),
    [
        ({"plain_text": "x" * 301, "fix_hint": "ok"}, "plain_text has 301 > 300"),
        ({"plain_text": "ok", "fix_hint": "x" * 201}, "fix_hint has 201 > 200"),
        ({"plain_text": "ok"}, "needs the strings plain_text and fix_hint"),
    ],
)
def test_seed_rules_fails_loudly_on_a_bad_text_and_writes_nothing(
    entry: dict[str, str],
    problem: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "curated_rules.json"
    good = {"plain_text": "ok", "fix_hint": "ok"}
    path.write_text(json.dumps({"A-1": good, "B-2": entry}), encoding="utf-8")
    monkeypatch.setattr(seed_rules, "CURATED_RULES", path)
    with pytest.raises(CommandError, match=f"B-2: {problem}"):
        call_command("seed_rules", stdout=StringIO())
    assert not RuleExplanation.objects.exists()


def test_seed_rules_rejects_a_file_that_is_not_an_object(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "curated_rules.json"
    path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(seed_rules, "CURATED_RULES", path)
    with pytest.raises(CommandError, match="JSON object keyed by rule ID"):
        call_command("seed_rules", stdout=StringIO())

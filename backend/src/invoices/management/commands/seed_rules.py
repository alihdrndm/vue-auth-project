"""`uv run poe seed-rules`: load the curated rule explanations (HANDOFF section 7).

Idempotent and makes no LLM call. Curated rows are created or updated; a rule that already
has an explanation from the LLM keeps it, because a stored rule is never re-explained.
Every text is checked against the column limits first, and nothing is written if one fails.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from invoices.models import RuleExplanation

CURATED_RULES = Path(__file__).resolve().parents[2] / "data" / "curated_rules.json"
PLAIN_TEXT_MAX = 300
FIX_HINT_MAX = 200


@dataclass(frozen=True)
class CuratedRule:
    rule_id: str
    plain_text: str
    fix_hint: str


def load_curated_rules(path: Path) -> list[CuratedRule]:
    """Read and check the file; raises CommandError listing every problem."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise CommandError(f"{path.name} must be a JSON object keyed by rule ID.")
    rules: list[CuratedRule] = []
    problems: list[str] = []
    for rule_id, entry in data.items():
        plain_text = entry.get("plain_text") if isinstance(entry, dict) else None
        fix_hint = entry.get("fix_hint") if isinstance(entry, dict) else None
        if not isinstance(plain_text, str) or not isinstance(fix_hint, str):
            problems.append(f"{rule_id}: needs the strings plain_text and fix_hint")
            continue
        if len(plain_text) > PLAIN_TEXT_MAX:
            problems.append(f"{rule_id}: plain_text has {len(plain_text)} > {PLAIN_TEXT_MAX} chars")
        if len(fix_hint) > FIX_HINT_MAX:
            problems.append(f"{rule_id}: fix_hint has {len(fix_hint)} > {FIX_HINT_MAX} chars")
        rules.append(CuratedRule(rule_id=rule_id, plain_text=plain_text, fix_hint=fix_hint))
    if problems:
        raise CommandError(f"{path.name} is invalid:\n" + "\n".join(problems))
    return rules


class Command(BaseCommand):
    help = "Load the curated rule explanations into rule_explanations (idempotent)."

    def handle(self, *args: Any, **options: Any) -> None:  # boundary: django command options
        rules = load_curated_rules(CURATED_RULES)
        seeded = 0
        with transaction.atomic():
            from_llm = set(
                RuleExplanation.objects.filter(
                    rule_id__in=[rule.rule_id for rule in rules],
                    source=RuleExplanation.Source.LLM,
                ).values_list("rule_id", flat=True)
            )
            for rule in rules:
                if rule.rule_id in from_llm:
                    continue
                RuleExplanation.objects.update_or_create(
                    rule_id=rule.rule_id,
                    defaults={
                        "plain_text": rule.plain_text,
                        "fix_hint": rule.fix_hint,
                        "source": RuleExplanation.Source.CURATED,
                        "prompt_version": None,
                    },
                )
                seeded += 1
        self.stdout.write(
            f"Seeded {seeded} curated rule explanations; kept {len(from_llm)} from the LLM."
        )

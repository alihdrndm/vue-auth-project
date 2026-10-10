"""Add the precomputed LLM answers to the seed data (HANDOFF section 12, "How the seed works").

Run as `uv run poe precompute-samples` with LLM_ENABLED=true for this run only. It adds

- to `samples/precomputed/S08.json` the key `extraction` (the extraction answer), and
- to `samples/precomputed/S10.json` the key `comparison` (the comparison answer),

each as `{"prompt_version": ..., "answer": ...}`. The requests are the activities' own, so
a request the smoke call already made is served from the cache for free. Like the smoke
call it prints the estimated maximum cost and asks for `yes` (or takes `--yes`). A sample
that already has its key is skipped unless `--force` is given. `samples/manifest.json` is
not changed here.
"""

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from live_llm import SAMPLES_DIR, Ask, Caller, confirm, enabled_settings, report_cost

from invoices.extraction import TEXT_LIMIT
from llm import requests
from llm.client import AnyRequest


@dataclass(frozen=True)
class Target:
    sample_id: str
    key: str
    build: Callable[[str], AnyRequest]  # the feature's request builder, from the text


TARGETS = (
    Target("S08", "extraction", requests.extraction_request),
    Target("S10", "comparison", requests.comparison_request),
)


def _path(samples_dir: Path, sample_id: str) -> Path:
    return samples_dir / "precomputed" / f"{sample_id}.json"


def _load(path: Path) -> dict[str, Any]:  # boundary: JSON file
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))  # boundary: json
    return loaded


def run(
    *,
    assume_yes: bool,
    force: bool = False,
    samples_dir: Path = SAMPLES_DIR,
    ask: Ask = input,
) -> int:
    settings = enabled_settings()
    if settings is None:
        return 2
    planned: list[tuple[Target, AnyRequest]] = []
    for target in TARGETS:
        precomputed = _load(_path(samples_dir, target.sample_id))
        if target.key in precomputed and not force:
            print(f"{target.sample_id}: already has '{target.key}', skipped (--force rewrites)")
            continue
        text = str(precomputed["text"])[:TEXT_LIMIT]
        planned.append((target, target.build(text)))
    if not planned:
        print("Nothing to precompute.")
        return 0
    if not confirm(settings, [request for _, request in planned], assume_yes=assume_yes, ask=ask):
        return 1
    caller = Caller()
    failures = 0
    for target, request in planned:
        outcome = caller.call(request)
        if isinstance(outcome, str):
            print(f"{target.sample_id}: FAILED: {outcome}", file=sys.stderr)
            failures += 1
            continue
        path = _path(samples_dir, target.sample_id)
        precomputed = _load(path)
        precomputed[target.key] = {
            "prompt_version": request.prompt.label,
            "answer": outcome.answer.model_dump(mode="json"),
        }
        path.write_text(
            json.dumps(precomputed, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"{target.sample_id}: wrote '{target.key}' to {path}")
    report_cost(caller)
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="do not ask before calling")
    parser.add_argument("--force", action="store_true", help="rewrite answers already present")
    parser.add_argument("--samples-dir", type=Path, default=SAMPLES_DIR)
    args = parser.parse_args()
    return run(assume_yes=args.yes, force=args.force, samples_dir=args.samples_dir)


if __name__ == "__main__":
    sys.exit(main())

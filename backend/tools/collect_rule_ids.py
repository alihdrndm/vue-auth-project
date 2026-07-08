"""List the rule IDs that need a curated explanation (HANDOFF section 7, "Rule explanations").

The curated texts must cover every rule ID that fires on the corpus `fail` files and on the
sandbox samples, plus `XSD`. This script detects and validates each of those files, prints
the rule IDs it finds, and then the IDs missing from `curated_rules.json`. It exits with 1
when any are missing.

Run from backend/ as `uv run python tools/collect_rule_ids.py`. It needs the corpus
(`uv run poe fetch-corpus`) and the worker libraries.
"""

import json
import sys
from collections.abc import Iterable
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR / "src"))

from einvoice.detect import detect  # noqa: E402 - after the path set-up above
from einvoice.validate import validate  # noqa: E402

CORPUS_DIR = REPO_ROOT / "data" / "corpus"
SAMPLES_DIR = REPO_ROOT / "samples"
CURATED_RULES = BACKEND_DIR / "src" / "invoices" / "data" / "curated_rules.json"
# XSD findings carry the rule ID "XSD" (section 3, step 1); always curated.
ALWAYS = frozenset({"XSD"})


def corpus_fail_files(corpus: Path) -> list[Path]:
    """Every file in the ZUGFeRDv1 and ZUGFeRDv2 `fail` folders."""
    return sorted(path for path in corpus.glob("ZUGFeRDv*/fail/**/*") if path.is_file())


def sample_files(samples: Path) -> list[Path]:
    """The sandbox samples listed in `samples/manifest.json`."""
    manifest = json.loads((samples / "manifest.json").read_text(encoding="utf-8"))
    return [samples / str(entry["file"]) for entry in manifest["samples"]]


def rule_ids_of(paths: Iterable[Path]) -> set[str]:
    """The rule IDs of every validation issue, of any severity, raised by these files."""
    found: set[str] = set()
    for path in paths:
        report = validate(detect(path.read_bytes(), path.name))
        found.update(issue.rule_id for issue in report.issues)
    return found


def collect(corpus: Path, samples: Path) -> set[str]:
    return set(ALWAYS) | rule_ids_of(corpus_fail_files(corpus)) | rule_ids_of(sample_files(samples))


def curated_ids(path: Path = CURATED_RULES) -> set[str]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(key) for key in data}


def main() -> int:
    if not corpus_fail_files(CORPUS_DIR):
        print("The corpus is missing. Run: uv run poe fetch-corpus", file=sys.stderr)
        return 1
    found = collect(CORPUS_DIR, SAMPLES_DIR)
    print(f"Rule IDs found ({len(found)}):")
    for rule_id in sorted(found):
        print(f"  {rule_id}")
    missing = sorted(found - curated_ids())
    if missing:
        print(f"Missing from {CURATED_RULES.name} ({len(missing)}):")
        for rule_id in missing:
            print(f"  {rule_id}")
        return 1
    print(f"All of them are in {CURATED_RULES.name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

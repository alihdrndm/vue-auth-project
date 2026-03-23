"""Fail when a package misses its coverage threshold (HANDOFF "Coverage thresholds").

Reads coverage.json, which pytest writes (`--cov-report=json`). Run as part of
`uv run poe test`.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPORT = BACKEND_DIR / "coverage.json"


@dataclass(frozen=True)
class Threshold:
    lines: float
    branches: float | None = None


# Packages under src/ with stricter thresholds; every other package needs DEFAULT.
THRESHOLDS = {
    "einvoice": Threshold(lines=90, branches=85),
    "invoices": Threshold(lines=90),
}
DEFAULT = Threshold(lines=75)

# The parts of coverage.json used here: {"files": {path: {"summary": {name: count}}}}.
Report = dict[str, dict[str, dict[str, dict[str, int]]]]


@dataclass
class Totals:
    statements: int = 0
    covered_lines: int = 0
    branches: int = 0
    covered_branches: int = 0

    def line_percent(self) -> float:
        return 100.0 if self.statements == 0 else 100 * self.covered_lines / self.statements

    def branch_percent(self) -> float:
        return 100.0 if self.branches == 0 else 100 * self.covered_branches / self.branches


def package_of(path: str) -> str:
    # coverage.json keeps the OS separator; split on both so the result is the same everywhere.
    parts = PurePosixPath(path.replace("\\", "/")).parts
    return parts[parts.index("src") + 1] if "src" in parts else parts[0]


def totals_by_package(report: Report) -> dict[str, Totals]:
    packages: dict[str, Totals] = {}
    for path, data in report["files"].items():
        summary = data["summary"]
        totals = packages.setdefault(package_of(path), Totals())
        totals.statements += summary["num_statements"]
        totals.covered_lines += summary["covered_lines"]
        totals.branches += summary.get("num_branches", 0)
        totals.covered_branches += summary.get("covered_branches", 0)
    return packages


def problems(packages: dict[str, Totals]) -> list[str]:
    found = []
    for name, totals in sorted(packages.items()):
        threshold = THRESHOLDS.get(name, DEFAULT)
        lines = totals.line_percent()
        if lines < threshold.lines:
            found.append(f"{name}: lines {lines:.1f}% < {threshold.lines}%")
        if threshold.branches is not None and totals.branch_percent() < threshold.branches:
            found.append(f"{name}: branches {totals.branch_percent():.1f}% < {threshold.branches}%")
    return found


def main() -> int:
    if not REPORT.exists():
        print("coverage.json is missing; run the tests first", file=sys.stderr)
        return 1
    packages = totals_by_package(json.loads(REPORT.read_text(encoding="utf-8")))
    for name, totals in sorted(packages.items()):
        print(
            f"{name:<12} lines {totals.line_percent():5.1f}%   "
            f"branches {totals.branch_percent():5.1f}%"
        )
    found = problems(packages)
    for problem in found:
        print(f"coverage below threshold: {problem}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())

"""The result of one evaluation run, and the shape of `evals/latest.json`.

`LatestReport` and its parts live in `eingang.accuracy`, because `GET /api/v1/accuracy`
validates the same file and application code does not import from `evals/`. `RunResult` is
what a run produces (the metrics code builds it): the headline numbers of one system plus the
run's context. It is written as `evals/reports/<date>-<system>.json`.
"""

from pydantic import AwareDatetime, Field

from eingang.accuracy import (
    SCORED_FIELDS,
    CriticalCorrect,
    Dataset,
    FieldScore,
    LatestReport,
    Parity,
    SystemResult,
)

__all__ = [
    "SCORED_FIELDS",
    "CriticalCorrect",
    "Dataset",
    "FieldScore",
    "LatestReport",
    "Parity",
    "RunResult",
    "SystemResult",
]


class RunResult(SystemResult):
    """One system's run: its headline numbers, when it ran, and on what."""

    generated_at: AwareDatetime
    dataset: Dataset
    documents: int = Field(ge=0, description="documents scored (fewer than the dataset's if cut)")

    def system(self) -> SystemResult:
        """The entry for `latest.json`."""
        return SystemResult.model_validate(self.model_dump(include=set(SystemResult.model_fields)))

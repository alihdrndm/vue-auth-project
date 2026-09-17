"""The shape of `evals/latest.json` (HANDOFF "Evaluation", "Outputs").

The evaluation scripts in `evals/` write the file and `GET /api/v1/accuracy` serves it; both
validate it with `LatestReport`. The models live here because application code never imports
from `evals/` (it is not on the application's import path), while the evaluation scripts put
`backend/src` on theirs.

Rates (accuracy, hallucination, abstention, agreement) are floats between 0 and 1. Money is
Decimal and is written as a string. A rate whose denominator is zero (for example the
hallucination rate of a field that is present in every document) is left out.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

# The fields every system is scored on, in the order reports list them.
SCORED_FIELDS = (
    "invoice_number",
    "issue_date",
    "due_date",
    "currency",
    "seller.name",
    "seller.vat_id",
    "payee_iban",
    "buyer.name",
    "net_total",
    "tax_total",
    "gross_total",
    "payable_amount",
)

Rate = Annotated[float, Field(ge=0, le=1)]
Usd = Annotated[Decimal, Field(ge=0)]
Milliseconds = Annotated[float, Field(ge=0)]


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Dataset(_Strict):
    name: str
    documents: int = Field(ge=0)
    corpus_commit: str


class CriticalCorrect(_Strict):
    """Share of documents whose critical fields are all correct, with its 95% bootstrap CI."""

    value: Rate
    ci_low: Rate
    ci_high: Rate


class FieldScore(_Strict):
    accuracy: Rate | None = None
    hallucination: Rate | None = None
    abstention: Rate | None = None


class SystemResult(_Strict):
    """The headline numbers of one system (`regex-baseline` or `llm:<model>`)."""

    id: str = Field(min_length=1)
    model: str | None = None
    prompt_version: str | None = None
    critical_correct: CriticalCorrect
    fields: dict[str, FieldScore]
    cost_usd: Usd
    usd_per_doc: Usd
    latency_p50_ms: Milliseconds
    latency_p95_ms: Milliseconds

    @field_validator("fields")
    @classmethod
    def _fields_are_scored_fields(cls, fields: dict[str, FieldScore]) -> dict[str, FieldScore]:
        unknown = sorted(set(fields) - set(SCORED_FIELDS))
        if unknown:
            raise ValueError(f"not a scored field: {', '.join(unknown)}")
        return fields


class Parity(_Strict):
    """Validation parity with the official KoSIT validator."""

    files: int = Field(ge=0)
    excluded: int = Field(ge=0)
    verdict_agreement: Rate
    rule_set_agreement: Rate


class LatestReport(_Strict):
    generated_at: AwareDatetime
    dataset: Dataset
    systems: list[SystemResult]
    parity: Parity | None = None

    @field_validator("systems")
    @classmethod
    def _one_entry_per_system(cls, systems: list[SystemResult]) -> list[SystemResult]:
        ids = [system.id for system in systems]
        if len(ids) != len(set(ids)):
            raise ValueError("each system appears once")
        return systems

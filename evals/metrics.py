"""Scoring an extraction run against the corpus truth (HANDOFF "Extraction accuracy").

Values are compared after normalisation: dates, currency, IBAN, VAT ID and amounts exactly;
the invoice number ignoring case and whitespace; names when `token_set_ratio` >= 90. Per
field: accuracy over documents whose truth has the field, hallucination (a value predicted
where the truth has none) and abstention (null predicted where the truth has a value).
"""

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from rapidfuzz import fuzz
from rapidfuzz.utils import default_process

Values = dict[str, str | None]

FIELDS = (
    "invoice_number", "issue_date", "due_date", "currency", "seller.name", "seller.vat_id",
    "payee_iban", "buyer.name", "net_total", "tax_total", "gross_total", "payable_amount",
)  # fmt: skip
NAME_THRESHOLD = 90
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 42


def _compact(value: str) -> str:
    return "".join(value.split()).upper()


def _date(value: str) -> date | None:
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _amount(value: str) -> Decimal | None:
    try:
        return Decimal(value.strip()).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _same_date(truth: str, predicted: str) -> bool:
    parsed = _date(predicted)
    return parsed is not None and parsed == _date(truth)


def _same_amount(truth: str, predicted: str) -> bool:
    parsed = _amount(predicted)
    return parsed is not None and parsed == _amount(truth)


def _same_code(truth: str, predicted: str) -> bool:
    return _compact(truth) == _compact(predicted)


def _same_name(truth: str, predicted: str) -> bool:
    ratio = fuzz.token_set_ratio(truth, predicted, processor=default_process)
    return bool(ratio >= NAME_THRESHOLD)


MATCHERS: dict[str, Callable[[str, str], bool]] = {
    "invoice_number": _same_code,  # case- and whitespace-insensitive
    "issue_date": _same_date,
    "due_date": _same_date,
    "currency": _same_code,
    "seller.name": _same_name,
    "seller.vat_id": _same_code,
    "payee_iban": _same_code,
    "buyer.name": _same_name,
    "net_total": _same_amount,
    "tax_total": _same_amount,
    "gross_total": _same_amount,
    "payable_amount": _same_amount,
}


def _present(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def correct(field: str, truth: str | None, predicted: str | None) -> bool:
    """Whether one predicted value matches a present truth value."""
    if truth is None or predicted is None or not truth.strip() or not predicted.strip():
        return False
    return MATCHERS[field](truth, predicted)


@dataclass(frozen=True)
class FieldScore:
    accuracy: float | None  # None when no document has the field in its truth
    hallucination: float | None  # None when every document has it
    abstention: float | None


def score_field(field: str, truths: Sequence[Values], predictions: Sequence[Values]) -> FieldScore:
    present = absent = right = invented = abstained = 0
    for truth, predicted in zip(truths, predictions, strict=True):
        truth_value, predicted_value = truth.get(field), predicted.get(field)
        if _present(truth_value):
            present += 1
            right += correct(field, truth_value, predicted_value)
            abstained += not _present(predicted_value)
        else:
            absent += 1
            invented += _present(predicted_value)
    return FieldScore(
        accuracy=right / present if present else None,
        hallucination=invented / absent if absent else None,
        abstention=abstained / present if present else None,
    )


def critical_correct(truth: Values, predicted: Values) -> bool:
    """Invoice number, issue date, gross total and (when the truth has one) the IBAN."""
    fields = ["invoice_number", "issue_date", "gross_total"]
    if _present(truth.get("payee_iban")):
        fields.append("payee_iban")
    return all(correct(field, truth.get(field), predicted.get(field)) for field in fields)


@dataclass(frozen=True)
class Interval:
    value: float
    ci_low: float
    ci_high: float


def bootstrap(outcomes: Sequence[bool], resamples: int = BOOTSTRAP_RESAMPLES) -> Interval:
    """The share of True with a 95% percentile bootstrap interval (seed 42)."""
    if not outcomes:
        return Interval(0.0, 0.0, 0.0)
    generator = random.Random(BOOTSTRAP_SEED)  # noqa: S311 - statistics, not security
    size = len(outcomes)
    shares = sorted(sum(generator.choices(outcomes, k=size)) / size for _ in range(resamples))
    return Interval(
        value=sum(outcomes) / size,
        ci_low=shares[int(0.025 * resamples)],
        ci_high=shares[int(0.975 * resamples) - 1],
    )


def percentile(values: Sequence[float], share: float) -> float | None:
    """Nearest-rank percentile (`share` 0.5 for p50, 0.95 for p95)."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(share * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


@dataclass(frozen=True)
class Scores:
    fields: dict[str, FieldScore]
    critical: Interval
    documents: int


def score(truths: Sequence[Values], predictions: Sequence[Values]) -> Scores:
    return Scores(
        fields={field: score_field(field, truths, predictions) for field in FIELDS},
        critical=bootstrap(
            [critical_correct(t, p) for t, p in zip(truths, predictions, strict=True)]
        ),
        documents=len(truths),
    )

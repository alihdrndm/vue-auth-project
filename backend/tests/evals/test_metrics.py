"""Scoring, the bootstrap interval and percentiles (evals/metrics.py)."""

import pytest
from evals.metrics import Values

from evals import metrics


def doc(**values: str | None) -> Values:
    base: Values = dict.fromkeys(metrics.FIELDS)
    base.update(values)
    return base


@pytest.mark.parametrize(
    ("field", "truth", "predicted", "expected"),
    [
        ("issue_date", "2026-03-01", "2026-03-01", True),
        ("issue_date", "2026-03-01", "2026-03-02", False),
        ("issue_date", "2026-03-01", "01.03.2026", False),  # predictions are normalised ISO
        ("gross_total", "1190.00", "1190", True),
        ("gross_total", "1190.00", "1190.01", False),
        ("gross_total", "1190.00", "abc", False),
        ("payee_iban", "DE89370400440532013000", "de89 3704 0044 0532 0130 00", True),
        ("seller.vat_id", "DE123456789", "DE 123 456 789", True),
        ("currency", "EUR", "eur", True),
        ("invoice_number", "RE-2026 0412", "re-20260412", True),
        ("invoice_number", "RE-2026-0412", "RE-2026-0413", False),
        ("seller.name", "Elektro Kessler GmbH", "ELEKTRO KESSLER GMBH", True),
        ("seller.name", "Elektro Kessler GmbH", "Kessler Elektro", True),
        ("seller.name", "Elektro Kessler GmbH", "Druckerei Sommer GmbH", False),
        ("gross_total", None, "1.00", False),
        ("gross_total", "1.00", None, False),
    ],
)
def test_correct_normalises_each_kind(
    field: str, truth: str | None, predicted: str | None, expected: bool
) -> None:
    assert metrics.correct(field, truth, predicted) is expected


def test_field_score_counts_accuracy_hallucination_and_abstention() -> None:
    truths = [doc(due_date="2026-04-01"), doc(due_date="2026-04-02"), doc(), doc()]
    predictions = [doc(due_date="2026-04-01"), doc(), doc(due_date="2026-05-01"), doc()]
    result = metrics.score_field("due_date", truths, predictions)
    assert result.accuracy == 0.5  # one of the two present values right
    assert result.abstention == 0.5  # one of the two present values not predicted
    assert result.hallucination == 0.5  # one of the two absent values invented


def test_field_score_is_none_without_a_denominator() -> None:
    result = metrics.score_field("due_date", [doc()], [doc()])
    assert (result.accuracy, result.abstention, result.hallucination) == (None, None, 0.0)


def test_critical_needs_the_iban_only_when_the_truth_has_one() -> None:
    truth = doc(invoice_number="A1", issue_date="2026-01-01", gross_total="10.00")
    assert metrics.critical_correct(truth, dict(truth))
    with_iban = {**truth, "payee_iban": "DE89370400440532013000"}
    assert not metrics.critical_correct(with_iban, dict(truth))


def test_bootstrap_is_seeded_and_brackets_the_value() -> None:
    outcomes = [True] * 70 + [False] * 30
    first, second = metrics.bootstrap(outcomes), metrics.bootstrap(outcomes)
    assert first == second
    assert first.value == 0.7
    assert first.ci_low < 0.7 < first.ci_high
    assert metrics.bootstrap([]) == metrics.Interval(0.0, 0.0, 0.0)


def test_percentile_is_nearest_rank() -> None:
    values = [float(n) for n in range(1, 101)]
    assert metrics.percentile(values, 0.5) == 50.0
    assert metrics.percentile(values, 0.95) == 95.0
    assert metrics.percentile([], 0.5) is None
    assert metrics.percentile([7.0], 0.95) == 7.0


def test_score_covers_every_field_and_the_critical_interval() -> None:
    truth = doc(invoice_number="A1", issue_date="2026-01-01", gross_total="10.00")
    scores = metrics.score([truth, truth], [truth, doc()])
    assert set(scores.fields) == set(metrics.FIELDS)
    assert scores.documents == 2
    assert scores.critical.value == 0.5

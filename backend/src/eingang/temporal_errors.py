"""Errors that stop a Temporal activity from retrying (HANDOFF "Python code rules").

Both pass their `type` to ApplicationError so Temporal can recognise them: the retry policy
lists them as non-retryable, and the workflow (which never imports these classes) reads
`err.cause.type` and `err.cause.details` from the ActivityError.
"""

from temporalio.exceptions import ApplicationError

from eingang.workflows.contracts import BUDGET_EXCEEDED_ERROR_TYPE, PERMANENT_ERROR_TYPE

UNAVAILABLE_REASONS = frozenset(
    {"disabled", "budget_lifetime", "budget_monthly", "budget_daily_public", "sandbox_limit"}
)


class PermanentError(ApplicationError):
    """The input itself is wrong (corrupt PDF, unparsable XML); retrying cannot help."""

    def __init__(self, message: str) -> None:
        super().__init__(message, type=PERMANENT_ERROR_TYPE, non_retryable=True)


class BudgetExceededError(ApplicationError):
    """An LLM call was refused before it was made; `reason` says why."""

    def __init__(self, reason: str) -> None:
        if reason not in UNAVAILABLE_REASONS:
            raise ValueError(f"unknown unavailable reason: {reason}")
        super().__init__(
            f"LLM call refused: {reason}",
            reason,
            type=BUDGET_EXCEEDED_ERROR_TYPE,
            non_retryable=True,
        )
        self.reason = reason

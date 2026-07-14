"""`GET /stats` (HANDOFF "HTTP API"; "LLM usage and budget")."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from accounts.models import Organization
from eingang import clock
from eingang.config import Settings, get_settings
from invoices import stats_api
from invoices.models import Document, Event
from llm.models import LlmCall
from tests.conftest import NOW, ApiClient, MakeUser
from tests.factories import add_check, make_document

pytestmark = pytest.mark.django_db

Status = Document.Status


def stats(api: ApiClient) -> dict[str, object]:
    response = api.get("/api/v1/stats")
    assert response.status_code == 200
    body: dict[str, object] = response.json()
    return body


def with_settings(monkeypatch: pytest.MonkeyPatch, **values: Decimal | int | None) -> None:
    changed: Settings = get_settings().model_copy(update=values)
    monkeypatch.setattr(stats_api, "get_settings", lambda: changed)


def ledger_row(cost: str, created_at: datetime, organization: Organization | None = None) -> None:
    call = LlmCall.objects.create(
        organization=organization,
        purpose="extract",
        prompt_version="v1",
        cost=Decimal(cost),
        status=LlmCall.Status.OK,
    )
    LlmCall.objects.filter(id=call.id).update(created_at=created_at)


def remind(document: Document) -> None:
    Event.objects.create(
        organization=document.organization, document=document, type=Event.Type.REMINDER_SENT
    )


def test_stats_by_status_counts_every_status_of_live_documents(
    signed_in: Callable[[str], ApiClient],
    organization: Organization,
    other_organization: Organization,
) -> None:
    make_document(organization, status=Status.NEEDS_REVIEW)
    make_document(organization, status=Status.NEEDS_REVIEW)
    make_document(organization, status=Status.APPROVED)
    deleted = make_document(organization, status=Status.NEEDS_REVIEW)
    Document.objects.filter(id=deleted.id).update(deleted_at=NOW)
    make_document(other_organization, status=Status.FAILED)
    assert stats(signed_in("viewer"))["by_status"] == {
        "received": 0,
        "processing": 0,
        "needs_review": 2,
        "awaiting_approval": 0,
        "approved": 1,
        "rejected": 0,
        "exported": 0,
        "failed": 0,
    }


def test_stats_blocked_counts_documents_with_an_unresolved_block_check(
    signed_in: Callable[[str], ApiClient],
    organization: Organization,
    other_organization: Organization,
) -> None:
    twice = make_document(organization)
    add_check(twice, "C05", "block")
    add_check(twice, "C15", "block")
    add_check(make_document(organization), "C05", "block")
    add_check(make_document(organization), "C13", "warn")
    resolved = add_check(make_document(organization), "C05", "block")
    resolved.resolved_at = NOW
    resolved.save()
    deleted = make_document(organization)
    add_check(deleted, "C05", "block")
    Document.objects.filter(id=deleted.id).update(deleted_at=NOW)
    add_check(make_document(other_organization), "C05", "block")
    assert stats(signed_in("viewer"))["blocked"] == 2


def test_stats_overdue_counts_awaiting_approval_with_a_reminder(
    signed_in: Callable[[str], ApiClient],
    organization: Organization,
    other_organization: Organization,
) -> None:
    overdue = make_document(organization, status=Status.AWAITING_APPROVAL)
    remind(overdue)
    remind(overdue)
    make_document(organization, status=Status.AWAITING_APPROVAL)  # no reminder yet
    remind(make_document(organization, status=Status.APPROVED))
    remind(make_document(other_organization, status=Status.AWAITING_APPROVAL))
    assert stats(signed_in("viewer"))["overdue"] == 1


@pytest.mark.parametrize(
    ("role", "expected"), [("admin", 2), ("approver", 2), ("accountant", 0), ("viewer", 0)]
)
def test_stats_awaiting_my_approval_by_role(
    role: str,
    expected: int,
    signed_in: Callable[[str], ApiClient],
    organization: Organization,
    other_organization: Organization,
) -> None:
    make_document(organization, status=Status.AWAITING_APPROVAL)
    make_document(organization, status=Status.AWAITING_APPROVAL)
    make_document(organization, status=Status.NEEDS_REVIEW)
    make_document(other_organization, status=Status.AWAITING_APPROVAL)
    assert stats(signed_in(role))["awaiting_my_approval"] == expected


def test_stats_awaiting_my_approval_leaves_out_FOUR_EYES_documents(
    api: ApiClient, make_user: MakeUser, organization: Organization
) -> None:
    admin = make_user("admin")
    reviewer = make_user("accountant")
    make_document(organization, status=Status.AWAITING_APPROVAL, reviewed_by=admin)
    make_document(organization, status=Status.AWAITING_APPROVAL, reviewed_by=reviewer)
    api.sign_in(admin)
    assert stats(api)["awaiting_my_approval"] == 1
    organization.four_eyes = False
    organization.save()
    assert stats(api)["awaiting_my_approval"] == 2


def test_stats_llm_spend_and_budgets(
    monkeypatch: pytest.MonkeyPatch,
    fixed_clock: clock.FixedClock,
    signed_in: Callable[[str], ApiClient],
    organization: Organization,
    other_organization: Organization,
) -> None:
    with_settings(
        monkeypatch,
        LLM_BUDGET_USD_LIFETIME=Decimal("2.00"),
        LLM_SPENT_ELSEWHERE_USD=Decimal("0.25"),
        LLM_BUDGET_USD_MONTHLY=Decimal("1.5"),
    )
    month_start = datetime(2026, 3, 1, tzinfo=UTC)
    ledger_row("0.104000", month_start, organization)  # this month
    ledger_row("0.021000", NOW, other_organization)  # this month, any organisation
    ledger_row("0.300000", month_start - timedelta(microseconds=1))  # February
    ledger_row("0.050000", datetime(2026, 4, 1, tzinfo=UTC))  # next month
    llm = stats(signed_in("viewer"))["llm"]
    # Lifetime: every row (0.475) plus the spend elsewhere (0.25); both round half up.
    assert llm == {
        "lifetime_spent_usd": "0.73",
        "lifetime_budget_usd": "2.00",
        "month_spent_usd": "0.13",
        "month_budget_usd": "1.50",
    }


def test_stats_llm_spend_without_ledger_rows_or_spend_elsewhere(
    monkeypatch: pytest.MonkeyPatch,
    fixed_clock: clock.FixedClock,
    signed_in: Callable[[str], ApiClient],
) -> None:
    with_settings(monkeypatch, LLM_SPENT_ELSEWHERE_USD=None)
    llm = stats(signed_in("viewer"))["llm"]
    assert isinstance(llm, dict)
    assert (llm["lifetime_spent_usd"], llm["month_spent_usd"]) == ("0.00", "0.00")


def test_stats_month_is_the_utc_calendar_month_in_december(
    fixed_clock: clock.FixedClock, signed_in: Callable[[str], ApiClient]
) -> None:
    fixed_clock.moment = datetime(2026, 12, 31, 23, 59, tzinfo=UTC)
    ledger_row("0.10", datetime(2026, 12, 1, tzinfo=UTC))
    ledger_row("0.20", datetime(2027, 1, 1, tzinfo=UTC))
    llm = stats(signed_in("viewer"))["llm"]
    assert isinstance(llm, dict)
    assert llm["month_spent_usd"] == "0.10"


@pytest.mark.parametrize(("used", "left"), [(0, 3), (2, 1), (3, 0), (5, 0)])
def test_stats_sandbox_calls_left(
    used: int,
    left: int,
    monkeypatch: pytest.MonkeyPatch,
    fixed_clock: clock.FixedClock,
    api: ApiClient,
    make_user: MakeUser,
) -> None:
    with_settings(monkeypatch, LLM_MAX_CALLS_PER_SANDBOX=3)
    sandbox = Organization.objects.create(
        name="Sandbox",
        slug="sandbox-test",
        kind=Organization.Kind.SANDBOX,
        expires_at=NOW + timedelta(hours=24),
        llm_calls_used=used,
    )
    api.sign_in(make_user("admin", org=sandbox))
    llm = stats(api)["llm"]
    assert isinstance(llm, dict)
    assert llm["sandbox_calls_left"] == left


def test_stats_standard_organization_has_no_sandbox_calls_left(
    signed_in: Callable[[str], ApiClient],
) -> None:
    llm = stats(signed_in("admin"))["llm"]
    assert isinstance(llm, dict)
    assert "sandbox_calls_left" not in llm


def test_stats_need_a_session_NOT_AUTHENTICATED(api: ApiClient) -> None:
    response = api.get("/api/v1/stats")
    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"

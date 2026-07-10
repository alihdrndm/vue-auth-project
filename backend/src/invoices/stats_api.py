"""Dashboard figures (HTTP API: `GET /stats`).

Document counts cover the signed-in user's organisation and its non-deleted documents. The
LLM figures follow the budget rules ("LLM usage and budget"): the lifetime spend is the
whole ledger of this database plus the spend recorded elsewhere, and the month is the
current UTC calendar month.
"""

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Exists, OuterRef, Q, QuerySet, Sum
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Organization, User
from accounts.permissions import AnyMember, signed_in_user
from accounts.scoping import scoped
from eingang import clock
from eingang.config import get_settings
from invoices.actions import allowed_actions
from invoices.models import Check, Document, Event
from invoices.stats_serializers import StatsSerializer
from llm.models import LlmCall

TAGS = ["stats"]
CENT = Decimal("0.01")
Status = Document.Status


def usd(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def month_bounds(moment: datetime) -> tuple[datetime, datetime]:
    """The start of the UTC calendar month that contains `moment`, and of the next one."""
    utc = moment.astimezone(UTC)
    start = datetime(utc.year, utc.month, 1, tzinfo=UTC)
    if utc.month == 12:
        return start, datetime(utc.year + 1, 1, 1, tzinfo=UTC)
    return start, datetime(utc.year, utc.month + 1, 1, tzinfo=UTC)


def ledger_total(calls: QuerySet[LlmCall]) -> Decimal:
    total: Decimal | None = calls.aggregate(total=Sum("cost"))["total"]
    return total if total is not None else Decimal(0)


def llm_stats(organization: Organization) -> dict[str, Decimal | int]:
    settings = get_settings()
    month_start, next_month = month_bounds(clock.now())
    elsewhere = settings.LLM_SPENT_ELSEWHERE_USD or Decimal(0)
    month_calls = LlmCall.objects.filter(created_at__gte=month_start, created_at__lt=next_month)
    stats: dict[str, Decimal | int] = {
        "lifetime_spent_usd": usd(ledger_total(LlmCall.objects.all()) + elsewhere),
        "lifetime_budget_usd": usd(settings.LLM_BUDGET_USD_LIFETIME),
        "month_spent_usd": usd(ledger_total(month_calls)),
        "month_budget_usd": usd(settings.LLM_BUDGET_USD_MONTHLY),
    }
    if organization.is_sandbox:
        left = settings.LLM_MAX_CALLS_PER_SANDBOX - organization.llm_calls_used
        stats["sandbox_calls_left"] = max(0, left)
    return stats


def status_counts(documents: QuerySet[Document]) -> dict[str, int]:
    counts = {status.value: 0 for status in Status}
    for row in documents.values("status").annotate(count=Count("id")):
        counts[row["status"]] = row["count"]
    return counts


def awaiting_my_approval(documents: QuerySet[Document], user: User) -> int:
    """Documents awaiting approval on which `allowed_actions` offers this user "approve"."""
    awaiting = (
        documents.filter(status=Status.AWAITING_APPROVAL)
        .select_related("organization")
        .annotate(
            open_blocks=Count(
                "checks",
                filter=Q(checks__severity=Check.Severity.BLOCK, checks__resolved_at__isnull=True),
            )
        )
    )
    return sum(
        1
        for document in awaiting
        if any(
            entry.action == "approve" and entry.enabled
            for entry in allowed_actions(document, user, blocking_checks=document.open_blocks)
        )
    )


class StatsView(APIView):
    permission_classes = (AnyMember,)

    @extend_schema(responses={200: StatsSerializer}, tags=TAGS)
    def get(self, request: Request) -> Response:
        user = signed_in_user(request)
        if user is None:
            raise NotAuthenticated
        documents = scoped(Document.objects.all(), request).filter(deleted_at__isnull=True)
        open_block = Check.objects.filter(
            document=OuterRef("pk"), severity=Check.Severity.BLOCK, resolved_at__isnull=True
        )
        reminder = Event.objects.filter(document=OuterRef("pk"), type=Event.Type.REMINDER_SENT)
        payload = {
            "by_status": status_counts(documents),
            "blocked": documents.filter(Exists(open_block)).count(),
            "overdue": documents.filter(status=Status.AWAITING_APPROVAL)
            .filter(Exists(reminder))
            .count(),
            "awaiting_my_approval": awaiting_my_approval(documents, user),
            "llm": llm_stats(user.organization),
        }
        return Response(StatsSerializer(payload).data)

"""The one place that limits a query to the signed-in user's organisation (IDOR protection).

Every view that reads or changes organisation data gets its queryset from `scoped`; an
object of another organisation is then simply not found (404), never revealed.
"""

from django.db.models import Model, QuerySet
from rest_framework.request import Request

from accounts.models import Organization, User


def organization_of(request: Request) -> Organization:
    user = request.user
    if not isinstance(user, User):
        # Views using this helper always require a signed-in user first.
        raise TypeError("scoped queries need a signed-in user")
    return user.organization


def scoped[M: Model](queryset: QuerySet[M], request: Request) -> QuerySet[M]:
    return queryset.filter(organization=organization_of(request))

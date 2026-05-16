"""One DRF permission class per role rule of the "HTTP API" table.

A signed-in user whose role is not allowed gets 403 FORBIDDEN_ROLE (the exception handler
maps DRF's PermissionDenied to it). Anonymous requests get 401 NOT_AUTHENTICATED first.
"""

from typing import TYPE_CHECKING

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

if TYPE_CHECKING:
    # DRF imports these classes while rest_framework.views is still loading.
    from rest_framework.views import APIView

from accounts.models import User
from eingang.problem import ProblemError

Role = User.Role


def signed_in_user(request: Request) -> User | None:
    user = request.user
    return user if isinstance(user, User) and user.is_active else None


class _RolePermission(BasePermission):
    roles: frozenset[str] = frozenset()

    def has_permission(self, request: Request, view: "APIView") -> bool:
        user = signed_in_user(request)
        return user is not None and user.role in self.roles


class AnyMember(_RolePermission):
    """All roles: admin, accountant, approver, viewer."""

    roles = frozenset({Role.ADMIN, Role.ACCOUNTANT, Role.APPROVER, Role.VIEWER})


class AdminOrAccountant(_RolePermission):
    roles = frozenset({Role.ADMIN, Role.ACCOUNTANT})


class AdminOrApprover(_RolePermission):
    roles = frozenset({Role.ADMIN, Role.APPROVER})


class AdminOnly(_RolePermission):
    roles = frozenset({Role.ADMIN})


def sandbox_restricted() -> ProblemError:
    return ProblemError(
        403, "SANDBOX_RESTRICTED", "Not available in the sandbox", "Not available in the sandbox."
    )


class NotInSandbox(BasePermission):
    """For actions a sandbox visitor may not take (members, most organisation settings)."""

    def has_permission(self, request: Request, view: "APIView") -> bool:
        user = signed_in_user(request)
        if user is not None and user.organization.is_sandbox:
            raise sandbox_restricted()
        return True

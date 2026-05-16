"""Rate limits (HANDOFF "Rate limits"): per client IP, per user, and for the sandbox.

The client IP comes from DRF's `get_ident`, which trusts exactly `NUM_PROXIES` hops of
`X-Forwarded-For` (settings: TRUSTED_PROXY_HOPS). A client cannot pick its own key by
sending that header itself.
"""

from typing import TYPE_CHECKING

from rest_framework.request import Request

if TYPE_CHECKING:
    # DRF imports these classes while rest_framework.views is still loading.
    from rest_framework.views import APIView
from rest_framework.throttling import SimpleRateThrottle


class _PerClientIp(SimpleRateThrottle):
    def get_cache_key(self, request: Request, view: "APIView") -> str | None:
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class GeneralThrottle(_PerClientIp):
    """120 requests per minute per client IP, on every endpoint."""

    scope = "general"


class LoginThrottle(_PerClientIp):
    scope = "login"


class SandboxPerIpThrottle(_PerClientIp):
    scope = "sandbox"


class UploadThrottle(SimpleRateThrottle):
    """30 uploads per minute per signed-in user."""

    scope = "uploads"

    def get_cache_key(self, request: Request, view: "APIView") -> str | None:
        user_id = getattr(request.user, "pk", None)
        if user_id is None:
            return None
        return self.cache_format % {"scope": self.scope, "ident": str(user_id)}

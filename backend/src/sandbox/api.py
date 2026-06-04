"""`POST /api/v1/sandbox`: open a sandbox and sign the visitor in."""

from django.contrib.auth import login
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import SessionSerializer, session_payload
from eingang import clock
from eingang.config import get_settings
from eingang.problem import ProblemError
from eingang.throttles import GeneralThrottle, SandboxPerIpThrottle
from sandbox.services import create_sandbox, sandboxes_created_last_day


def sandbox_limit(wait_seconds: float | None = None) -> ProblemError:
    headers = {} if wait_seconds is None else {"Retry-After": str(max(1, round(wait_seconds)))}
    return ProblemError(
        429,
        "SANDBOX_LIMIT",
        "Too many sandboxes",
        "Too many sandboxes were opened recently. Please try again later.",
        headers=headers,
    )


class SandboxView(APIView):
    authentication_classes = ()
    permission_classes = ()
    throttle_classes = (GeneralThrottle, SandboxPerIpThrottle)

    def check_throttles(self, request: Request) -> None:
        # Only the sandbox limit answers SANDBOX_LIMIT; the general limit stays RATE_LIMITED.
        for throttle in self.get_throttles():
            if not throttle.allow_request(request, self):
                if isinstance(throttle, SandboxPerIpThrottle):
                    raise sandbox_limit(throttle.wait())
                wait = throttle.wait()
                self.throttled(request, wait if wait is not None else 0.0)

    @extend_schema(
        request=None,
        responses={201: SessionSerializer, 429: OpenApiResponse(description="SANDBOX_LIMIT")},
        tags=["sandbox"],
    )
    @method_decorator(csrf_protect)
    def post(self, request: Request) -> Response:
        if sandboxes_created_last_day() >= get_settings().SANDBOX_DAILY_LIMIT:
            raise sandbox_limit()
        visitor = create_sandbox()
        login(request._request, visitor)
        # A visitor cannot sign in again, so the session lasts exactly as long as the sandbox.
        # The age is relative, so it also holds under the injected clock in tests.
        expires_at = visitor.organization.expires_at
        if expires_at is None:
            raise RuntimeError("a sandbox always has an expiry")
        request.session.set_expiry(int((expires_at - clock.now()).total_seconds()))
        return Response(session_payload(visitor), status=201)

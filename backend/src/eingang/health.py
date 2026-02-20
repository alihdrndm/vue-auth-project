"""Liveness (`/healthz`) and readiness (`/readyz`) endpoints. No authentication."""

from concurrent.futures import ThreadPoolExecutor

from django.db import connections
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from eingang import temporal_client
from eingang.problem import ProblemError

CHECK_TIMEOUT_SECONDS = 2.0


def database_is_reachable(timeout: float) -> bool:
    def ping() -> None:
        # Runs in its own thread, so Django opens (and we close) a separate connection.
        connection = connections["default"]
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        finally:
            connection.close()

    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="readyz-db")
    try:
        executor.submit(ping).result(timeout=timeout)
    except Exception:  # a timeout or any database error both mean "not reachable"
        return False
    finally:
        # Never wait for a hung connection attempt; the thread ends on its own.
        executor.shutdown(wait=False)
    return True


def temporal_is_reachable(timeout: float) -> bool:
    return temporal_client.is_healthy(timeout)


_status_serializer = inline_serializer("HealthStatus", {"status": serializers.CharField()})


class HealthzView(APIView):
    authentication_classes = ()
    permission_classes = ()

    @extend_schema(responses={200: _status_serializer}, tags=["health"])
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class ReadyzView(APIView):
    authentication_classes = ()
    permission_classes = ()

    @extend_schema(
        responses={
            200: inline_serializer(
                "ReadyStatus",
                {"status": serializers.CharField(), "checks": serializers.DictField()},
            ),
            503: OpenApiResponse(
                description="NOT_READY problem+json; `checks` names what is unreachable."
            ),
        },
        tags=["health"],
    )
    def get(self, request: Request) -> Response:
        checks = {
            "database": "ok" if database_is_reachable(CHECK_TIMEOUT_SECONDS) else "unreachable",
            "temporal": "ok" if temporal_is_reachable(CHECK_TIMEOUT_SECONDS) else "unreachable",
        }
        failed = [name for name, state in checks.items() if state != "ok"]
        if failed:
            raise ProblemError(
                503,
                "NOT_READY",
                "Not ready",
                f"Unreachable: {', '.join(failed)}.",
                extra={"checks": checks},
            )
        return Response({"status": "ok", "checks": checks})

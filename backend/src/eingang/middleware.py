"""Request id, the one request log line, and problem+json for errors outside DRF views."""

import logging
import re
import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from uuid_utils.compat import uuid7

from eingang import problem
from eingang.log import request_id_var

logger = logging.getLogger("eingang.request")

REQUEST_ID_HEADER = "x-request-id"
# A client-supplied id is echoed and logged, so only accept a short, harmless token.
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")


def _request_id_from(request: HttpRequest) -> str:
    supplied = request.headers.get(REQUEST_ID_HEADER, "")
    if _VALID_REQUEST_ID.fullmatch(supplied):
        return supplied
    return str(uuid7())


class RequestContextMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = _request_id_from(request)
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = self.get_response(request)
            if response.status_code == 404 and not _is_problem(response):
                # Unknown routes: Django's own 404 page (HTML, or the debug page) is replaced.
                response = problem.not_found()
            response[REQUEST_ID_HEADER] = request_id
            duration_ms = round((time.perf_counter() - started) * 1000)
            # request.path never includes the query string, which can contain names.
            logger.info(
                "%s %s %s %dms",
                request.method,
                request.path,
                response.status_code,
                duration_ms,
            )
            return response
        finally:
            request_id_var.reset(token)

    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse:
        logger.exception("Unhandled exception in %s %s", request.method, request.path)
        return problem.internal_error()


def _is_problem(response: HttpResponse) -> bool:
    return response.get("Content-Type", "").startswith(problem.PROBLEM_CONTENT_TYPE)

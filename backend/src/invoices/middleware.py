"""Limits every multipart upload before anything reads the request body.

The CSRF check reads `request.POST`, which parses the whole multipart body; by the time a
view runs it is too late to choose how the body is read. So this middleware refuses an
oversized body outright and installs the size-limited handler first.
"""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from eingang.config import get_settings
from eingang.problem import ProblemError, from_problem_error
from invoices.uploads import SizeLimitedUploadHandler, check_request_size


class UploadLimitMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.method == "POST" and request.content_type == "multipart/form-data":
            try:
                check_request_size(request.META.get("CONTENT_LENGTH"))
            except ProblemError as error:
                return from_problem_error(error)
            request.upload_handlers = [SizeLimitedUploadHandler(get_settings().MAX_UPLOAD_BYTES)]
        return self.get_response(request)

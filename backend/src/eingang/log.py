"""Logging set-up and the request id that every log line carries."""

from contextvars import ContextVar
from logging import Filter, LogRecord
from typing import Any

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(Filter):
    def filter(self, record: LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def logging_config(*, json_logs: bool) -> dict[str, Any]:  # boundary: logging.config dict schema
    formatter: dict[str, str]
    if json_logs:
        formatter = {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
        }
    else:
        formatter = {"format": "%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s"}
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"request_id": {"()": "eingang.log.RequestIdFilter"}},
        "formatters": {"default": formatter},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "filters": ["request_id"],
            }
        },
        "root": {"handlers": ["console"], "level": "INFO"},
        "loggers": {
            # The dev server's access log prints query strings, which can contain names.
            # Our own request log line (eingang.request) replaces it.
            "django.server": {"handlers": [], "level": "CRITICAL", "propagate": False},
        },
    }

"""Typed configuration, read once from the environment at start-up.

This is the only module that reads environment variables. Everything else
asks for `get_settings()`.
"""

import sys
from functools import cache
from typing import Literal

from pydantic import Field, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Development default only; the validator below rejects it when DJANGO_DEBUG is false.
DEV_SECRET_KEY = "dev-insecure-secret-key-change-me"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    DJANGO_SECRET_KEY: str = DEV_SECRET_KEY
    DJANGO_DEBUG: bool = True
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    FRONTEND_ORIGIN: str = "http://localhost:3110"
    DATABASE_URL: str = "postgres://eingang:eingang@localhost:5452/eingang"

    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    S3_ENDPOINT_URL: str = ""
    S3_REGION: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET: str = "documents"

    # Proxy hops in front of the API whose X-Forwarded-For entries are trusted (rate limits).
    TRUSTED_PROXY_HOPS: int = Field(default=0, ge=0)

    TEMPORAL_ADDRESS: str = "localhost:7233"
    TEMPORAL_NAMESPACE: str = "eingang"

    MAX_UPLOAD_BYTES: int = Field(default=4_194_304, gt=0)
    SANDBOX_TTL_HOURS: int = Field(default=24, gt=0)
    SANDBOX_DAILY_LIMIT: int = Field(default=50, ge=0)
    SANDBOX_MAX_UPLOADS: int = Field(default=10, ge=0)
    SANDBOX_STORAGE_BUDGET_BYTES: int = Field(default=314_572_800, ge=0)
    COMPARE_HYBRID_PDF: bool = True
    SEED_PASSWORD: str = "eingang-dev"  # noqa: S105 - local seed users only

    MAILBOX_ENABLED: bool = False
    MAILBOX_HOST: str = ""
    MAILBOX_PORT: int = 993
    MAILBOX_USER: str = ""
    MAILBOX_PASSWORD: str = ""
    MAILBOX_ORG_SLUG: str = ""

    LLM_ENABLED: bool = False

    @property
    def allowed_hosts(self) -> list[str]:
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]

    @model_validator(mode="after")
    def _production_needs_real_values(self) -> "Settings":
        problems: list[str] = []
        if not self.DJANGO_DEBUG and self.DJANGO_SECRET_KEY == DEV_SECRET_KEY:
            problems.append("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false")
        if self.STORAGE_BACKEND == "s3":
            required = {
                "S3_ENDPOINT_URL": self.S3_ENDPOINT_URL,
                "S3_ACCESS_KEY_ID": self.S3_ACCESS_KEY_ID,
                "S3_SECRET_ACCESS_KEY": self.S3_SECRET_ACCESS_KEY,
            }
            problems += [
                f"{name} is required when STORAGE_BACKEND=s3"
                for name, value in required.items()
                if not value
            ]
        if self.MAILBOX_ENABLED:
            required = {
                "MAILBOX_HOST": self.MAILBOX_HOST,
                "MAILBOX_USER": self.MAILBOX_USER,
                "MAILBOX_PASSWORD": self.MAILBOX_PASSWORD,
                "MAILBOX_ORG_SLUG": self.MAILBOX_ORG_SLUG,
            }
            problems += [
                f"{name} is required when MAILBOX_ENABLED=true"
                for name, value in required.items()
                if not value
            ]
        if problems:
            raise ValueError("; ".join(problems))
        return self


def format_problems(error: ValidationError) -> list[str]:
    lines = []
    for item in error.errors():
        location = ".".join(str(part) for part in item["loc"]) or "configuration"
        lines.append(f"{location}: {item['msg']}")
    return lines


@cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as error:
        # Print every problem at once so a deploy needs one fix round, not one per variable.
        print("Invalid configuration:", file=sys.stderr)
        for line in format_problems(error):
            print(f"  - {line}", file=sys.stderr)
        sys.exit(1)

"""The LLM ledger and response cache (HANDOFF "LLM usage and budget").

Nothing in the application deletes rows of either table: they protect real money.
"""

from django.db import models

from accounts.models import Organization
from eingang import clock
from eingang.db import BaseModel


class LlmCall(BaseModel):
    """One ledger row per LLM call, success or failure. Never holds prompt or response text."""

    class Status(models.TextChoices):
        OK = "ok"
        ERROR = "error"
        REFUSED_BUDGET = "refused_budget"
        REFUSED_DISABLED = "refused_disabled"

    # ON DELETE SET NULL in the database itself, not only in Django: deleting a sandbox,
    # by any route, keeps its spend on record (spec: the ledger is never deleted).
    organization = models.ForeignKey(
        Organization,
        on_delete=models.DB_SET_NULL,
        null=True,
        blank=True,
        related_name="llm_calls",
    )
    purpose = models.CharField(max_length=64)
    model = models.CharField(max_length=100, null=True, blank=True)
    prompt_version = models.CharField(max_length=32)
    input_tokens = models.PositiveIntegerField(default=0)
    cached_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    cache_hit = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices)
    # Made for a demo (sandbox) visitor. Stored, because a deleted sandbox's spend must
    # still count against today's public budget.
    is_public = models.BooleanField(default=False)
    # From the injected clock, so the monthly and daily budget windows can be tested.
    created_at = models.DateTimeField(default=clock.now)

    class Meta:
        db_table = "llm_calls"

    def __str__(self) -> str:
        return str(self.id)


class LlmCache(models.Model):
    # SHA-256 of model + prompt version + exact input messages + output schema JSON.
    request_hash = models.CharField(max_length=64, primary_key=True)
    response_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "llm_cache"

    def __str__(self) -> str:
        return self.request_hash

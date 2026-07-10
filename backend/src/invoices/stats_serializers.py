"""Response shape of `GET /stats` (HANDOFF "HTTP API")."""

from rest_framework import serializers

from eingang.serializers import Serializer


class StatusCountsSerializer(Serializer):
    """Non-deleted documents of the organisation per status; every status is present."""

    received = serializers.IntegerField()
    processing = serializers.IntegerField()
    needs_review = serializers.IntegerField()
    awaiting_approval = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    exported = serializers.IntegerField()
    failed = serializers.IntegerField()


class LlmStatsSerializer(Serializer):
    """LLM spend and budgets in USD, as strings with 2 decimals."""

    lifetime_spent_usd = serializers.DecimalField(max_digits=14, decimal_places=2)
    lifetime_budget_usd = serializers.DecimalField(max_digits=14, decimal_places=2)
    month_spent_usd = serializers.DecimalField(max_digits=14, decimal_places=2)
    month_budget_usd = serializers.DecimalField(max_digits=14, decimal_places=2)
    # Sandboxes only; omitted for standard organisations.
    sandbox_calls_left = serializers.IntegerField(required=False)


class StatsSerializer(Serializer):
    by_status = StatusCountsSerializer()
    blocked = serializers.IntegerField()
    overdue = serializers.IntegerField()
    awaiting_my_approval = serializers.IntegerField()
    llm = LlmStatsSerializer()

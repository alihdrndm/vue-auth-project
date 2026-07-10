"""Response shape of `GET /rules/{rule_id}` (HANDOFF "HTTP API", section 7)."""

from rest_framework import serializers

from invoices.models import RuleExplanation


class RuleExplanationSerializer(serializers.ModelSerializer[RuleExplanation]):
    class Meta:
        model = RuleExplanation
        fields = ("rule_id", "plain_text", "fix_hint", "source")

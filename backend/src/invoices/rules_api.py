"""Rule explanations (HTTP API: `GET /rules/{rule_id}`, section 7).

Explanations are global, not per organisation, so the lookup is not scoped.
"""

import re

from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import AnyMember
from invoices.models import RuleExplanation
from invoices.rules_serializers import RuleExplanationSerializer

TAGS = ["rules"]
RULE_ID = re.compile(r"[A-Za-z0-9._-]+")


class RuleExplanationView(APIView):
    permission_classes = (AnyMember,)

    @extend_schema(responses={200: RuleExplanationSerializer}, tags=TAGS)
    def get(self, request: Request, rule_id: str) -> Response:
        if not RULE_ID.fullmatch(rule_id):
            raise Http404
        explanation = RuleExplanation.objects.filter(rule_id=rule_id).first()
        if explanation is None:
            raise Http404
        return Response(RuleExplanationSerializer(explanation).data)

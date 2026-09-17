"""Public evaluation results (HTTP API: `GET /accuracy`; HANDOFF "Evaluation").

Serves `evals/latest.json`, validated with `LatestReport`. No session is needed; the general
per-IP rate limit applies. Fields that are not set are left out of the response.

The serializers below only describe the response in the OpenAPI schema: the Pydantic models
in `eingang.accuracy` validate it. (drf-spectacular's Pydantic support writes JSON Schema
`null` types, which OpenAPI 3.0 does not allow.) A test keeps the two in step.
"""

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from eingang.accuracy import SCORED_FIELDS, LatestReport
from eingang.problem import ProblemError
from eingang.serializers import Serializer


class AccuracyDatasetSerializer(Serializer):
    """The evaluation dataset."""

    name = serializers.CharField()
    documents = serializers.IntegerField()
    corpus_commit = serializers.CharField()


class CriticalCorrectSerializer(Serializer):
    """Share of documents with all critical fields correct, with its 95% CI."""

    value = serializers.FloatField()
    ci_low = serializers.FloatField()
    ci_high = serializers.FloatField()


class FieldScoreSerializer(Serializer):
    """Rates for one field; a rate with no documents to count is omitted."""

    accuracy = serializers.FloatField(required=False)
    hallucination = serializers.FloatField(required=False)
    abstention = serializers.FloatField(required=False)


class SystemResultSerializer(Serializer):
    """Headline numbers of one system."""

    id = serializers.CharField()
    model = serializers.CharField(required=False)
    prompt_version = serializers.CharField(required=False)
    critical_correct = CriticalCorrectSerializer()
    cost_usd = serializers.DecimalField(max_digits=12, decimal_places=6)
    usd_per_doc = serializers.DecimalField(max_digits=12, decimal_places=6)
    latency_p50_ms = serializers.FloatField()
    latency_p95_ms = serializers.FloatField()

    def get_fields(self) -> dict[str, serializers.Field[object, object, object, object]]:
        fields = super().get_fields()
        # Declared here: a class attribute named `fields` would hide Serializer.fields.
        fields["fields"] = serializers.DictField(
            child=FieldScoreSerializer(), help_text=f"Keyed by field: {', '.join(SCORED_FIELDS)}."
        )
        return fields


class ParitySerializer(Serializer):
    """Validation parity with the official KoSIT validator."""

    files = serializers.IntegerField()
    excluded = serializers.IntegerField()
    verdict_agreement = serializers.FloatField()
    rule_set_agreement = serializers.FloatField()


class AccuracyReportSerializer(Serializer):
    """The published evaluation results (evals/latest.json)."""

    generated_at = serializers.DateTimeField()
    dataset = AccuracyDatasetSerializer()
    systems = SystemResultSerializer(many=True)
    parity = ParitySerializer(required=False)


def load_latest() -> LatestReport:
    """The published report; `404 NOT_AVAILABLE` when there is none yet."""
    try:
        raw = settings.EVALS_LATEST.read_bytes()
    except FileNotFoundError:
        raise ProblemError(
            404, "NOT_AVAILABLE", "Not available", "No evaluation results have been published."
        ) from None
    # An invalid file is a build error, so it surfaces as 500 INTERNAL.
    return LatestReport.model_validate_json(raw)


class AccuracyView(APIView):
    authentication_classes = ()
    permission_classes = ()

    @extend_schema(
        responses={
            200: AccuracyReportSerializer,
            404: OpenApiResponse(description="NOT_AVAILABLE: no results published yet."),
        },
        tags=["accuracy"],
    )
    def get(self, request: Request) -> Response:
        return Response(load_latest().model_dump(mode="json", exclude_none=True))

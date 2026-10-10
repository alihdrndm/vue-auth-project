"""Review endpoints (HTTP API): edit fields, resolve checks, review, decide, send back,
reopen and retry. Each answers with the updated document detail (resolve: the check).
"""

from typing import Any, ClassVar
from uuid import UUID

from django.http import Http404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import AdminOrAccountant, AdminOrApprover
from accounts.scoping import scoped
from eingang import temporal_client
from eingang.problem import ProblemError
from invoices import review
from invoices.api import current_user, get_document
from invoices.models import Check, Document, Invoice, InvoiceLine
from invoices.serializers import (
    CheckSerializer,
    DocumentDetailSerializer,
    check_entry,
    document_detail,
)

TAGS = ["documents"]


class LineEditSerializer(serializers.ModelSerializer[InvoiceLine]):
    class Meta:
        model = InvoiceLine
        fields = review.LINE_FIELDS
        extra_kwargs: ClassVar = {name: {"required": False} for name in review.LINE_FIELDS}


class InvoiceEditSerializer(serializers.ModelSerializer[Invoice]):
    lines = LineEditSerializer(many=True, required=False)

    class Meta:
        model = Invoice
        fields = (*review.EDITABLE_FIELDS, "lines")
        extra_kwargs: ClassVar = {name: {"required": False} for name in review.EDITABLE_FIELDS}


class NoteSerializer(serializers.Serializer[object]):
    note = serializers.CharField(allow_blank=True, trim_whitespace=False)


class CommentSerializer(serializers.Serializer[object]):
    comment = serializers.CharField(allow_blank=True, required=False, default="")


class DecisionSerializer(serializers.Serializer[object]):
    decision = serializers.ChoiceField(
        choices=[Document.Status.APPROVED.value, Document.Status.REJECTED.value]
    )
    comment = serializers.CharField(allow_blank=True, required=False, default="")


def _blank_to_none(value: Any) -> Any:  # boundary: drf data
    return None if value == "" else value


def _detail(request: Request, document_id: UUID, user: User) -> Response:
    return Response(document_detail(get_document(request, document_id), user))


def _payload[S: serializers.BaseSerializer[Any]](  # boundary: rest_framework serializer
    serializer: S,
) -> dict[str, Any]:  # boundary: rest_framework validated data
    serializer.is_valid(raise_exception=True)
    data: dict[str, Any] = dict(serializer.validated_data)  # boundary: drf data
    return data


DETAIL = {200: DocumentDetailSerializer}


class InvoiceEditView(APIView):
    permission_classes = (AdminOrAccountant,)

    @extend_schema(
        request=InvoiceEditSerializer,
        responses={**DETAIL, 409: OpenApiResponse(description="INVALID_TRANSITION")},
        tags=TAGS,
    )
    def patch(self, request: Request, document_id: UUID) -> Response:
        user = current_user(request)
        document = get_document(request, document_id)
        data = _payload(InvoiceEditSerializer(data=request.data, partial=True))
        lines = data.pop("lines", None)
        fields = {name: _blank_to_none(value) for name, value in data.items()}
        if lines is not None:
            lines = [{name: _blank_to_none(v) for name, v in line.items()} for line in lines]
        review.edit_invoice(document, user, fields, lines)
        return _detail(request, document_id, user)


class CheckResolveView(APIView):
    permission_classes = (AdminOrAccountant,)

    @extend_schema(
        request=NoteSerializer,
        responses={
            200: CheckSerializer,
            409: OpenApiResponse(description="CHECK_NOT_RESOLVABLE or INVALID_TRANSITION"),
        },
        tags=TAGS,
    )
    def post(self, request: Request, check_id: UUID) -> Response:
        user = current_user(request)
        check = (
            Check.objects.filter(
                id=check_id,
                document__in=scoped(Document.objects.filter(deleted_at__isnull=True), request),
            )
            .select_related("document")
            .first()
        )
        if check is None:
            raise Http404
        note = _payload(NoteSerializer(data=request.data))["note"]
        check = review.resolve_check(check, user, note)
        check = Check.objects.select_related("resolved_by", "document").get(pk=check.pk)
        return Response(CheckSerializer(check_entry(check, check.document, user)).data)


class MarkReviewedView(APIView):
    permission_classes = (AdminOrAccountant,)

    @extend_schema(
        request=None,
        responses={**DETAIL, 409: OpenApiResponse(description="BLOCKING_CHECKS")},
        tags=TAGS,
    )
    def post(self, request: Request, document_id: UUID) -> Response:
        user = current_user(request)
        review.mark_reviewed(get_document(request, document_id), user)
        return _detail(request, document_id, user)


class DecisionView(APIView):
    permission_classes = (AdminOrApprover,)

    @extend_schema(
        request=DecisionSerializer,
        responses={**DETAIL, 403: OpenApiResponse(description="FOUR_EYES")},
        tags=TAGS,
    )
    def post(self, request: Request, document_id: UUID) -> Response:
        user = current_user(request)
        data = _payload(DecisionSerializer(data=request.data))
        document = get_document(request, document_id)
        review.decide(document, user, data["decision"], data["comment"])
        return _detail(request, document_id, user)


class SendBackView(APIView):
    permission_classes = (AdminOrAccountant,)

    @extend_schema(request=CommentSerializer, responses=DETAIL, tags=TAGS)
    def post(self, request: Request, document_id: UUID) -> Response:
        user = current_user(request)
        data = _payload(CommentSerializer(data=request.data))
        review.send_back(get_document(request, document_id), user, data["comment"])
        return _detail(request, document_id, user)


class ReopenView(APIView):
    permission_classes = (AdminOrAccountant,)

    @extend_schema(request=None, responses=DETAIL, tags=TAGS)
    def post(self, request: Request, document_id: UUID) -> Response:
        user = current_user(request)
        review.reopen(get_document(request, document_id), user)
        return _detail(request, document_id, user)


class RetryView(APIView):
    permission_classes = (AdminOrAccountant,)

    @extend_schema(
        request=None,
        responses={**DETAIL, 503: OpenApiResponse(description="TEMPORAL_UNAVAILABLE")},
        tags=TAGS,
    )
    def post(self, request: Request, document_id: UUID) -> Response:
        user = current_user(request)
        try:
            review.retry(get_document(request, document_id), user)
        except temporal_client.TemporalUnavailableError as error:
            raise ProblemError(
                503,
                "TEMPORAL_UNAVAILABLE",
                "Processing unavailable",
                "Processing can't start right now. Try again in a few minutes.",
            ) from error
        return _detail(request, document_id, user)

"""Document endpoints (HTTP API: `/documents`)."""

import logging
from collections.abc import Sequence

from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import BaseParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import AdminOrAccountant, AnyMember, signed_in_user
from accounts.scoping import scoped
from eingang import temporal_client
from eingang.problem import ProblemError
from eingang.throttles import GeneralThrottle, UploadThrottle
from invoices.models import Document
from invoices.queries import DocumentListQuerySerializer, filter_documents
from invoices.serializers import (
    DocumentPageSerializer,
    DocumentSummarySerializer,
    document_summary,
    with_summary_data,
)
from invoices.uploads import (
    MAX_FILES_PER_REQUEST,
    SizeLimitedUploadHandler,
    file_too_large,
    store_uploads,
    too_many_files,
)

logger = logging.getLogger(__name__)
TAGS = ["documents"]


def current_user(request: Request) -> User:
    user = signed_in_user(request)
    if user is None:
        raise NotAuthenticated
    return user


def temporal_unavailable() -> ProblemError:
    return ProblemError(
        503,
        "TEMPORAL_UNAVAILABLE",
        "Processing delayed",
        "The upload was stored. Processing will start automatically in a few minutes.",
    )


UploadResponse = inline_serializer(
    "UploadResponse",
    {
        "created": DocumentSummarySerializer(many=True),
        "duplicates": inline_serializer(
            "DuplicateUpload",
            {"filename": serializers.CharField(), "existing_document_id": serializers.UUIDField()},
            many=True,
        ),
    },
)


class DocumentCollectionView(APIView):
    """`GET /documents` lists; `POST /documents` uploads."""

    def get_permissions(self) -> Sequence[BasePermission]:
        if self.request.method == "POST":
            return [AdminOrAccountant()]
        return [AnyMember()]

    def get_throttles(self) -> list[BaseThrottle]:
        if self.request.method == "POST":
            return [GeneralThrottle(), UploadThrottle()]
        return [GeneralThrottle()]

    def get_parsers(self) -> list[BaseParser]:
        return [MultiPartParser()]

    @extend_schema(
        parameters=[DocumentListQuerySerializer],
        responses={200: DocumentPageSerializer},
        tags=TAGS,
        operation_id="api_v1_documents_list",
    )
    def get(self, request: Request) -> Response:
        user = current_user(request)
        query = DocumentListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        documents = with_summary_data(
            filter_documents(scoped(Document.objects.all(), request), query.validated_data)
        )
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(documents, request, view=self) or []
        return paginator.get_paginated_response(
            [document_summary(document, user) for document in page]
        )

    @extend_schema(
        request=inline_serializer(
            "UploadRequest", {"files": serializers.ListField(child=serializers.FileField())}
        ),
        responses={
            201: UploadResponse,
            503: OpenApiResponse(description="TEMPORAL_UNAVAILABLE: stored, starts later"),
        },
        tags=TAGS,
    )
    def post(self, request: Request) -> Response:
        user = current_user(request)
        files = request.FILES.getlist("files")
        # invoices.middleware installed the size-limited reader before the body was parsed.
        if any(
            isinstance(handler, SizeLimitedUploadHandler) and handler.too_large
            for handler in request._request.upload_handlers
        ):
            raise file_too_large()
        if not files:
            raise ValidationError({"files": ["Send at least one file."]})
        if len(files) > MAX_FILES_PER_REQUEST:
            raise too_many_files()
        result = store_uploads(user, [(file.name or "upload", file.read()) for file in files])
        unavailable = False
        for document in result.created:
            try:
                temporal_client.start_processing(document.id)
            except temporal_client.TemporalUnavailableError:
                # The maintenance workflow starts documents still `received` later.
                logger.warning("Temporal unavailable; document %s waits", document.id)
                unavailable = True
        if unavailable:
            raise temporal_unavailable()
        documents = with_summary_data(
            scoped(Document.objects.filter(id__in=[doc.id for doc in result.created]), request)
        ).order_by("received_at", "id")
        return Response(
            {
                "created": [document_summary(document, user) for document in documents],
                "duplicates": [duplicate.__dict__ for duplicate in result.duplicates],
            },
            status=201,
        )

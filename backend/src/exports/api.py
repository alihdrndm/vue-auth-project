"""Export endpoints (HTTP API: `/exports`)."""

from collections.abc import Sequence
from uuid import UUID

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import AdminOrAccountant, AnyMember
from accounts.scoping import scoped
from eingang import storage
from exports.builders import CONTENT_TYPE
from exports.models import ExportBatch
from exports.serializers import (
    ExportCreatedSerializer,
    ExportCreateSerializer,
    ExportPageSerializer,
    ExportSerializer,
    export_created,
    export_row,
)
from exports.services import create_export
from invoices.api import current_user, download

TAGS = ["exports"]


class ExportCollectionView(APIView):
    """`GET /exports` lists (newest first); `POST /exports` creates one."""

    def get_permissions(self) -> Sequence[BasePermission]:
        if self.request.method == "POST":
            return [AdminOrAccountant()]
        return [AnyMember()]

    @extend_schema(
        operation_id="api_v1_exports_list",
        parameters=[OpenApiParameter("page", int)],
        responses={200: ExportPageSerializer},
        tags=TAGS,
    )
    def get(self, request: Request) -> Response:
        batches = (
            scoped(ExportBatch.objects.all(), request)
            .select_related("created_by")
            .order_by("-created_at", "-id")
        )
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(batches, request, view=self) or []
        return paginator.get_paginated_response(
            ExportSerializer([export_row(batch) for batch in page], many=True).data
        )

    @extend_schema(
        request=ExportCreateSerializer,
        responses={
            201: ExportCreatedSerializer,
            409: OpenApiResponse(description="NOTHING_TO_EXPORT"),
        },
        tags=TAGS,
    )
    def post(self, request: Request) -> Response:
        user = current_user(request)
        payload = ExportCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        batch = create_export(
            user, payload.validated_data["format"], payload.validated_data.get("document_ids")
        )
        return Response(ExportCreatedSerializer(export_created(batch)).data, status=201)


class ExportDownloadView(APIView):
    @extend_schema(
        responses={
            (200, "text/csv"): OpenApiTypes.BINARY,
            (200, "application/zip"): OpenApiTypes.BINARY,
        },
        tags=TAGS,
    )
    def get(self, request: Request, export_id: UUID) -> HttpResponse:
        batch = get_object_or_404(scoped(ExportBatch.objects.all(), request), id=export_id)
        name = batch.storage_key.rsplit("/", 1)[-1]
        return download(storage.read(batch.storage_key), CONTENT_TYPE[batch.format], name)

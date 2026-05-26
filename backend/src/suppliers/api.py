"""Supplier endpoints: list and detail with IBAN history (HANDOFF "HTTP API", section 10)."""

from uuid import UUID

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import AnyMember
from accounts.scoping import scoped
from invoices.models import Invoice
from suppliers.models import Supplier, SupplierIban
from suppliers.serializers import (
    SupplierDetailSerializer,
    SupplierPageSerializer,
    SupplierSerializer,
)
from suppliers.trust import first_invoice_id, iban_status, is_trusted

TAGS = ["suppliers"]


class SupplierListView(APIView):
    permission_classes = (AnyMember,)

    @extend_schema(
        operation_id="api_v1_suppliers_list",
        parameters=[
            OpenApiParameter("q", str, description="Part of the supplier name."),
            OpenApiParameter("page", int),
        ],
        responses={200: SupplierPageSerializer},
        tags=TAGS,
    )
    def get(self, request: Request) -> Response:
        suppliers = scoped(Supplier.objects.all(), request)
        query = request.query_params.get("q", "").strip()
        if query:
            suppliers = suppliers.filter(name__icontains=query)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(suppliers.order_by("name", "id"), request, view=self)
        return paginator.get_paginated_response(SupplierSerializer(page, many=True).data)


class SupplierDetailView(APIView):
    permission_classes = (AnyMember,)

    @extend_schema(responses={200: SupplierDetailSerializer}, tags=TAGS)
    def get(self, request: Request, supplier_id: UUID) -> Response:
        supplier = get_object_or_404(scoped(Supplier.objects.all(), request), id=supplier_id)
        first_invoice = first_invoice_id(supplier)
        entries = SupplierIban.objects.filter(supplier=supplier).select_related("confirmed_by")
        ibans = [
            {
                "iban": entry.iban,
                "first_seen_invoice_id": entry.first_seen_invoice_id,
                "first_seen_at": entry.first_seen_at,
                "last_seen_at": entry.last_seen_at,
                "trusted": is_trusted(entry, first_invoice),
                "status": iban_status(entry, first_invoice),
                "confirmed_by_name": entry.confirmed_by.name if entry.confirmed_by else None,
                "confirmed_at": entry.confirmed_at,
                "confirmation_note": entry.confirmation_note,
            }
            for entry in entries.order_by("first_seen_at", "id")
        ]
        invoices = (
            scoped(Invoice.objects.all(), request)
            .filter(supplier=supplier, document__deleted_at__isnull=True)
            .select_related("document")
            .order_by("-document__received_at", "-document__id")
        )
        payload = {
            "id": supplier.id,
            "name": supplier.name,
            "vat_id": supplier.vat_id,
            "invoice_count": supplier.invoice_count,
            "first_seen_at": supplier.first_seen_at,
            "last_seen_at": supplier.last_seen_at,
            "ibans": ibans,
            "invoices": list(invoices),
        }
        return Response(SupplierDetailSerializer(payload).data)

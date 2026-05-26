"""Filtering and ordering the document list (HTTP API: `GET /documents`)."""

from typing import Any

from django.db.models import F, Q, QuerySet
from rest_framework import serializers

from eingang.serializers import Serializer
from invoices.models import Document

ORDERINGS = {
    "-received_at": (F("received_at").desc(), F("id").desc()),
    "received_at": (F("received_at").asc(), F("id").asc()),
    "-gross_total": (F("invoice__gross_total").desc(nulls_last=True), F("id").desc()),
    "due_date": (F("invoice__due_date").asc(nulls_last=True), F("id").asc()),
}


class DocumentListQuerySerializer(Serializer):
    status = serializers.ChoiceField(choices=Document.Status.choices, required=False)
    q = serializers.CharField(required=False, max_length=200, trim_whitespace=True)
    supplier = serializers.UUIDField(required=False)
    kind = serializers.ChoiceField(choices=Document.Kind.choices, required=False)
    format = serializers.CharField(required=False, max_length=100)
    # A ChoiceField, not BooleanField: DRF reads a missing query boolean as False.
    einvoice = serializers.ChoiceField(choices=["true", "false"], required=False)
    ordering = serializers.ChoiceField(choices=list(ORDERINGS), required=False)
    page = serializers.IntegerField(required=False, min_value=1)


def filter_documents(
    documents: QuerySet[Document],
    params: dict[str, Any],  # boundary: validated query params
) -> QuerySet[Document]:
    """Apply the validated list parameters; deleted documents are never listed."""
    documents = documents.filter(deleted_at__isnull=True)
    if "status" in params:
        documents = documents.filter(status=params["status"])
    if params.get("q"):
        text = params["q"]
        documents = documents.filter(
            Q(invoice__invoice_number__icontains=text)
            | Q(invoice__supplier__name__icontains=text)
            | Q(invoice__seller_name__icontains=text)
            | Q(original_filename__icontains=text)
        )
    if "supplier" in params:
        documents = documents.filter(invoice__supplier_id=params["supplier"])
    if "kind" in params:
        documents = documents.filter(kind=params["kind"])
    if "format" in params:
        documents = documents.filter(format_label=params["format"])
    if "einvoice" in params:
        documents = documents.filter(invoice__is_einvoice=params["einvoice"] == "true")
    return documents.order_by(*ORDERINGS[params.get("ordering", "-received_at")])

"""Request and response shapes of the export endpoints (HANDOFF "HTTP API")."""

from rest_framework import serializers

from eingang.serializers import Serializer
from exports.models import ExportBatch


def download_url(batch: ExportBatch) -> str:
    return f"/api/v1/exports/{batch.id}/download"


class ExportCreateSerializer(Serializer):
    format = serializers.ChoiceField(choices=ExportBatch.Format.choices)
    document_ids = serializers.ListField(child=serializers.UUIDField(), required=False)


class ExportCreatedSerializer(Serializer):
    id = serializers.UUIDField()
    format = serializers.ChoiceField(choices=ExportBatch.Format.choices)
    row_count = serializers.IntegerField()
    download_url = serializers.CharField()


class ExportSerializer(ExportCreatedSerializer):
    """One row of `GET /exports`."""

    created_at = serializers.DateTimeField()
    created_by_name = serializers.CharField()


class ExportPageSerializer(Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = ExportSerializer(many=True)


def export_created(batch: ExportBatch) -> dict[str, object]:
    return {
        "id": batch.id,
        "format": batch.format,
        "row_count": batch.row_count,
        "download_url": download_url(batch),
    }


def export_row(batch: ExportBatch) -> dict[str, object]:
    return {
        **export_created(batch),
        "created_at": batch.created_at,
        "created_by_name": batch.created_by.name,
    }

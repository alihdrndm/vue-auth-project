"""Serializer helpers shared by every app."""

from typing import Any

from rest_framework import serializers


class OmitUnsetMixin:
    """Leave out fields whose value is None: an absent optional field is omitted, not null.

    Use it only on serializers whose fields are never nullable by design (HANDOFF "JSON").
    """

    def to_representation(self, instance: Any) -> dict[str, Any]:  # boundary: rest_framework
        data: dict[str, Any] = super().to_representation(instance)  # type: ignore[misc]  # mixin
        return {key: value for key, value in data.items() if value is not None}


class Serializer(OmitUnsetMixin, serializers.Serializer[Any]):  # boundary: rest_framework
    pass

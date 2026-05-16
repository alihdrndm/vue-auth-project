"""Request and response shapes of the auth endpoints."""

from typing import Any

from rest_framework import serializers

from accounts.models import Organization, User
from eingang.serializers import Serializer


class LoginRequestSerializer(Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)


class SessionUserSerializer(Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    name = serializers.CharField()


class SessionOrganizationSerializer(Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    kind = serializers.ChoiceField(choices=Organization.Kind.choices)
    expires_at = serializers.DateTimeField(required=False)
    vat_id = serializers.CharField(required=False)
    four_eyes = serializers.BooleanField()


class SessionSerializer(Serializer):
    """`{user, organization, role}`: the body of login, me and sandbox."""

    user = SessionUserSerializer()
    organization = SessionOrganizationSerializer()
    role = serializers.ChoiceField(choices=User.Role.choices)


def session_payload(user: User) -> dict[str, Any]:  # boundary: rest_framework data
    data: dict[str, Any] = SessionSerializer(
        {"user": user, "organization": user.organization, "role": user.role}
    ).data
    return data

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


class OrganizationSerializer(Serializer):
    """The body of `GET` and `PATCH /organization`."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.SlugField()
    kind = serializers.ChoiceField(choices=Organization.Kind.choices)
    expires_at = serializers.DateTimeField(required=False)
    vat_id = serializers.CharField(required=False)
    four_eyes = serializers.BooleanField()
    duplicate_window_days = serializers.IntegerField()
    reminder_after_days = serializers.IntegerField()


class OrganizationUpdateSerializer(Serializer):
    """Any subset of the editable settings; `vat_id: null` clears the VAT ID."""

    name = serializers.CharField(min_length=1, max_length=200, required=False)
    vat_id = serializers.CharField(max_length=32, allow_null=True, required=False)
    four_eyes = serializers.BooleanField(required=False)
    duplicate_window_days = serializers.IntegerField(min_value=1, max_value=365, required=False)
    reminder_after_days = serializers.IntegerField(min_value=1, max_value=60, required=False)


class MemberSerializer(Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    name = serializers.CharField()
    role = serializers.ChoiceField(choices=User.Role.choices)
    is_active = serializers.BooleanField()


class MemberPageSerializer(Serializer):
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = MemberSerializer(many=True)


class MemberCreatedSerializer(MemberSerializer):
    """The create response: the only place the one-time password is ever returned."""

    one_time_password = serializers.CharField()


class MemberCreateSerializer(Serializer):
    email = serializers.EmailField(max_length=254)
    name = serializers.CharField(min_length=1, max_length=200)
    role = serializers.ChoiceField(choices=User.Role.choices)

    def validate_email(self, value: str) -> str:
        email = value.lower()
        # Email addresses are unique across all organisations (they are the sign-in name).
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return email


class MemberUpdateSerializer(Serializer):
    email = serializers.EmailField(max_length=254, required=False)
    name = serializers.CharField(min_length=1, max_length=200, required=False)
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)
    is_active = serializers.BooleanField(required=False)

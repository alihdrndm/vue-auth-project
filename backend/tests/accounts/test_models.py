import uuid

import pytest

from accounts.models import Organization, User


@pytest.mark.django_db
def test_user_signs_in_with_email_and_belongs_to_one_organization() -> None:
    organization = Organization.objects.create(name="Holzwerk Brandt GmbH", slug="holzwerk")
    user = User.objects.create_user(
        "Anna@Example.INVALID", "secret-pass", organization=organization, role="accountant"
    )
    assert user.email == "anna@example.invalid"
    assert user.check_password("secret-pass")
    assert uuid.UUID(str(user.id)).version == 7
    assert user.organization == organization
    assert organization.four_eyes is True
    assert organization.duplicate_window_days == 30
    assert organization.reminder_after_days == 3
    assert not organization.is_sandbox


@pytest.mark.django_db
def test_user_without_password_can_never_sign_in() -> None:
    organization = Organization.objects.create(name="Sandbox", slug="sb", kind="sandbox")
    user = User.objects.create_user(
        "sandbox@example.invalid", None, organization=organization, role="admin"
    )
    assert not user.has_usable_password()
    assert organization.is_sandbox

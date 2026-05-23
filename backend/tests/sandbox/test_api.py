from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from accounts.models import Organization, User
from eingang import clock
from tests.conftest import ApiClient

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse as Response

pytestmark = pytest.mark.django_db


def open_sandbox(api: ApiClient, ip: str = "198.51.100.7") -> "Response":
    return api.unsafe("post", "/api/v1/sandbox", REMOTE_ADDR=ip)


def test_sandbox_creates_the_organisation_and_signs_the_visitor_in(
    api: ApiClient, fixed_clock: clock.FixedClock
) -> None:
    response = open_sandbox(api)
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "admin"
    assert body["organization"]["kind"] == "sandbox"
    assert body["organization"]["name"] == "Holzwerk Brandt GmbH"
    assert body["organization"]["four_eyes"] is False
    organization = Organization.objects.get(id=body["organization"]["id"])
    assert organization.expires_at == fixed_clock.now() + timedelta(hours=24)
    assert organization.vat_id == body["organization"]["vat_id"]
    assert api.get("/api/v1/auth/me").json()["user"]["id"] == body["user"]["id"]


def test_sandbox_has_two_inactive_sample_people(api: ApiClient) -> None:
    organization_id = open_sandbox(api).json()["organization"]["id"]
    people = User.objects.filter(organization_id=organization_id)
    sample = {user.name: (user.role, user.is_active) for user in people if "(sample)" in user.name}
    assert sample == {
        "Anna Weber (sample)": ("accountant", False),
        "Jonas Brandt (sample)": ("approver", False),
    }
    visitor = people.get(role="admin")
    assert not visitor.has_usable_password()
    assert visitor.email.endswith("@example.invalid")


def test_sandbox_session_expires_with_the_sandbox(
    api: ApiClient, fixed_clock: clock.FixedClock
) -> None:
    open_sandbox(api)
    assert api.session.get_expiry_age() == 24 * 60 * 60


def test_SANDBOX_LIMIT_five_per_hour_per_ip(api: ApiClient) -> None:
    for _ in range(5):
        assert open_sandbox(api).status_code == 201
    response = open_sandbox(api)
    assert response.status_code == 429
    assert response.json()["code"] == "SANDBOX_LIMIT"
    assert int(response["Retry-After"]) > 0
    # Another address may still open one.
    assert open_sandbox(api, ip="198.51.100.8").status_code == 201


def test_SANDBOX_LIMIT_fifty_per_day_in_total(
    api: ApiClient, fixed_clock: clock.FixedClock
) -> None:
    for number in range(50):
        Organization.objects.create(name="old", slug=f"old-{number}", kind="sandbox")
    response = open_sandbox(api, ip="198.51.100.9")
    assert response.status_code == 429
    assert response.json()["code"] == "SANDBOX_LIMIT"

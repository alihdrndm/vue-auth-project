from collections.abc import Callable
from datetime import timedelta

import pytest

from accounts.models import Organization, User
from eingang import clock
from tests.conftest import ApiClient, MakeUser

pytestmark = pytest.mark.django_db


@pytest.fixture
def sandbox_admin(api: ApiClient, make_user: MakeUser, fixed_clock: clock.FixedClock) -> ApiClient:
    sandbox = Organization.objects.create(
        name="Sandbox",
        slug="sandbox-1",
        kind="sandbox",
        expires_at=fixed_clock.now() + timedelta(hours=1),
    )
    api.sign_in(make_user("admin", org=sandbox))
    return api


# Organisation


def test_NOT_AUTHENTICATED_organization(api: ApiClient) -> None:
    response = api.get("/api/v1/organization")
    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"


def test_every_role_reads_the_organization(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    response = signed_in("viewer").get("/api/v1/organization")
    assert response.status_code == 200
    assert response.json() == {
        "id": str(organization.id),
        "name": "Holzwerk Brandt GmbH",
        "slug": "holzwerk-brandt",
        "kind": "standard",
        "vat_id": "DE291746055",
        "four_eyes": True,
        "duplicate_window_days": 30,
        "reminder_after_days": 3,
    }


def test_admin_patches_the_organization(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    response = signed_in("admin").unsafe(
        "patch",
        "/api/v1/organization",
        data={
            "name": "Holzwerk Brandt KG",
            "vat_id": None,
            "four_eyes": False,
            "duplicate_window_days": 365,
            "reminder_after_days": 60,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Holzwerk Brandt KG"
    assert "vat_id" not in body
    assert body["four_eyes"] is False
    organization.refresh_from_db()
    assert organization.vat_id is None
    assert organization.duplicate_window_days == 365
    assert organization.reminder_after_days == 60


def test_patch_changes_only_the_fields_sent(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    response = signed_in("admin").unsafe(
        "patch", "/api/v1/organization", data={"reminder_after_days": 5}
    )
    assert response.status_code == 200
    organization.refresh_from_db()
    assert organization.reminder_after_days == 5
    assert organization.vat_id == "DE291746055"
    assert organization.four_eyes is True


def test_FORBIDDEN_ROLE_viewer_patching_the_organization(
    signed_in: Callable[[str], ApiClient],
) -> None:
    response = signed_in("viewer").unsafe("patch", "/api/v1/organization", data={"name": "X"})
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN_ROLE"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("duplicate_window_days", 0),
        ("duplicate_window_days", 366),
        ("reminder_after_days", 0),
        ("reminder_after_days", 61),
        ("name", ""),
        ("name", "x" * 201),
    ],
)
def test_VALIDATION_FAILED_organization_out_of_range(
    signed_in: Callable[[str], ApiClient], field: str, value: object
) -> None:
    response = signed_in("admin").unsafe("patch", "/api/v1/organization", data={field: value})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert [error["path"] for error in body["errors"]] == [field]


def test_SANDBOX_RESTRICTED_sandbox_admin_patching_four_eyes(sandbox_admin: ApiClient) -> None:
    response = sandbox_admin.unsafe(
        "patch", "/api/v1/organization", data={"name": "Mein Test", "four_eyes": False}
    )
    assert response.status_code == 403
    assert response.json()["code"] == "SANDBOX_RESTRICTED"
    assert Organization.objects.get(slug="sandbox-1").name == "Sandbox"


def test_sandbox_admin_may_patch_the_name(sandbox_admin: ApiClient) -> None:
    response = sandbox_admin.unsafe("patch", "/api/v1/organization", data={"name": "Mein Test"})
    assert response.status_code == 200
    assert response.json()["name"] == "Mein Test"


# Members


def test_NOT_AUTHENTICATED_members(api: ApiClient) -> None:
    response = api.get("/api/v1/members")
    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"


def test_FORBIDDEN_ROLE_accountant_listing_members(
    signed_in: Callable[[str], ApiClient],
) -> None:
    response = signed_in("accountant").get("/api/v1/members")
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN_ROLE"


def test_SANDBOX_RESTRICTED_sandbox_admin_listing_members(sandbox_admin: ApiClient) -> None:
    response = sandbox_admin.get("/api/v1/members")
    assert response.status_code == 403
    assert response.json()["code"] == "SANDBOX_RESTRICTED"


def test_admin_lists_the_members_of_the_own_organization(
    signed_in: Callable[[str], ApiClient],
    make_user: MakeUser,
    other_organization: Organization,
) -> None:
    api = signed_in("admin")
    viewer = make_user("viewer")
    make_user("admin", org=other_organization)
    response = api.get("/api/v1/members")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["results"][1] == {
        "id": str(viewer.id),
        "email": viewer.email,
        "name": "Viewer",
        "role": "viewer",
        "is_active": True,
    }


def test_create_returns_a_one_time_password_once_that_signs_in(
    signed_in: Callable[[str], ApiClient], organization: Organization
) -> None:
    api = signed_in("admin")
    response = api.unsafe(
        "post",
        "/api/v1/members",
        data={"email": "Neu.Person@Example.invalid", "name": "Neue Person", "role": "approver"},
    )
    assert response.status_code == 201
    body = response.json()
    password = body.pop("one_time_password")
    assert len(password) >= 24
    member = User.objects.get(id=body["id"])
    assert member.organization_id == organization.id
    assert body == {
        "id": str(member.id),
        "email": "neu.person@example.invalid",
        "name": "Neue Person",
        "role": "approver",
        "is_active": True,
    }
    listed = api.get("/api/v1/members").json()["results"]
    assert all("one_time_password" not in row for row in listed)
    patched = api.unsafe("patch", f"/api/v1/members/{member.id}", data={"name": "N. Person"})
    assert "one_time_password" not in patched.json()

    newcomer = ApiClient()
    login = newcomer.unsafe(
        "post",
        "/api/v1/auth/login",
        data={"email": "neu.person@example.invalid", "password": password},
    )
    assert login.status_code == 200
    assert login.json()["role"] == "approver"


def test_VALIDATION_FAILED_duplicate_email_in_another_organization(
    signed_in: Callable[[str], ApiClient],
    make_user: MakeUser,
    other_organization: Organization,
) -> None:
    api = signed_in("admin")
    existing = make_user("viewer", org=other_organization)
    response = api.unsafe(
        "post",
        "/api/v1/members",
        data={"email": existing.email.upper(), "name": "Doppelt", "role": "viewer"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert [error["path"] for error in body["errors"]] == ["email"]


def test_VALIDATION_FAILED_create_without_fields(signed_in: Callable[[str], ApiClient]) -> None:
    response = signed_in("admin").unsafe("post", "/api/v1/members", data={"role": "owner"})
    assert response.status_code == 422
    paths = {error["path"] for error in response.json()["errors"]}
    assert paths == {"email", "name", "role"}


def test_admin_changes_another_member(
    signed_in: Callable[[str], ApiClient], make_user: MakeUser
) -> None:
    api = signed_in("admin")
    member = make_user("viewer")
    response = api.unsafe(
        "patch",
        f"/api/v1/members/{member.id}",
        data={"role": "accountant", "is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "accountant"
    assert response.json()["is_active"] is False
    member.refresh_from_db()
    assert member.role == "accountant"
    assert member.is_active is False


def test_VALIDATION_FAILED_admin_deactivating_themselves(
    api: ApiClient, make_user: MakeUser
) -> None:
    admin = make_user("admin")
    api.sign_in(admin)
    response = api.unsafe("patch", f"/api/v1/members/{admin.id}", data={"is_active": False})
    assert response.status_code == 422
    assert [error["path"] for error in response.json()["errors"]] == ["is_active"]
    admin.refresh_from_db()
    assert admin.is_active is True


def test_VALIDATION_FAILED_admin_changing_their_own_role(
    api: ApiClient, make_user: MakeUser
) -> None:
    admin = make_user("admin")
    api.sign_in(admin)
    response = api.unsafe("patch", f"/api/v1/members/{admin.id}", data={"role": "viewer"})
    assert response.status_code == 422
    assert [error["path"] for error in response.json()["errors"]] == ["role"]


def test_admin_may_rename_themselves(api: ApiClient, make_user: MakeUser) -> None:
    admin = make_user("admin")
    api.sign_in(admin)
    response = api.unsafe(
        "patch", f"/api/v1/members/{admin.id}", data={"name": "Chefin", "role": "admin"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Chefin"


def test_NOT_FOUND_member_of_another_organization(
    signed_in: Callable[[str], ApiClient],
    make_user: MakeUser,
    other_organization: Organization,
) -> None:
    api = signed_in("admin")
    stranger = make_user("viewer", org=other_organization)
    response = api.unsafe("patch", f"/api/v1/members/{stranger.id}", data={"name": "X"})
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    stranger.refresh_from_db()
    assert stranger.name == "Viewer"


def test_member_email_can_be_changed_but_must_stay_unique(
    signed_in: Callable[[str], ApiClient], make_user: MakeUser
) -> None:
    api = signed_in("admin")
    member = make_user("viewer")
    other = make_user("accountant")
    url = f"/api/v1/members/{member.id}"
    response = api.unsafe("patch", url, data={"email": "New.Name@Example.INVALID"})
    assert response.status_code == 200
    assert response.json()["email"] == "new.name@example.invalid"
    clash = api.unsafe("patch", url, data={"email": other.email})
    assert clash.status_code == 422
    assert clash.json()["errors"][0]["path"] == "email"

"""`/exports`: create, list and download (HANDOFF "HTTP API", section 11)."""

import zipfile
from collections.abc import Callable, Iterator
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest
from django.core.files.storage import storages
from django.test import override_settings
from pytest_django import DjangoCaptureOnCommitCallbacks

from accounts.models import Organization
from eingang import clock, storage, temporal_client
from exports.models import ExportBatch
from invoices.models import Document, Event
from tests.conftest import ApiClient, MakeUser
from tests.factories import add_approval, make_document, make_export, make_invoice

pytestmark = pytest.mark.django_db
Signals = list[tuple[UUID, str, str]]


@pytest.fixture(autouse=True)
def _temporary_storage(tmp_path: Path) -> Iterator[None]:
    documents = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": str(tmp_path), "allow_overwrite": True},
    }
    with override_settings(STORAGES={**storages.backends, "documents": documents}):
        yield


@pytest.fixture
def signals(monkeypatch: pytest.MonkeyPatch) -> Signals:
    sent: Signals = []
    monkeypatch.setattr(
        temporal_client,
        "signal",
        lambda document_id, workflow_id, name: sent.append((document_id, workflow_id, name)),
    )
    return sent


def approved(organization: Organization, make_user: MakeUser) -> Document:
    document = make_document(organization, status=Document.Status.APPROVED)
    Document.objects.filter(id=document.id).update(workflow_id=f"invoice-{document.id}")
    make_invoice(document)
    add_approval(document, make_user("approver", email=f"ap-{document.id}@example.invalid"))
    storage.write(document.storage_key, b"<Invoice/>")
    return document


def test_export_marks_approved_documents_exported_with_events(
    signed_in: Callable[[str], ApiClient],
    organization: Organization,
    make_user: MakeUser,
    signals: Signals,
    fixed_clock: clock.FixedClock,
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> None:
    api = signed_in("accountant")
    first, second = approved(organization, make_user), approved(organization, make_user)
    waiting = make_document(organization, status=Document.Status.AWAITING_APPROVAL)
    with django_capture_on_commit_callbacks(execute=True):
        response = api.unsafe("post", "/api/v1/exports", data={"format": "csv_invoices"})
    assert response.status_code == 201
    body = response.json()
    assert body["format"] == "csv_invoices"
    assert body["row_count"] == 2
    assert body["download_url"] == f"/api/v1/exports/{body['id']}/download"
    batch = ExportBatch.objects.get(id=body["id"])
    assert batch.document_ids == [str(first.id), str(second.id)]
    assert batch.storage_key == (
        f"orgs/{organization.id}/exports/{batch.id}/eingang-invoices-20260310-0930.csv"
    )
    for document in (first, second):
        document.refresh_from_db()
        assert document.status == Document.Status.EXPORTED
        event = Event.objects.get(document=document, type="export.created")
        assert event.actor is None  # the system exports
        assert event.data == {"from": "approved", "to": "exported", "export_id": str(batch.id)}
    waiting.refresh_from_db()
    assert waiting.status == Document.Status.AWAITING_APPROVAL
    assert signals == [
        (first.id, f"invoice-{first.id}", "exported"),
        (second.id, f"invoice-{second.id}", "exported"),
    ]


def test_explicit_ids_export_only_the_approved_ones(
    signed_in: Callable[[str], ApiClient],
    organization: Organization,
    other_organization: Organization,
    make_user: MakeUser,
    signals: Signals,
) -> None:
    api = signed_in("admin")
    chosen = approved(organization, make_user)
    not_chosen = approved(organization, make_user)
    waiting = make_document(organization, status=Document.Status.AWAITING_APPROVAL)
    foreign = make_document(other_organization, status=Document.Status.APPROVED)
    ids = [str(chosen.id), str(waiting.id), str(foreign.id)]
    response = api.unsafe(
        "post", "/api/v1/exports", data={"format": "csv_lines", "document_ids": ids}
    )
    assert response.status_code == 201
    assert response.json()["row_count"] == 1
    assert ExportBatch.objects.get().document_ids == [str(chosen.id)]
    for document, status in ((not_chosen, "approved"), (waiting, "awaiting_approval"),
                             (foreign, "approved")):  # fmt: skip
        document.refresh_from_db()
        assert document.status == status


def test_deleted_documents_are_not_exported(
    signed_in: Callable[[str], ApiClient], organization: Organization, make_user: MakeUser
) -> None:
    api = signed_in("admin")
    document = approved(organization, make_user)
    Document.objects.filter(id=document.id).update(deleted_at=clock.now())
    response = api.unsafe("post", "/api/v1/exports", data={"format": "csv_invoices"})
    assert response.status_code == 409
    assert response.json()["code"] == "NOTHING_TO_EXPORT"


def test_NOTHING_TO_EXPORT_when_nothing_is_approved(
    signed_in: Callable[[str], ApiClient], organization: Organization, signals: Signals
) -> None:
    api = signed_in("accountant")
    waiting = make_document(organization, status=Document.Status.AWAITING_APPROVAL)
    for body in (
        {"format": "zip_bundle"},
        {"format": "zip_bundle", "document_ids": [str(waiting.id)]},
    ):
        response = api.unsafe("post", "/api/v1/exports", data=body)
        assert response.status_code == 409
        assert response.json()["code"] == "NOTHING_TO_EXPORT"
    assert not ExportBatch.objects.exists()
    assert signals == []


def test_NOTHING_TO_EXPORT_after_everything_was_exported(
    signed_in: Callable[[str], ApiClient], organization: Organization, make_user: MakeUser
) -> None:
    api = signed_in("admin")
    approved(organization, make_user)
    assert api.unsafe("post", "/api/v1/exports", data={"format": "csv_invoices"}).status_code == 201
    again = api.unsafe("post", "/api/v1/exports", data={"format": "csv_invoices"})
    assert again.json()["code"] == "NOTHING_TO_EXPORT"


@pytest.mark.parametrize("role", ["approver", "viewer"])
def test_FORBIDDEN_ROLE_create_export(
    role: str, signed_in: Callable[[str], ApiClient], organization: Organization,
    make_user: MakeUser,
) -> None:  # fmt: skip
    api = signed_in(role)
    document = approved(organization, make_user)
    response = api.unsafe("post", "/api/v1/exports", data={"format": "csv_invoices"})
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN_ROLE"
    document.refresh_from_db()
    assert document.status == Document.Status.APPROVED


def test_VALIDATION_FAILED_unknown_format(signed_in: Callable[[str], ApiClient]) -> None:
    response = signed_in("admin").unsafe("post", "/api/v1/exports", data={"format": "xlsx"})
    assert response.status_code == 422
    assert response.json()["errors"][0]["path"] == "format"


@pytest.mark.parametrize(
    ("export_format", "content_type"),
    [("csv_invoices", "text/csv; charset=utf-8"), ("zip_bundle", "application/zip")],
)
def test_download_is_an_attachment_and_unchanged_on_repeat(
    export_format: str,
    content_type: str,
    signed_in: Callable[[str], ApiClient],
    organization: Organization,
    make_user: MakeUser,
    fixed_clock: clock.FixedClock,
) -> None:
    api = signed_in("accountant")
    document = approved(organization, make_user)
    created = api.unsafe("post", "/api/v1/exports", data={"format": export_format}).json()
    events = Event.objects.count()
    first = api.get(created["download_url"])
    assert first.status_code == 200
    assert first["Content-Type"] == content_type
    assert first["Content-Security-Policy"] == "sandbox; default-src 'none'"
    extension = "csv" if export_format == "csv_invoices" else "zip"
    assert first["Content-Disposition"].startswith("attachment")
    assert f"-20260310-0930.{extension}" in first["Content-Disposition"]
    if export_format == "zip_bundle":
        assert f"reports/{document.id}.json" in zipfile.ZipFile(BytesIO(first.content)).namelist()
    second = api.get(created["download_url"])
    assert second.content == first.content
    assert Event.objects.count() == events
    assert ExportBatch.objects.count() == 1
    document.refresh_from_db()
    assert document.status == Document.Status.EXPORTED


def test_viewer_can_list_and_download(
    signed_in: Callable[[str], ApiClient], organization: Organization, make_user: MakeUser
) -> None:
    batch = make_export(organization, make_user("accountant"))
    storage.write(batch.storage_key, b"\xef\xbb\xbfBelegdatum\r\n")
    api = signed_in("viewer")
    assert api.get(f"/api/v1/exports/{batch.id}/download").content == b"\xef\xbb\xbfBelegdatum\r\n"
    (row,) = api.get("/api/v1/exports").json()["results"]
    assert row == {
        "id": str(batch.id),
        "format": "csv_invoices",
        "row_count": 0,
        "created_at": row["created_at"],
        "created_by_name": "Accountant",
        "download_url": f"/api/v1/exports/{batch.id}/download",
    }


def test_list_is_paginated_newest_first_and_scoped(
    signed_in: Callable[[str], ApiClient],
    organization: Organization,
    other_organization: Organization,
    make_user: MakeUser,
) -> None:
    creator = make_user("accountant")
    batches = [make_export(organization, creator) for _ in range(27)]
    make_export(other_organization, make_user("admin", org=other_organization))
    api = signed_in("viewer")
    page = api.get("/api/v1/exports").json()
    assert page["count"] == 27
    assert len(page["results"]) == 25
    assert page["results"][0]["id"] == str(batches[-1].id)
    assert page["previous"] is None
    second = api.get("/api/v1/exports", {"page": 2}).json()
    assert [row["id"] for row in second["results"]] == [str(b.id) for b in batches[1::-1]]
    assert second["next"] is None


def test_NOT_FOUND_download_of_another_organizations_export(
    signed_in: Callable[[str], ApiClient], other_organization: Organization, make_user: MakeUser
) -> None:
    batch = make_export(other_organization, make_user("admin", org=other_organization))
    storage.write(batch.storage_key, b"secret")
    response = signed_in("admin").get(f"/api/v1/exports/{batch.id}/download")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"

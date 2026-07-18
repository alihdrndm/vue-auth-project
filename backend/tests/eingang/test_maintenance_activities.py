"""The maintenance activities against a real database, with Temporal replaced by fakes."""

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest
from django.core.files.storage import storages
from django.test import override_settings

from accounts.models import Organization, User
from eingang import clock, maintenance_activities, storage, temporal_client
from eingang.maintenance_activities import (
    delete_expired_sandboxes,
    log_daily_stats,
    resignal_inconsistent_documents,
    start_unstarted_documents,
)
from eingang.workflows import contracts as c
from exports.models import ExportBatch
from invoices.models import Document, Event
from tests.factories import add_approval, make_document, make_export, make_sandbox

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _temporary_storage(tmp_path: Path) -> Iterator[None]:
    documents = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": str(tmp_path), "allow_overwrite": True},
    }
    with override_settings(STORAGES={**storages.backends, "documents": documents}):
        yield


@pytest.fixture(autouse=True)
def _keep_test_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    # The test runs inside a transaction; closing "old" connections would close it.
    monkeypatch.setattr(maintenance_activities, "close_old_connections", lambda: None)


@dataclass
class FakeTemporal:
    """Records what the activities asked Temporal to do."""

    phases: dict[str, str | None] = field(default_factory=dict)
    signals: list[tuple[UUID, str, str]] = field(default_factory=list)
    started: list[UUID] = field(default_factory=list)
    unavailable: bool = False

    def signal(self, document_id: UUID, workflow_id: str, name: str) -> None:
        self.signals.append((document_id, workflow_id, name))

    def start_processing(self, document_id: UUID) -> None:
        if self.unavailable:
            raise temporal_client.TemporalUnavailableError
        self.started.append(document_id)

    def query_phase(self, workflow_id: str) -> str | None:
        return self.phases.get(workflow_id)


@pytest.fixture
def temporal(monkeypatch: pytest.MonkeyPatch) -> FakeTemporal:
    fake = FakeTemporal()
    monkeypatch.setattr(temporal_client, "signal", fake.signal)
    monkeypatch.setattr(temporal_client, "start_processing", fake.start_processing)
    monkeypatch.setattr(temporal_client, "query_phase", fake.query_phase)
    return fake


def _with_workflow(document: Document) -> Document:
    document.workflow_id = c.process_invoice_workflow_id(document.id)
    document.save(update_fields=["workflow_id"])
    return document


def _store_files(document: Document) -> list[str]:
    keys = [
        document.storage_key,
        storage.derived_key(document.organization_id, document.id, "invoice.xml"),
        storage.derived_key(document.organization_id, document.id, "visualization.html"),
    ]
    for key in keys:
        storage.write(key, b"<Invoice/>")
    return keys


# --- delete_expired_sandboxes ------------------------------------------------------


def test_expired_sandbox_is_deleted_with_its_files_after_signalling(
    fixed_clock: clock.FixedClock, temporal: FakeTemporal, monkeypatch: pytest.MonkeyPatch
) -> None:
    sandbox = make_sandbox(clock.now() - timedelta(minutes=1))
    visitor = User.objects.create_user(
        "visitor@example.invalid", None, organization=sandbox, role=User.Role.ADMIN
    )
    running = _with_workflow(make_document(sandbox, status=Document.Status.APPROVED))
    seeded = make_document(sandbox)  # seeded documents have no workflow
    add_approval(running, visitor)
    Event.objects.create(organization=sandbox, document=running, type=Event.Type.DOCUMENT_RECEIVED)
    keys = _store_files(running) + _store_files(seeded)
    export = make_export(sandbox, visitor)
    storage.write(export.storage_key, b"csv")
    keys.append(export.storage_key)

    def signal_while_data_exists(document_id: UUID, workflow_id: str, name: str) -> None:
        # The workflow is told before anything is gone.
        assert Organization.objects.filter(id=sandbox.id).exists()
        assert all(storage.exists(key) for key in keys)
        temporal.signals.append((document_id, workflow_id, name))

    monkeypatch.setattr(temporal_client, "signal", signal_while_data_exists)

    assert delete_expired_sandboxes() == 1

    assert temporal.signals == [(running.id, running.workflow_id, c.SIG_DELETED)]
    assert not Organization.objects.filter(id=sandbox.id).exists()
    assert not Document.objects.filter(organization_id=sandbox.id).exists()
    assert not ExportBatch.objects.filter(organization_id=sandbox.id).exists()
    assert not User.objects.filter(organization_id=sandbox.id).exists()
    assert not any(storage.exists(key) for key in keys)
    assert delete_expired_sandboxes() == 0  # idempotent


def test_unexpired_sandbox_and_real_organisations_are_kept(
    fixed_clock: clock.FixedClock, temporal: FakeTemporal, organization: Organization
) -> None:
    fresh = make_sandbox(clock.now() + timedelta(hours=1))
    organization.expires_at = clock.now() - timedelta(days=1)  # ignored: not a sandbox
    organization.save(update_fields=["expires_at"])
    kept = [_with_workflow(make_document(fresh)), _with_workflow(make_document(organization))]
    keys = _store_files(kept[0]) + _store_files(kept[1])

    assert delete_expired_sandboxes() == 0

    assert Organization.objects.filter(id__in=[fresh.id, organization.id]).count() == 2
    assert Document.objects.filter(id__in=[doc.id for doc in kept]).count() == 2
    assert all(storage.exists(key) for key in keys)
    assert temporal.signals == []


# --- start_unstarted_documents -----------------------------------------------------


def _received(organization: Organization, minutes_ago: int, *, workflow: bool = True) -> Document:
    document = make_document(organization, status=Document.Status.RECEIVED)
    document.received_at = clock.now() - timedelta(minutes=minutes_ago)
    if workflow:
        document.workflow_id = c.process_invoice_workflow_id(document.id)
    document.save(update_fields=["received_at", "workflow_id"])
    return document


def test_documents_received_over_ten_minutes_ago_are_started(
    fixed_clock: clock.FixedClock, temporal: FakeTemporal, organization: Organization
) -> None:
    stuck = _received(organization, 11)
    _received(organization, 9)  # still young: the API's own start may be under way
    _received(organization, 60, workflow=False)  # seeded: never has a workflow
    deleted = _received(organization, 60)
    deleted.deleted_at = clock.now()
    deleted.save(update_fields=["deleted_at"])
    processing = _received(organization, 60)
    processing.status = Document.Status.PROCESSING
    processing.save(update_fields=["status"])

    assert start_unstarted_documents() == 1
    assert temporal.started == [stuck.id]


def test_temporal_down_makes_the_start_step_fail_so_it_is_retried(
    fixed_clock: clock.FixedClock, temporal: FakeTemporal, organization: Organization
) -> None:
    _received(organization, 30)
    temporal.unavailable = True
    with pytest.raises(temporal_client.TemporalUnavailableError):
        start_unstarted_documents()


# --- resignal_inconsistent_documents ----------------------------------------------


def test_sync_is_signalled_only_when_the_phase_differs_from_the_status(
    temporal: FakeTemporal, organization: Organization
) -> None:
    behind = _with_workflow(make_document(organization, status=Document.Status.APPROVED))
    in_step = _with_workflow(make_document(organization, status=Document.Status.NEEDS_REVIEW))
    gone = _with_workflow(make_document(organization, status=Document.Status.REJECTED))
    exported = _with_workflow(make_document(organization, status=Document.Status.EXPORTED))
    make_document(organization, status=Document.Status.NEEDS_REVIEW)  # seeded, no workflow
    temporal.phases = {
        behind.workflow_id: Document.Status.AWAITING_APPROVAL,
        in_step.workflow_id: Document.Status.NEEDS_REVIEW,
        gone.workflow_id: None,  # finished, e.g. after the 180-day wait
        exported.workflow_id: Document.Status.APPROVED,  # never asked: exported is final
    }

    summary = resignal_inconsistent_documents()

    assert temporal.signals == [(behind.id, behind.workflow_id, c.SIG_SYNC)]
    assert summary == c.ResyncSummary(resignalled_documents=1, abandoned_workflows=1)


# --- log_daily_stats ---------------------------------------------------------------


def test_daily_stats_log_counts_per_status_on_one_line(
    organization: Organization, caplog: pytest.LogCaptureFixture
) -> None:
    make_document(organization, status=Document.Status.NEEDS_REVIEW)
    make_document(organization, status=Document.Status.NEEDS_REVIEW)
    make_document(organization, status=Document.Status.APPROVED)
    removed = make_document(organization, status=Document.Status.APPROVED)
    removed.deleted_at = removed.received_at
    removed.save(update_fields=["deleted_at"])

    with caplog.at_level(logging.INFO, logger="eingang.maintenance_activities"):
        assert log_daily_stats() == 3

    [record] = [r for r in caplog.records if r.getMessage().startswith("Daily stats")]
    assert "documents=3" in record.getMessage()
    assert "needs_review=2" in record.getMessage()
    assert "approved=1" in record.getMessage()
    counts = record.__dict__["document_counts"]
    assert counts["needs_review"] == 2
    assert counts["received"] == 0
    assert organization.name not in record.getMessage()

"""Activities of MaintenanceWorkflow: the daily clean-up (HANDOFF "Temporal workflows").

Each activity is idempotent and reads the current state from the database. Workflows never
import this module; they call the activities by name. Temporal being unreachable raises
TemporalUnavailableError, so the activity is retried.
"""

import logging
from collections.abc import Callable, Iterable
from datetime import timedelta

from django.db import close_old_connections, transaction
from django.db.models import Count
from temporalio import activity

from accounts.models import Organization
from eingang import clock, storage, temporal_client
from eingang.workflows import contracts as c
from exports.models import ExportBatch
from invoices.models import Document

logger = logging.getLogger(__name__)
Status = Document.Status

# Uploads still `received` this long after upload were never started (e.g. Temporal was down).
UNSTARTED_AFTER = timedelta(minutes=10)
# Statuses whose workflow is not waiting any more (exported) or not started yet (received;
# `start_unstarted_documents` handles those).
NOT_RESYNCED = (Status.EXPORTED, Status.RECEIVED)
DERIVED_FILES: tuple[storage.DerivedFile, ...] = ("invoice.xml", "text.txt", "visualization.html")


def _document_keys(document: Document) -> Iterable[str]:
    yield document.storage_key
    if document.text_storage_key:
        yield document.text_storage_key
    for name in DERIVED_FILES:
        yield storage.derived_key(document.organization_id, document.id, name)


def delete_organization(organization: Organization) -> None:
    """Delete an organisation with its stored files, after waking its running workflows."""
    documents = list(Document.objects.filter(organization=organization))
    # Wake the running workflows first so they end; the database row is the source of truth.
    for document in documents:
        if document.workflow_id and document.deleted_at is None:
            temporal_client.signal(document.id, document.workflow_id, c.SIG_DELETED)
    for document in documents:
        for key in _document_keys(document):
            storage.delete(key)
    for key in ExportBatch.objects.filter(organization=organization).values_list(
        "storage_key", flat=True
    ):
        storage.delete(key)
    with transaction.atomic():
        organization.delete()  # cascades to users, documents, invoices, events and exports


@activity.defn(name=c.ACT_DELETE_EXPIRED_SANDBOXES)
def delete_expired_sandboxes() -> int:
    """Delete every sandbox organisation whose expiry has passed, with its files."""
    close_old_connections()
    expired = Organization.objects.filter(
        kind=Organization.Kind.SANDBOX, expires_at__lte=clock.now()
    ).order_by("expires_at")
    count = 0
    for organization in expired:
        delete_organization(organization)
        count += 1
    if count:
        logger.info("Deleted %d expired sandboxes", count)
    return count


@activity.defn(name=c.ACT_START_UNSTARTED_DOCUMENTS)
def start_unstarted_documents() -> int:
    """Start the workflow of uploads that are still `received` ten minutes after upload."""
    close_old_connections()
    unstarted = (
        Document.objects.filter(
            status=Status.RECEIVED,
            received_at__lt=clock.now() - UNSTARTED_AFTER,
            deleted_at__isnull=True,
        )
        .exclude(workflow_id="")
        .values_list("id", flat=True)
    )
    count = 0
    for document_id in unstarted:
        # An already running workflow is accepted; TemporalUnavailableError retries the activity.
        temporal_client.start_processing(document_id)
        count += 1
    if count:
        logger.info("Started %d unstarted documents", count)
    return count


@activity.defn(name=c.ACT_RESIGNAL_INCONSISTENT_DOCUMENTS)
def resignal_inconsistent_documents() -> c.ResyncSummary:
    """Signal `sync` to every running workflow whose `phase` differs from the document status."""
    close_old_connections()
    open_documents = (
        Document.objects.filter(deleted_at__isnull=True)
        .exclude(workflow_id="")
        .exclude(status__in=NOT_RESYNCED)
        .only("id", "workflow_id", "status")
    )
    resignalled = 0
    abandoned = 0
    for document in open_documents:
        phase = temporal_client.query_phase(document.workflow_id)
        if phase is None:
            abandoned += 1
        elif phase != document.status:
            temporal_client.signal(document.id, document.workflow_id, c.SIG_SYNC)
            resignalled += 1
    if resignalled or abandoned:
        logger.info("Resignalled %d workflows; %d without a workflow", resignalled, abandoned)
    return c.ResyncSummary(resignalled_documents=resignalled, abandoned_workflows=abandoned)


@activity.defn(name=c.ACT_LOG_DAILY_STATS)
def log_daily_stats() -> int:
    """Log the number of documents per status (no personal data); returns the total."""
    close_old_connections()
    rows = (
        Document.objects.filter(deleted_at__isnull=True)
        .values_list("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )
    counts = {status: 0 for status in Status.values}
    for status, number in rows:
        counts[status] = number
    total = sum(counts.values())
    summary = " ".join(f"{status}={number}" for status, number in counts.items())
    logger.info("Daily stats: documents=%d %s", total, summary, extra={"document_counts": counts})
    return total


MAINTENANCE_ACTIVITIES: list[Callable[..., object]] = [
    delete_expired_sandboxes,
    start_unstarted_documents,
    resignal_inconsistent_documents,
    log_daily_stats,
]

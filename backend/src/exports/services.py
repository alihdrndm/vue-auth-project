"""Creating an export (HANDOFF section 11): build, store, record, mark exported.

Only approved, non-deleted documents of the user's organisation are exported. The file,
the batch and every `approved → exported` transition commit together; the workflows are
signalled after the commit.
"""

from collections.abc import Sequence
from functools import partial
from uuid import UUID

from django.db import transaction

from accounts.models import User
from eingang import clock, storage, temporal_client
from eingang.problem import ProblemError
from eingang.workflows.contracts import SIG_EXPORTED
from exports import builders
from exports.models import ExportBatch
from invoices.models import Document
from invoices.status import transition


def nothing_to_export() -> ProblemError:
    return ProblemError(
        409,
        "NOTHING_TO_EXPORT",
        "Nothing to export",
        "No approved, not-yet-exported invoices match the export request.",
    )


def _signal_exported(documents: Sequence[Document]) -> None:
    for document in documents:
        temporal_client.signal(document.id, document.workflow_id, SIG_EXPORTED)


def create_export(
    user: User, export_format: str, document_ids: Sequence[UUID] | None
) -> ExportBatch:
    """Export the user's approved documents (all of them, or those of `document_ids`).

    Ids that are not approved, deleted or of another organisation are left out; when
    nothing is left the answer is 409 NOTHING_TO_EXPORT.
    """
    with transaction.atomic():
        exportable = Document.objects.filter(
            organization=user.organization,
            deleted_at__isnull=True,
            status=Document.Status.APPROVED,
        )
        if document_ids is not None:
            exportable = exportable.filter(id__in=document_ids)
        # Lock first, so two exports at once cannot both include a document.
        locked = list(exportable.select_for_update().values_list("id", flat=True))
        if not locked:
            raise nothing_to_export()
        documents = list(builders.export_queryset(Document.objects.filter(id__in=locked)))
        moment = clock.now()
        batch = ExportBatch(
            organization=user.organization,
            created_by=user,
            format=export_format,
            document_ids=[str(document.id) for document in documents],
            row_count=len(documents),
        )
        batch.storage_key = storage.export_key(
            user.organization_id, batch.id, builders.filename(export_format, moment)
        )
        storage.write(batch.storage_key, builders.build(export_format, documents, moment))
        batch.save()
        for document in documents:
            transition(
                document,
                Document.Status.EXPORTED,
                None,
                event_data={"export_id": str(batch.id)},
            )
        transaction.on_commit(partial(_signal_exported, documents))
    return batch

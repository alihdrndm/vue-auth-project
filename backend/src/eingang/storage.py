"""Where document files live: object keys and the configured storage backend.

Keys never contain original file names (HANDOFF "Files"):
`orgs/<org_id>/documents/<document_id>/<sha256>.<ext>`, with the derived files
(`invoice.xml`, `text.txt`, `visualization.html`) next to the original.
"""

from typing import Literal
from uuid import UUID

from django.core.files.base import ContentFile
from django.core.files.storage import Storage, storages

DerivedFile = Literal["invoice.xml", "text.txt", "visualization.html"]


def document_folder(organization_id: UUID, document_id: UUID) -> str:
    return f"orgs/{organization_id}/documents/{document_id}"


def original_key(organization_id: UUID, document_id: UUID, sha256: str, extension: str) -> str:
    return f"{document_folder(organization_id, document_id)}/{sha256}.{extension}"


def derived_key(organization_id: UUID, document_id: UUID, name: DerivedFile) -> str:
    return f"{document_folder(organization_id, document_id)}/{name}"


def backend() -> Storage:
    return storages["documents"]


def write(key: str, data: bytes) -> None:
    storage = backend()
    # Keys are content-addressed, so an existing key already holds these bytes.
    if storage.exists(key):
        storage.delete(key)
    stored = storage.save(key, ContentFile(data))
    if stored != key:
        raise RuntimeError("storage renamed an object key")


def read(key: str) -> bytes:
    with backend().open(key, "rb") as handle:
        data: bytes = handle.read()
    return data


def exists(key: str) -> bool:
    return backend().exists(key)


def delete(key: str) -> None:
    storage = backend()
    if storage.exists(key):
        storage.delete(key)

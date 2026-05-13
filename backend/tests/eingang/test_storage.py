import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from django.core.files.storage import storages
from django.test import override_settings

from eingang import storage

ORG = uuid.UUID("01900000-0000-7000-8000-000000000001")
DOC = uuid.UUID("01900000-0000-7000-8000-000000000002")


@pytest.fixture(autouse=True)
def _temporary_storage(tmp_path: Path) -> Iterator[None]:
    documents = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": str(tmp_path), "allow_overwrite": True},
    }
    with override_settings(STORAGES={**storages.backends, "documents": documents}):
        yield


def test_keys_contain_ids_and_hash_never_the_file_name() -> None:
    assert storage.original_key(ORG, DOC, "ab" * 32, "pdf") == (
        f"orgs/{ORG}/documents/{DOC}/{'ab' * 32}.pdf"
    )
    assert storage.derived_key(ORG, DOC, "invoice.xml") == f"orgs/{ORG}/documents/{DOC}/invoice.xml"


def test_write_read_and_delete() -> None:
    key = storage.derived_key(ORG, DOC, "text.txt")
    storage.write(key, b"one")
    storage.write(key, b"two")  # writing the same key again replaces it
    assert storage.read(key) == b"two"
    assert storage.exists(key)
    storage.delete(key)
    assert not storage.exists(key)
    storage.delete(key)  # deleting a missing key is not an error

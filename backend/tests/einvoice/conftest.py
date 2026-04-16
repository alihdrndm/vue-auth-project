from pathlib import Path

import pytest

CORPUS = Path(__file__).resolve().parents[3] / "data" / "corpus"
CORPUS_COMMIT = "d891458e9822e34271a5438497bf924e89955979"


@pytest.fixture(scope="session")
def corpus() -> Path:
    """The pinned ZUGFeRD corpus; tests fail (never skip) when it is missing."""
    marker = CORPUS / ".commit"
    if not marker.exists() or marker.read_text(encoding="utf-8").strip() != CORPUS_COMMIT:
        pytest.fail("The corpus is missing or outdated. Run: cd backend && uv run poe fetch-corpus")
    return CORPUS

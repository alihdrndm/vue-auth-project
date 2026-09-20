"""build_dataset: which corpus files become documents, and a deterministic manifest."""

import json
import re
from pathlib import Path

import pytest
from evals.build_dataset import (
    DUPLICATE,
    NO_TEXT,
    NO_XML,
    NOT_CII,
    NOT_PARSED,
    NOT_READABLE,
    DatasetError,
    build,
    candidates,
    document_id,
    guess_language,
    load_documents,
    load_manifest,
)

from einvoice.parse_cii import parse_cii
from evals import build_dataset
from tests.fixtures.pdfs import LONG_TEXT, blank_pdf, text_pdf, with_attachment

REPO = Path(__file__).resolve().parents[3]
S01_UBL = (REPO / "samples" / "S01-RE-2026-0412.xml").read_bytes()
S02_CII = (REPO / "samples" / "S02-BN-88213.xml").read_bytes()
S03_HYBRID = next((REPO / "samples").glob("S03-*.pdf")).read_bytes()
COMMIT = "abc123"

HYBRID = "ZUGFeRDv2/correct/Vendor/hybrid.pdf"
FX_HYBRID = "XML-Rechnung/FX/fx-hybrid.pdf"


def _without_grand_total(xml: bytes) -> bytes:
    return re.sub(rb"<ram:GrandTotalAmount[^>]*>[^<]*</ram:GrandTotalAmount>", b"", xml)


def _text_pdf_with(xml: bytes) -> bytes:
    return with_attachment(text_pdf([LONG_TEXT]), "factur-x.xml", xml)


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    files = {
        HYBRID: S03_HYBRID,
        "ZUGFeRDv2/correct/Vendor/later-copy.pdf": S03_HYBRID,
        FX_HYBRID: _text_pdf_with(S02_CII),
        "XML-Rechnung/FX/plain.pdf": text_pdf([LONG_TEXT]),
        "ZUGFeRDv2/correct/Vendor/scan.pdf": with_attachment(blank_pdf(), "factur-x.xml", S02_CII),
        "ZUGFeRDv2/correct/Vendor/ubl.pdf": _text_pdf_with(S01_UBL),
        "ZUGFeRDv2/correct/Vendor/no-total.pdf": _text_pdf_with(_without_grand_total(S02_CII)),
        "ZUGFeRDv2/correct/Vendor/corrupt.PDF": b"%PDF-1.4 this is not a PDF",
        # Not candidates: outside `correct` and FX, or not a PDF.
        "ZUGFeRDv2/fail/Vendor/hybrid.pdf": S03_HYBRID,
        "ZUGFeRDv2/correct-ish/hybrid.pdf": S03_HYBRID,
        "XML-Rechnung/CII/invoice.xml": S02_CII,
        "ZUGFeRDv2/correct/Vendor/invoice.xml": S02_CII,
    }
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    (root / ".commit").write_text(COMMIT + "\n", encoding="utf-8")
    return root


def test_candidates_are_pdfs_under_correct_or_fx(corpus: Path) -> None:
    assert candidates(corpus) == [
        "XML-Rechnung/FX/fx-hybrid.pdf",
        "XML-Rechnung/FX/plain.pdf",
        "ZUGFeRDv2/correct/Vendor/corrupt.PDF",
        "ZUGFeRDv2/correct/Vendor/hybrid.pdf",
        "ZUGFeRDv2/correct/Vendor/later-copy.pdf",
        "ZUGFeRDv2/correct/Vendor/no-total.pdf",
        "ZUGFeRDv2/correct/Vendor/scan.pdf",
        "ZUGFeRDv2/correct/Vendor/ubl.pdf",
    ]


def test_build_keeps_hybrid_cii_with_text_and_names_every_skip(
    corpus: Path, tmp_path: Path
) -> None:
    manifest = build(corpus, tmp_path / "data")

    assert manifest.corpus_commit == COMMIT
    assert manifest.documents == 2
    assert [entry.path for entry in manifest.entries] == [FX_HYBRID, HYBRID]
    assert {item.path: item.reason for item in manifest.skipped} == {
        "XML-Rechnung/FX/plain.pdf": NO_XML,
        "ZUGFeRDv2/correct/Vendor/later-copy.pdf": DUPLICATE,
        "ZUGFeRDv2/correct/Vendor/corrupt.PDF": NOT_READABLE,
        "ZUGFeRDv2/correct/Vendor/no-total.pdf": NOT_PARSED,
        "ZUGFeRDv2/correct/Vendor/scan.pdf": NO_TEXT,
        "ZUGFeRDv2/correct/Vendor/ubl.pdf": NOT_CII,
    }
    assert sum(manifest.skipped_counts.values()) == 6


def test_manifest_entry_describes_the_extraction_input(corpus: Path, tmp_path: Path) -> None:
    data = tmp_path / "data"
    build(corpus, data)
    entry = next(entry for entry in load_manifest(data).entries if entry.path == FX_HYBRID)
    document = next(doc for doc in load_documents(data) if doc.path == FX_HYBRID)

    assert entry.id == "XML-Rechnung__FX__fx-hybrid"
    assert len(entry.sha256) == 64
    assert entry.language == "de"
    assert entry.profile == "XRECHNUNG"
    assert entry.text_chars == len(document.text)
    assert entry.text_truncated is False
    assert document.text.startswith("--- page 1 ---\nRechnung Nr. RE-2026-0001")
    assert document.truth == parse_cii(S02_CII)


def test_manifest_is_byte_identical_on_a_rerun(corpus: Path, tmp_path: Path) -> None:
    data = tmp_path / "data"
    build(corpus, data)
    first = (data / "manifest.json").read_bytes()
    build(corpus, data)

    assert (data / "manifest.json").read_bytes() == first
    assert b"\r\n" not in first
    assert "generated_at" not in json.loads(first)


def test_rebuild_removes_documents_that_left_the_dataset(corpus: Path, tmp_path: Path) -> None:
    data = tmp_path / "data"
    build(corpus, data)
    (corpus / FX_HYBRID).unlink()
    build(corpus, data)

    cached = sorted(path.name for path in build_dataset.cache_dir(data).iterdir())
    assert cached == [
        "ZUGFeRDv2__correct__Vendor__hybrid.json",
        "ZUGFeRDv2__correct__Vendor__hybrid.txt",
    ]


def test_long_text_is_cut_at_the_app_limit(corpus: Path, tmp_path: Path) -> None:
    from invoices.extraction import TEXT_LIMIT

    long_pages = [[f"Zeile {page}-{line} " + "x" * 80 for line in range(60)] for page in range(4)]
    (corpus / FX_HYBRID).write_bytes(with_attachment(text_pdf(long_pages), "factur-x.xml", S02_CII))
    entry = next(
        entry for entry in build(corpus, tmp_path / "data").entries if entry.path == FX_HYBRID
    )

    assert entry.text_chars == TEXT_LIMIT
    assert entry.text_truncated is True


def test_load_documents_refuses_a_stale_cache(corpus: Path, tmp_path: Path) -> None:
    data = tmp_path / "data"
    manifest = build(corpus, data)
    entry = manifest.entries[0]
    cached = build_dataset.cache_dir(data) / f"{entry.id}.json"
    stale = cached.read_text(encoding="utf-8").replace(entry.sha256, "0" * 64)
    cached.write_text(stale, encoding="utf-8")

    with pytest.raises(DatasetError, match="stale"):
        list(load_documents(data))


def test_load_documents_needs_the_cache(corpus: Path, tmp_path: Path) -> None:
    data = tmp_path / "data"
    manifest = build(corpus, data)
    (build_dataset.cache_dir(data) / f"{manifest.entries[0].id}.txt").unlink()

    with pytest.raises(DatasetError, match="not cached"):
        list(load_documents(data))


def test_load_manifest_needs_a_build(tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match="eval-dataset"):
        load_manifest(tmp_path)


def test_build_needs_the_pinned_corpus(tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match="fetch-corpus"):
        build(tmp_path / "missing", tmp_path / "data")


def test_main_prints_the_count_and_the_skip_reasons(
    corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert build_dataset.main(["--corpus", str(corpus), "--out", str(tmp_path / "data")]) == 0
    out = capsys.readouterr().out
    assert "2 documents (corpus abc123)" in out
    assert f"1  {NOT_CII}" in out
    assert "6 skipped:" in out


def test_main_fails_without_a_corpus(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert build_dataset.main(["--corpus", str(tmp_path), "--out", str(tmp_path / "d")]) == 1
    assert "fetch-corpus" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("Rechnung Nr. 1\nRechnungsdatum 01.03.2026\nNetto 10,00 Brutto 11,90 MwSt", "de"),
        ("Invoice No. 1\nInvoice date 2026-03-01\nTotal due, VAT and payment terms", "en"),
        ("Facture n° 1\nMontant HT 10,00 TVA 2,00 TTC 12,00\nÉchéance", "fr"),
        ("12345 67890 ---", "unknown"),
        ("Rechnung invoice", "de"),  # a tie goes to the language listed first
    ],
)
def test_guess_language(text: str, language: str) -> None:
    assert guess_language(text) == language


def test_document_id_is_file_name_safe() -> None:
    assert document_id("ZUGFeRDv2/correct/Some Vendor/Rechnung (1).pdf") == (
        "ZUGFeRDv2__correct__Some_Vendor__Rechnung_1_"
    )

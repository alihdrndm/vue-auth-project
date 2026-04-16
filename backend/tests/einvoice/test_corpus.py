"""Tests against the pinned ZUGFeRD corpus (downloaded by `uv run poe fetch-corpus`)."""

from pathlib import Path

from einvoice.detect import Kind, Syntax, detect
from einvoice.model import CanonicalInvoice
from einvoice.parse_cii import parse_cii
from einvoice.parse_ubl import parse_ubl

# Deliberately inconsistent test file of the corpus; its UBL and CII versions differ on purpose.
NOT_VALIDATING = "not_validating_full_invoice_based_onTest_EeISI_300_CENfullmodel"


def files(corpus: Path, pattern: str) -> list[Path]:
    return sorted(path for path in corpus.glob(pattern) if path.is_file())


def parse_detected(path: Path) -> CanonicalInvoice:
    detection = detect(path.read_bytes(), path.name)
    assert detection.kind in (Kind.XML, Kind.HYBRID_PDF), f"{path.name}: {detection.kind}"
    assert detection.xml is not None
    return parse_ubl(detection.xml) if detection.syntax is Syntax.UBL else parse_cii(detection.xml)


def test_parse_corpus_correct(corpus: Path) -> None:
    """Every XML and hybrid PDF in a `correct` folder, and every XML-Rechnung file, parses."""
    paths = (
        files(corpus, "XML-Rechnung/UBL/*.xml")
        + files(corpus, "XML-Rechnung/CII/*.xml")
        + files(corpus, "XML-Rechnung/FX/*.pdf")
        + files(corpus, "ZUGFeRDv2/correct/**/*.pdf")
        + files(corpus, "ZUGFeRDv2/correct/**/*.xml")
    )
    assert len(paths) == 172, "the pinned corpus has 172 such files"
    failures = {}
    for path in paths:
        try:
            parse_detected(path)
        except Exception as error:  # collect every failure, not only the first
            failures[str(path.relative_to(corpus))] = f"{type(error).__name__}: {error}"
    assert failures == {}


def test_parse_corpus_ubl_and_cii_versions_agree(corpus: Path) -> None:
    """The corpus has each XML-Rechnung invoice in both syntaxes: a cross-check of the XPaths.

    Notes are excluded: UBL carries the note's subject code inside the text (`#REG#...`),
    CII in its own element, and the mapping takes each note's text as it is.
    """
    compared = 0
    for ubl_path in files(corpus, "XML-Rechnung/UBL/*.ubl.xml"):
        if ubl_path.name.startswith(NOT_VALIDATING):
            continue
        cii_path = ubl_path.with_name(ubl_path.name.replace(".ubl.xml", ".cii.xml"))
        cii_path = corpus / "XML-Rechnung" / "CII" / cii_path.name
        ubl = parse_ubl(ubl_path.read_bytes()).model_dump(exclude={"notes"})
        cii = parse_cii(cii_path.read_bytes()).model_dump(exclude={"notes"})
        assert ubl == cii, ubl_path.name
        compared += 1
    assert compared >= 25


# Two Mustang samples predate ZUGFeRD 1.0: their root is in the draft namespace
# urn:un:unece:uncefact:data:standard:CBFBUY:5, so rule D2 calls them unsupported.
PRE_RELEASE_ZUGFERD1 = {
    "MustangGnuaccountingBeispielRE-20140519_499.pdf",
    "MustangGnuaccountingBeispielRE-20140522_501.pdf",
}


def test_D2_corpus_zugferd1_correct_is_legacy(corpus: Path) -> None:
    paths = files(corpus, "ZUGFeRDv1/correct/**/*.pdf")
    assert len(paths) == 21
    for path in paths:
        expected = (
            Kind.HYBRID_PDF_UNSUPPORTED
            if path.name in PRE_RELEASE_ZUGFERD1
            else Kind.LEGACY_ZUGFERD1
        )
        assert detect(path.read_bytes(), path.name).kind is expected, path.name


def test_D3_corpus_unstructured_pdf_is_plain(corpus: Path) -> None:
    (path,) = files(corpus, "unstructured/*.pdf")
    detection = detect(path.read_bytes(), path.name)
    assert detection.kind is Kind.PDF_TEXT
    assert detection.xml is None


def test_detect_corpus_reference_invoice(corpus: Path) -> None:
    invoice = parse_detected(corpus / "XML-Rechnung" / "UBL" / "XRECHNUNG_Einfach.ubl.xml")
    assert invoice.invoice_number == "471102"
    assert str(invoice.gross_total) == "529.87"
    assert invoice.seller.vat_id == "DE123456789"
    assert invoice.payee_iban == "DE02120300000000202051"

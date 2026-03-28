import pytest

from einvoice.errors import CorruptPdfError, UnsafeXmlError
from einvoice.pdf import embedded_invoice_xml, extract_text, is_pdf
from tests.fixtures.pdfs import LONG_TEXT, blank_pdf, text_pdf, with_attachment

CII = (
    b'<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:'
    b'CrossIndustryInvoice:100"/>'
)


def test_is_pdf_checks_the_magic_bytes() -> None:
    assert is_pdf(b"%PDF-1.7 ...")
    assert not is_pdf(b"<Invoice/>")


def test_factur_x_attachment_is_found() -> None:
    assert embedded_invoice_xml(with_attachment(text_pdf([LONG_TEXT]), "factur-x.xml", CII)) == CII


@pytest.mark.parametrize("name", ["xrechnung.xml", "XRechnung.XML", "zugferd-invoice.xml"])
def test_fallback_names_are_matched_case_insensitively(name: str) -> None:
    pdf = with_attachment(text_pdf([LONG_TEXT]), name, CII)
    assert embedded_invoice_xml(pdf) == CII


def test_other_xml_attachments_are_not_invoices() -> None:
    pdf = with_attachment(text_pdf([LONG_TEXT]), "metadata.xml", b"<meta/>")
    assert embedded_invoice_xml(pdf) is None


def test_pdf_without_attachments_has_no_xml() -> None:
    assert embedded_invoice_xml(text_pdf([LONG_TEXT])) is None


def test_xxe_in_hybrid_pdf_attachment_is_refused_before_any_parser_sees_it() -> None:
    payload = (
        b'<?xml version="1.0"?><!-- a long comment -->'
        + b"<!--"
        + b"x" * 10_000
        + b"-->"
        + b'<!DOCTYPE r [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><r>&xxe;</r>'
    )
    pdf = with_attachment(text_pdf([LONG_TEXT]), "factur-x.xml", payload)
    with pytest.raises(UnsafeXmlError):
        embedded_invoice_xml(pdf)


def test_text_of_the_first_six_pages_and_the_page_count() -> None:
    pages = [[f"page {number}"] for number in range(1, 9)]
    text = extract_text(text_pdf(pages))
    assert text.page_count == 8
    assert len(text.pages) == 6
    assert text.pages[0].strip() == "page 1"


def test_non_whitespace_characters_are_counted() -> None:
    text = extract_text(text_pdf([["a b", "c"]]))
    assert text.non_whitespace_chars == 3


def test_scan_has_no_text() -> None:
    text = extract_text(blank_pdf(2))
    assert text.page_count == 2
    assert text.non_whitespace_chars == 0


def test_corrupt_pdf_raises_for_xml_and_text() -> None:
    with pytest.raises(CorruptPdfError):
        embedded_invoice_xml(b"%PDF-1.4\nthis is not a pdf")
    with pytest.raises(CorruptPdfError):
        extract_text(b"%PDF-1.4\nthis is not a pdf")


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-be", "utf-32", "utf-32-le"])
def test_xxe_doctype_is_found_in_utf16_and_utf32_attachments(encoding: str) -> None:
    payload = f'<?xml version="1.0" encoding="{encoding}"?><!DOCTYPE r><r/>'.encode(encoding)
    pdf = with_attachment(text_pdf([LONG_TEXT]), "factur-x.xml", payload)
    with pytest.raises(UnsafeXmlError):
        embedded_invoice_xml(pdf)


def test_xxe_doctype_in_a_utf7_attachment_is_refused() -> None:
    # "+ADw-" and friends are UTF-7 for "<", "!" and "["; a byte scan would miss the DOCTYPE.
    payload = (
        b'<?xml version="1.0" encoding="UTF-7"?>'
        b"+ADwAIQ-DOCTYPE r +AFsAPAAh-ENTITY e +ACI-PWNED+ACIAPgBd-+AD4-<r>&e;</r>"
    )
    pdf = with_attachment(text_pdf([LONG_TEXT]), "factur-x.xml", payload)
    with pytest.raises(UnsafeXmlError):
        embedded_invoice_xml(pdf)


def test_malformed_xml_attachment_does_not_stop_the_search() -> None:
    pdf = with_attachment(text_pdf([LONG_TEXT]), "broken.xml", b"<r>")
    assert embedded_invoice_xml(pdf) is None

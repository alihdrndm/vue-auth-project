"""Reading PDFs: the embedded invoice XML (hybrid PDFs) and the text layer."""

import logging
from dataclasses import dataclass
from io import BytesIO

import facturx
import pdfplumber
from pypdf import PdfReader

from einvoice.errors import CorruptPdfError, UnsafeXmlError

logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF-"
# Names under which hybrid PDFs embed the invoice (rule D1 fallback), compared lower-cased.
INVOICE_ATTACHMENT_NAMES = frozenset({"factur-x.xml", "zugferd-invoice.xml", "xrechnung.xml"})
TEXT_PAGES = 6


@dataclass(frozen=True)
class PdfText:
    pages: list[str]  # text of the first TEXT_PAGES pages, one string per page
    page_count: int  # pages in the whole document

    @property
    def non_whitespace_chars(self) -> int:
        return sum(len("".join(page.split())) for page in self.pages)


def is_pdf(data: bytes) -> bool:
    return data.startswith(PDF_MAGIC)


def _reader(data: bytes) -> PdfReader:
    try:
        return PdfReader(BytesIO(data))
    except Exception as error:  # broad on purpose: a malformed PDF can fail in many ways
        raise CorruptPdfError from error


def _xml_attachments(reader: PdfReader) -> list[tuple[str, bytes]]:
    attachments: list[tuple[str, bytes]] = []
    try:
        for name, contents in reader.attachments.items():
            if name.lower().endswith(".xml"):
                attachments.extend((name, content) for content in contents)
    except Exception as error:  # broad on purpose: a malformed PDF can fail in many ways
        raise CorruptPdfError from error
    return attachments


# XML may be encoded in UTF-16 or UTF-32; a DOCTYPE must be found in any of them.
_ENCODINGS = ("utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be")


def _mentions_doctype(content: bytes) -> bool:
    # The whole attachment is scanned: corpus files open with long licence comments.
    return any(
        "<!doctype" in content.decode(encoding, errors="ignore").lower() for encoding in _ENCODINGS
    )


def _refuse_doctype(attachments: list[tuple[str, bytes]]) -> None:
    # factur-x parses attachments with lxml's default parser before we see them, so any
    # DOCTYPE is refused here first (see docs/DECISIONS.md).
    for _name, content in attachments:
        if _mentions_doctype(content):
            raise UnsafeXmlError


def embedded_invoice_xml(data: bytes) -> bytes | None:
    """The invoice XML embedded in a PDF, or None for a PDF without one (rule D1)."""
    reader = _reader(data)
    attachments = _xml_attachments(reader)
    if not attachments:
        return None
    _refuse_doctype(attachments)
    try:
        _filename, xml_bytes = facturx.get_xml_from_pdf(data, check_xsd=False)
    except Exception as error:  # broad on purpose: factur-x raises bare Exception
        logger.info("factur-x could not read the attachments: %s", type(error).__name__)
        xml_bytes = None
    if isinstance(xml_bytes, bytes) and xml_bytes:
        return xml_bytes
    for name, content in attachments:
        if name.lower() in INVOICE_ATTACHMENT_NAMES and content:
            return content
    return None


def extract_text(data: bytes, max_pages: int = TEXT_PAGES) -> PdfText:
    """Text of the first `max_pages` pages (rule D3) and the total page count."""
    try:
        with pdfplumber.open(BytesIO(data)) as document:
            pages = [page.extract_text() or "" for page in document.pages[:max_pages]]
            return PdfText(pages=pages, page_count=len(document.pages))
    except Exception as error:  # broad on purpose: pdfminer raises many unrelated types
        raise CorruptPdfError from error

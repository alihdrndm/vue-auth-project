"""Builders for small test PDFs, made in code so no binary fixture has to be committed."""

from io import BytesIO

from pypdf import PdfWriter


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text_pdf(pages: list[list[str]]) -> bytes:
    """A valid PDF whose pages carry the given lines as a real text layer (Helvetica)."""
    objects: list[bytes] = []
    page_count = len(pages)
    # 1 catalog, 2 page tree, 3 font, then per page: page object + content stream.
    kids = " ".join(f"{4 + 2 * index} 0 R" for index in range(page_count))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for index, lines in enumerate(pages):
        content_id = 5 + 2 * index
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode()
        )
        operations = ["BT", "/F1 11 Tf", "14 TL", "50 800 Td"]
        for line in lines:
            operations.append(f"({_escape(line)}) Tj T*")
        operations.append("ET")
        stream = "\n".join(operations).encode("latin-1")
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref_start = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        output.write(f"{offset:010d} 00000 n \n".encode())
    trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
    output.write(f"{trailer}startxref\n{xref_start}\n%%EOF\n".encode())
    return output.getvalue()


def blank_pdf(page_count: int = 1) -> bytes:
    """A PDF with pages but no text layer, like a scan."""
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=595, height=842)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def with_attachment(pdf: bytes, filename: str, content: bytes) -> bytes:
    """The given PDF with one embedded file added."""
    writer = PdfWriter(clone_from=BytesIO(pdf))
    writer.add_attachment(filename, content)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


LONG_TEXT = [
    "Rechnung Nr. RE-2026-0001",
    "Rechnungsdatum: 01.03.2026",
    "Druckerei Sommer GmbH, Musterstrasse 1, 04109 Leipzig",
    "An: Holzwerk Brandt GmbH, Leipzig",
    "Pos. 1  Visitenkarten 500 Stueck   1.000,00 EUR",
    "Netto 1.000,00 EUR  USt 19 %  190,00 EUR  Brutto 1.190,00 EUR",
    "Zahlbar innerhalb 30 Tagen netto. IBAN DE89 3704 0044 0532 0130 00",
]

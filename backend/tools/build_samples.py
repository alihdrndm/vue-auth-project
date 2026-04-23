"""Build the sandbox sample set into samples/ (HANDOFF section 12, "How the seed works").

Run as `uv run poe build-samples`. It writes the twelve files, `samples/manifest.json`
and `samples/precomputed/`, and refuses to finish if any sample does not detect and
validate exactly as the sandbox table says. The output is committed; the API's seed
reads it and never runs this builder.
"""

import hashlib
import io
import json
import shutil
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR / "src"))

import facturx  # noqa: E402 - after the path set-up above
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.pdfgen.canvas import Canvas  # noqa: E402
from sample_data import BUYER, SAMPLES, Sample  # noqa: E402
from stdnum import iban  # noqa: E402
from stdnum.eu import vat  # noqa: E402

from einvoice.detect import Detection, detect, format_label  # noqa: E402
from einvoice.model import CanonicalInvoice  # noqa: E402
from einvoice.parse_cii import parse_cii  # noqa: E402
from einvoice.parse_ubl import parse_ubl  # noqa: E402
from einvoice.pdf import extract_text  # noqa: E402
from einvoice.validate import ValidationReport, validate  # noqa: E402
from einvoice.visualize import visualize  # noqa: E402
from einvoice.write import to_cii, to_ubl  # noqa: E402

SAMPLES_DIR = BACKEND_DIR.parent / "samples"
PRECOMPUTED_DIR = SAMPLES_DIR / "precomputed"
FIXED_DATE = datetime(2026, 3, 1, tzinfo=UTC)


def euro(value: Decimal) -> str:
    """German number format: 1.190,00 EUR."""
    text = f"{value:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return f"{text} EUR"


def german_date(value: object) -> str:
    return value.strftime("%d.%m.%Y") if hasattr(value, "strftime") else ""


def printed_lines(sample: Sample) -> list[str]:
    """What the visible invoice says, line by line (German, like a real supplier)."""
    invoice = sample.invoice
    seller = invoice.seller
    buyer = invoice.buyer
    gross = sample.printed_gross or invoice.gross_total
    payable = sample.printed_gross or invoice.payable_amount or invoice.gross_total
    title = "Gutschrift" if invoice.is_credit_note else "Rechnung"
    lines = [
        f"{seller.name}",
        f"{seller.street}, {seller.postcode} {seller.city}",
        f"USt-IdNr.: {seller.vat_id}",
        "",
        f"An: {buyer.name}",
        f"{buyer.street}, {buyer.postcode} {buyer.city}",
        f"USt-IdNr.: {buyer.vat_id}",
        "",
        title,
        f"Rechnungsnummer: {invoice.invoice_number}",
        f"Rechnungsdatum: {german_date(invoice.issue_date)}",
    ]
    if invoice.due_date is not None:
        lines.append(f"Fällig am: {german_date(invoice.due_date)}")
    if invoice.buyer_reference:
        lines.append(f"Ihre Referenz: {invoice.buyer_reference}")
    lines += [
        "",
        "Pos.  Beschreibung                                   Menge   Einzelpreis   Netto",
    ]
    for item in invoice.lines:
        lines.append(
            f"{item.line_id}     {item.description}   {item.quantity:.0f}   "
            f"{euro(item.unit_price or Decimal(0))}   {euro(item.net_amount or Decimal(0))}"
        )
    tax_label = (
        "Steuerschuldnerschaft des Leistungsempfängers (Reverse Charge)"
        if invoice.tax_total == 0
        else "USt 19 %"
    )
    lines += [
        "",
        f"Netto: {euro(invoice.net_total or Decimal(0))}",
        f"{tax_label}: {euro(invoice.tax_total or Decimal(0))}",
        f"Brutto: {euro(gross)}",
        f"Zahlbetrag: {euro(payable)}",
        "",
        f"Zahlungsbedingungen: {invoice.payment_terms}",
        f"IBAN: {iban.format(invoice.payee_iban or '')}",
    ]
    return lines


def render_pdf(lines: list[str]) -> bytes:
    """A one-page PDF with a real text layer (ReportLab, reproducible output)."""
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=A4, invariant=1)
    canvas.setFont("Helvetica", 10)
    y = A4[1] - 60
    for line in lines:
        if line in ("Rechnung", "Gutschrift"):
            canvas.setFont("Helvetica-Bold", 14)
            canvas.drawString(50, y, line)
            canvas.setFont("Helvetica", 10)
        else:
            canvas.drawString(50, y, line)
        y -= 16
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def render_scan(lines: list[str]) -> bytes:
    """An image of the invoice saved as a PDF page: no text layer, like a scan (150 dpi)."""
    width, height = 1240, 1754  # A4 at 150 dpi
    image = Image.new("L", (width, height), color=246)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=22)
    y = 120
    for line in lines:
        draw.text((110, y), line, fill=30, font=font)
        y += 34
    tilted = image.rotate(0.7, resample=Image.Resampling.BICUBIC, fillcolor=246)
    buffer = io.BytesIO()
    # Fixed dates keep the scan byte-for-byte reproducible.
    tilted.save(
        buffer,
        format="PDF",
        resolution=150,
        creationDate=FIXED_DATE.utctimetuple(),
        modDate=FIXED_DATE.utctimetuple(),
    )
    return buffer.getvalue()


def build_file(sample: Sample) -> bytes:
    invoice = sample.invoice
    if sample.form == "ubl":
        return to_ubl(invoice, sample.write_options)
    if sample.form == "cii":
        return to_cii(invoice, sample.write_options, sample.guideline_id)
    if sample.form == "hybrid":
        xml = to_cii(invoice, sample.write_options, sample.guideline_id)
        visible = render_pdf(printed_lines(sample))
        embedded: bytes = facturx.generate_from_binary(
            visible, xml, flavor="factur-x", level=sample.facturx_level, check_xsd=True, lang="de"
        )
        return embedded
    if sample.form == "plain_pdf":
        return render_pdf(printed_lines(sample))
    return render_scan(printed_lines(sample))


def parsed(detection: Detection) -> CanonicalInvoice | None:
    if detection.xml is None or detection.syntax is None:
        return None
    return parse_ubl(detection.xml) if detection.syntax.value == "ubl" else parse_cii(detection.xml)


def detection_summary(detection: Detection, label: str) -> dict[str, object]:
    return {
        "kind": detection.kind.value,
        "syntax": detection.syntax.value if detection.syntax else None,
        "profile": detection.profile.value if detection.profile else None,
        "profile_version": detection.profile_version,
        "spec_id": detection.spec_id,
        "has_text_layer": detection.has_text_layer,
        "page_count": detection.page_count,
        "is_einvoice": detection.is_einvoice,
        "format_label": label,
        "notes": detection.notes,
    }


def report_json(report: ValidationReport) -> dict[str, object]:
    return {
        "status": report.status,
        "engine": report.engine,
        "xsd_ok": report.xsd_ok,
        "fatal_count": report.fatal_count,
        "warning_count": report.warning_count,
        "issues": [issue.__dict__ for issue in report.issues],
    }


def check(sample: Sample, label: str, report: ValidationReport) -> list[str]:
    """Problems with a built sample, measured against the sandbox table."""
    problems = []
    if label != sample.format_label:
        problems.append(f"{sample.id}: format label {label!r}, expected {sample.format_label!r}")
    fatal = [issue.rule_id for issue in report.issues if issue.severity == "fatal"]
    if sample.form in ("plain_pdf", "scan") or sample.facturx_level == "basicwl":
        expected_status = "not_applicable"
    else:
        expected_status = "invalid" if sample.expected_fatal_rules else "valid"
    if report.status != expected_status:
        problems.append(f"{sample.id}: validation {report.status}, expected {expected_status}")
    if fatal != sample.expected_fatal_rules:
        problems.append(f"{sample.id}: fatal rules {fatal}, expected {sample.expected_fatal_rules}")
    seller_vat = sample.invoice.seller.vat_id
    if seller_vat is None or not vat.is_valid(seller_vat):
        problems.append(f"{sample.id}: seller VAT ID is not valid")
    return problems


def write_json(path: Path, data: object) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    if SAMPLES_DIR.exists():
        shutil.rmtree(SAMPLES_DIR)
    PRECOMPUTED_DIR.mkdir(parents=True)
    manifest_samples = []
    problems: list[str] = []
    for sample in SAMPLES:
        data = build_file(sample)
        (SAMPLES_DIR / sample.filename).write_bytes(data)
        detection = detect(data, sample.filename)
        invoice = parsed(detection)
        label = format_label(detection, invoice.type_code if invoice else None)
        report = validate(detection)
        problems += check(sample, label, report)
        precomputed: dict[str, object] = {
            "id": sample.id,
            "detection": detection_summary(detection, label),
            "validation": report_json(report),
            "invoice": invoice.model_dump(mode="json") if invoice else None,
            "text": extract_text(data).as_text() if detection.page_count else None,
        }
        write_json(PRECOMPUTED_DIR / f"{sample.id}.json", precomputed)
        if detection.kind.value == "hybrid_pdf" and detection.xml is not None:
            (PRECOMPUTED_DIR / f"{sample.id}.xml").write_bytes(detection.xml)
        page = visualize(detection)
        if page is not None:
            (PRECOMPUTED_DIR / f"{sample.id}.visualization.html").write_text(
                page, encoding="utf-8", newline="\n"
            )
        entry: dict[str, object] = {
            "id": sample.id,
            "file": sample.filename,
            "sha256": hashlib.sha256(data).hexdigest(),
            "received_offset_minutes": sample.received_offset_minutes,
            "format_label": label,
            "expected_checks": sample.expected_checks,
            "expected_status": sample.expected_status,
        }
        if sample.decision is not None:
            entry["decision"] = sample.decision.__dict__
        manifest_samples.append(entry)
        print(f"{sample.id}  {label:<32} {report.status}")
    write_json(
        SAMPLES_DIR / "manifest.json",
        {"buyer": {"name": BUYER.name, "vat_id": BUYER.vat_id}, "samples": manifest_samples},
    )
    for problem in problems:
        print(f"build-samples: {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

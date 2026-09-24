"""The `regex-baseline` system: label-anchored regular expressions, no LLM (HANDOFF "Systems").

It reads German, English and French labels ("Rechnungsnummer", "Invoice No.", "Facture n°")
and takes the value that follows on the same line. It is deliberately simple: it shows what
the LLM adds over a fixed rule set, not the best possible rule set.
"""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from evals.metrics import FIELDS, Values

_GAP = r"[ \t]*[:.#]?[ \t]*(?:n[o°º]\.?|nr\.?|number)?[ \t]*[:.#]?[ \t]*"


def _labels(*words: str) -> re.Pattern[str]:
    return re.compile(r"(?im)\b(?:" + "|".join(words) + r")\b" + _GAP + r"(?P<value>[^\n]+)")


LABELS: dict[str, re.Pattern[str]] = {
    "invoice_number": _labels(
        "rechnungsnummer", "rechnungs-nr", "rechnung", "invoice", "invoice number",
        "facture", "numéro de facture",
    ),
    "issue_date": _labels(
        "rechnungsdatum", "datum", "invoice date", "date of issue", "date", "date de facture",
    ),
    "due_date": _labels("fällig am", "fälligkeitsdatum", "fällig", "due date", "échéance"),
    "seller.vat_id": _labels(
        "ust-idnr", "ust-id", "umsatzsteuer-id", "vat id", "vat number", "vat no",
        "n° tva", "tva intracommunautaire",
    ),
    "payee_iban": _labels("iban"),
    "net_total": _labels(
        "nettobetrag", "netto", "summe netto", "net amount", "net total", "subtotal",
        "total ht", "montant ht",
    ),
    "tax_total": _labels(
        "mwst", "ust", "umsatzsteuer", "mehrwertsteuer", "vat", "tax", "tva", "total tva",
    ),
    "gross_total": _labels(
        "bruttobetrag", "brutto", "gesamtbetrag", "rechnungsbetrag", "total amount",
        "grand total", "invoice total", "total ttc", "montant ttc",
    ),
    "payable_amount": _labels(
        "zahlbetrag", "zu zahlen", "amount due", "amount payable", "balance due",
        "net à payer", "à payer",
    ),
}  # fmt: skip

_DATE = re.compile(r"(\d{1,2})[./](\d{1,2})[./](\d{4})|(\d{4})-(\d{2})-(\d{2})")
_AMOUNT = re.compile(r"-?\d{1,3}(?:[.,' ]\d{3})*(?:[.,]\d{2})|-?\d+(?:[.,]\d{2})")
_IBAN = re.compile(r"\b([A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?)\b")
_VAT_ID = re.compile(r"\b([A-Z]{2}[ ]?[A-Z0-9]{8,12})\b")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9/_.\-]*\d[A-Za-z0-9/_.\-]*")
_CURRENCY = re.compile(r"(EUR|€|USD|\$|GBP|£|CHF)")
_CURRENCY_CODES = {"€": "EUR", "$": "USD", "£": "GBP"}


def _date(text: str) -> str | None:
    match = _DATE.search(text)
    if match is None:
        return None
    day, month, year = (
        (match[1], match[2], match[3]) if match[1] else (match[6], match[5], match[4])
    )
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except ValueError:
        return None


def _amount(text: str) -> str | None:
    matches = _AMOUNT.findall(text)
    if not matches:
        return None
    raw = matches[-1].replace("'", "").replace(" ", "")
    decimal_mark = raw[-3]
    group_mark = "." if decimal_mark == "," else ","
    normalised = raw.replace(group_mark, "").replace(decimal_mark, ".")
    try:
        return str(Decimal(normalised).quantize(Decimal("0.01")))
    except InvalidOperation:
        return None


def _value(field: str, text: str) -> str | None:
    if field in ("issue_date", "due_date"):
        return _date(text)
    if field in ("net_total", "tax_total", "gross_total", "payable_amount"):
        return _amount(text)
    if field == "payee_iban":
        match = _IBAN.search(text.upper())
        return match[1].replace(" ", "") if match else None
    if field == "seller.vat_id":
        match = _VAT_ID.search(text.upper())
        return match[1].replace(" ", "") if match else None
    match = _TOKEN.search(text)  # invoice_number: the first token with a digit
    return match[0].rstrip(".") if match else None


def _first(field: str, text: str) -> str | None:
    for match in LABELS[field].finditer(text):
        found = _value(field, match["value"])
        if found is not None:
            return found
    return None


def _currency(text: str) -> str | None:
    match = _CURRENCY.search(text)
    return _CURRENCY_CODES.get(match[1], match[1]) if match else None


def _seller_name(text: str) -> str | None:
    """The first non-empty line after the first page marker: usually the letterhead."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("--- page"):
            return stripped
    return None


def extract(text: str) -> Values:
    """Every scored field the rules can read from the visible text; the rest is None."""
    values: Values = dict.fromkeys(FIELDS)
    for field in LABELS:
        values[field] = _first(field, text)
    values["currency"] = _currency(text)
    values["seller.name"] = _seller_name(text)
    return values

"""Reading and normalising single values from invoice XML, shared by both parsers."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from lxml import etree

from einvoice.errors import InvoiceParseError

Namespaces = dict[str, str]


def clean(value: str | None) -> str | None:
    """Strip whitespace; an element that is present but empty counts as absent."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def compact_upper(value: str | None) -> str | None:
    """Upper-case with all spaces removed: how IBANs and VAT IDs are compared."""
    if value is None:
        return None
    return "".join(value.split()).upper() or None


def text(element: etree._Element, path: str, namespaces: Namespaces) -> str | None:
    return clean(element.findtext(path, namespaces=namespaces))


def required_text(element: etree._Element, path: str, namespaces: Namespaces, field: str) -> str:
    value = text(element, path, namespaces)
    if value is None:
        raise InvoiceParseError(field, path)
    return value


def to_decimal(value: str | None, field: str, path: str) -> Decimal | None:
    if value is None:
        return None
    try:
        number = Decimal(value)
    except InvalidOperation as error:
        raise InvoiceParseError(field, path, "is not a number") from error
    if not number.is_finite():
        raise InvoiceParseError(field, path, "is not a number")
    return number


def decimal_at(
    element: etree._Element, path: str, namespaces: Namespaces, field: str
) -> Decimal | None:
    return to_decimal(text(element, path, namespaces), field, path)


def to_date(value: str | None, pattern: str, field: str, path: str) -> date | None:
    if value is None:
        return None
    try:
        # A date-only pattern; the naive datetime is discarded at once.
        return datetime.strptime(value, pattern).date()  # noqa: DTZ007
    except ValueError as error:
        raise InvoiceParseError(field, path, "is not a valid date") from error


def to_int(value: str | None, field: str, path: str) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as error:
        raise InvoiceParseError(field, path, "is not a number") from error

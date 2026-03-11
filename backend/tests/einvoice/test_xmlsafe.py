from pathlib import Path

import pytest

from einvoice.errors import InvoiceParseError, UnsafeXmlError, UnsupportedFileError
from einvoice.xmlsafe import parse_xml, strip_leading, to_bytes


def xxe_payload(secret_file: Path) -> bytes:
    return (
        b'<?xml version="1.0"?>\n'
        b'<!DOCTYPE Invoice [<!ENTITY xxe SYSTEM "' + secret_file.as_uri().encode() + b'">]>\n'
        b'<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">&xxe;</Invoice>'
    )


def test_xxe_external_entity_is_refused_and_never_resolved(tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP-SECRET", encoding="utf-8")
    with pytest.raises(UnsafeXmlError) as error:
        parse_xml(xxe_payload(secret))
    assert "TOP-SECRET" not in str(error.value)


def test_xxe_billion_laughs_is_refused() -> None:
    payload = (
        b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
        b'<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">]><r>&lol2;</r>'
    )
    with pytest.raises(UnsafeXmlError):
        parse_xml(payload)


def test_any_doctype_is_refused_even_without_entities() -> None:
    with pytest.raises(UnsafeXmlError):
        parse_xml(b"<!DOCTYPE r><r/>")


def test_unsafe_xml_is_an_unsupported_file() -> None:
    assert issubclass(UnsafeXmlError, UnsupportedFileError)


def test_malformed_xml_is_unsupported() -> None:
    with pytest.raises(UnsupportedFileError, match="well-formed"):
        parse_xml(b"<r><unclosed></r>")


def test_bom_and_leading_whitespace_are_accepted() -> None:
    root = parse_xml(b"\xef\xbb\xbf \n\t<?xml version='1.0'?><r>x</r>")
    assert root.tag == "r"
    assert root.text == "x"


def test_strip_leading_keeps_bytes_without_bom() -> None:
    assert strip_leading(b"  <r/>") == b"<r/>"


def test_to_bytes_serialises_with_declaration() -> None:
    assert to_bytes(parse_xml(b"<r>\xc3\xa4</r>")).startswith(
        b"<?xml version='1.0' encoding='UTF-8'?>"
    )


def test_parse_error_message_names_field_and_path() -> None:
    error = InvoiceParseError("invoice_number", "cbc:ID")
    assert str(error) == "invoice_number is missing (at cbc:ID)"
    assert (error.field, error.path) == ("invoice_number", "cbc:ID")


def test_external_doctype_without_internal_subset_is_refused() -> None:
    with pytest.raises(UnsafeXmlError):
        parse_xml(b'<!DOCTYPE r SYSTEM "http://example.invalid/r.dtd"><r/>')

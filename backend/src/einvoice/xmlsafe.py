"""The one way this package parses XML.

Entity resolution, DTD loading and network access are all off, and any document
with a DOCTYPE is refused outright, so neither external entities (XXE) nor
expanding entities ("billion laughs") can do anything.
"""

from lxml import etree

from einvoice.errors import UnsafeXmlError, UnsupportedFileError

_BOM = b"\xef\xbb\xbf"


def _parser() -> etree.XMLParser:
    # A new parser per call: lxml parsers keep state and are not safe to share across threads.
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        dtd_validation=False,
        load_dtd=False,
        huge_tree=False,
        remove_blank_text=False,
    )


def strip_leading(data: bytes) -> bytes:
    """Remove an optional UTF-8 byte-order mark and leading whitespace."""
    if data.startswith(_BOM):
        data = data[len(_BOM) :]
    return data.lstrip()


def parse_xml(data: bytes) -> etree._Element:
    """Parse untrusted XML bytes and return the root element."""
    try:
        root = etree.fromstring(strip_leading(data), parser=_parser())
    except etree.XMLSyntaxError as error:
        raise UnsupportedFileError("not well-formed XML") from error
    docinfo = root.getroottree().docinfo
    # lxml-stubs does not declare DocInfo.doctype; it is "" when there is no DOCTYPE.
    doctype: str = getattr(docinfo, "doctype", "")
    if doctype or docinfo.internalDTD is not None:
        raise UnsafeXmlError
    return root


def to_bytes(root: etree._Element) -> bytes:
    """Serialise a safely parsed tree; this, never the original bytes, goes to other tools."""
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")

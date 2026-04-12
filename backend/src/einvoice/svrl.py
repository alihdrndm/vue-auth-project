"""SVRL (Schematron Validation Report Language) → validation issues (HANDOFF section 3, step 4)."""

from dataclasses import dataclass
from typing import Literal

from lxml import etree

from einvoice.xmlsafe import parse_xml

SVRL = "http://purl.oclc.org/dsdl/svrl"
NS = {"svrl": SVRL}

Severity = Literal["fatal", "warning", "information"]
Source = Literal["xsd", "en16931", "xrechnung"]

_SEVERITIES: dict[str, Severity] = {
    "fatal": "fatal",
    "error": "fatal",
    "warning": "warning",
    "warn": "warning",
    "information": "information",
    "info": "information",
}


@dataclass(frozen=True)
class Issue:
    rule_id: str
    severity: Severity
    message: str
    location: str
    test: str
    source: Source


def normalise_severity(value: str | None) -> Severity:
    """Map an SVRL flag/role to fatal, warning or information; anything unknown is fatal."""
    return _SEVERITIES.get((value or "").strip().lower(), "fatal")


def _collapse(text: str) -> str:
    return " ".join(text.split())


def _text_of(element: etree._Element | None) -> str:
    if element is None:
        return ""
    return "".join(part for part in element.itertext() if isinstance(part, str))


def parse_svrl(report: bytes, source: Source) -> list[Issue]:
    """Every failed-assert and successful-report becomes one issue, in document order."""
    root = parse_xml(report)
    issues = []
    for element in root.iter(f"{{{SVRL}}}failed-assert", f"{{{SVRL}}}successful-report"):
        flag = element.get("flag") or element.get("role")
        text = element.find("svrl:text", namespaces=NS)
        issues.append(
            Issue(
                rule_id=element.get("id") or "",
                severity=normalise_severity(flag),
                message=_collapse(_text_of(text)),
                location=element.get("location") or "",
                test=element.get("test") or "",
                source=source,
            )
        )
    return issues

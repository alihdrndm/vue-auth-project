"""Validation: XML Schema, EN 16931 Schematron, XRechnung Schematron (HANDOFF section 3).

The KoSIT validator's custom levels for the matching scenario are applied to the
findings, so a verdict here agrees with the official validator (docs/DECISIONS.md).
"""

import threading
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal

from lxml import etree

from einvoice import resources, saxon
from einvoice.detect import Detection, Kind, Profile, Syntax
from einvoice.namespaces import UBL_CREDIT_NOTE_ROOT
from einvoice.scenarios import Scenario, bundled_scenarios
from einvoice.svrl import Issue, Source, parse_svrl
from einvoice.xmlsafe import parse_xml, to_text

Status = Literal["valid", "warnings", "invalid", "not_applicable"]

ENGINE = (
    f"xrechnung-config {resources.CONFIG_RELEASE}; CEN {resources.CEN_RULES_VERSION}; "
    f"saxonche {saxon.SAXONCHE_VERSION}"
)
# MINIMUM and BASIC WL are not EN 16931 invoices; their rules are not applied.
NOT_APPLICABLE_PROFILES = frozenset({Profile.MINIMUM, Profile.BASIC_WL})

_schema_lock = threading.Lock()


@dataclass(frozen=True)
class ValidationReport:
    status: Status
    engine: str
    xsd_ok: bool | None  # None when nothing was validated
    issues: list[Issue]

    @property
    def fatal_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "fatal")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")


NOT_APPLICABLE = ValidationReport(status="not_applicable", engine=ENGINE, xsd_ok=None, issues=[])


@cache
def _schema(path: Path) -> etree.XMLSchema:
    # Vendored, trusted schema files; their imports are local relative paths.
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    return etree.XMLSchema(etree.parse(str(path), parser=parser))


def _xsd_path(syntax: Syntax, root: etree._Element) -> Path:
    if syntax is Syntax.CII:
        return resources.CII_XSD
    if root.tag == UBL_CREDIT_NOTE_ROOT:
        return resources.UBL_CREDIT_NOTE_XSD
    return resources.UBL_INVOICE_XSD


def xsd_issues(root: etree._Element, syntax: Syntax) -> list[Issue]:
    """Step 1: XML Schema errors as fatal issues with rule ID "XSD"."""
    with _schema_lock:  # an lxml schema object is not safe to share between threads
        schema = _schema(_xsd_path(syntax, root))
        schema.validate(root)
        errors = list(schema.error_log)  # type: ignore[call-overload]  # lxml-stubs: the log is iterable
    return [
        Issue(
            rule_id="XSD",
            severity="fatal",
            message=error.message,
            location=f"line {error.line}",
            test="",
            source="xsd",
        )
        for error in errors
    ]


def _schematron(stylesheet: Path, document: str, source: Source) -> list[Issue]:
    return parse_svrl(saxon.transform(stylesheet, document).encode("utf-8"), source)


@cache
def _scenarios() -> list[Scenario]:
    return bundled_scenarios()


def matching_scenario(document: str) -> Scenario | None:
    scenarios = _scenarios()
    index = saxon.first_match(
        document, [(scenario.match, scenario.namespaces) for scenario in scenarios]
    )
    return None if index is None else scenarios[index]


def apply_custom_levels(issues: list[Issue], scenario: Scenario | None) -> list[Issue]:
    if scenario is None:
        return issues
    return [
        Issue(
            rule_id=issue.rule_id,
            severity=scenario.custom_levels.get(issue.rule_id, issue.severity),
            message=issue.message,
            location=issue.location,
            test=issue.test,
            source=issue.source,
        )
        for issue in issues
    ]


def _status(issues: list[Issue]) -> Status:
    if any(issue.severity == "fatal" for issue in issues):
        return "invalid"
    if any(issue.severity == "warning" for issue in issues):
        return "warnings"
    return "valid"


def validate_xml(
    xml: bytes, syntax: Syntax, profile: Profile, profile_version: str | None
) -> ValidationReport:
    """Validate one invoice XML whose syntax and profile `detect` determined."""
    if profile in NOT_APPLICABLE_PROFILES:
        return NOT_APPLICABLE
    root = parse_xml(xml)
    issues = xsd_issues(root, syntax)
    if issues:
        # Like the KoSIT validator: a document that fails the schema is not checked further.
        return ValidationReport(status="invalid", engine=ENGINE, xsd_ok=False, issues=issues)
    document = to_text(root)
    en16931 = resources.EN16931_CII_XSL if syntax is Syntax.CII else resources.EN16931_UBL_XSL
    issues = _schematron(en16931, document, "en16931")
    if profile is Profile.XRECHNUNG and (profile_version or "").startswith("3"):
        xrechnung = (
            resources.XRECHNUNG_CII_XSL if syntax is Syntax.CII else resources.XRECHNUNG_UBL_XSL
        )
        issues += _schematron(xrechnung, document, "xrechnung")
    issues = apply_custom_levels(issues, matching_scenario(document))
    return ValidationReport(status=_status(issues), engine=ENGINE, xsd_ok=True, issues=issues)


def validate(detection: Detection) -> ValidationReport:
    """Validate a detected document; plain PDFs and legacy ZUGFeRD 1 are not applicable."""
    if detection.kind not in (Kind.XML, Kind.HYBRID_PDF) or detection.xml is None:
        return NOT_APPLICABLE
    if detection.syntax is None or detection.profile is None:
        return NOT_APPLICABLE
    return validate_xml(
        detection.xml, detection.syntax, detection.profile, detection.profile_version
    )


def warm_up() -> None:
    """Compile every Schematron stylesheet and load the schemas (worker start-up)."""
    saxon.compile_all(
        [
            resources.EN16931_UBL_XSL,
            resources.EN16931_CII_XSL,
            resources.XRECHNUNG_UBL_XSL,
            resources.XRECHNUNG_CII_XSL,
        ]
    )
    for path in (resources.UBL_INVOICE_XSD, resources.UBL_CREDIT_NOTE_XSD, resources.CII_XSD):
        _schema(path)
    _scenarios()

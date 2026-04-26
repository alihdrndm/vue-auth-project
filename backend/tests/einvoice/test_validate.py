from pathlib import Path

import pytest
from lxml import etree

from einvoice import namespaces as ns
from einvoice.detect import Detection, Kind, Profile, Syntax, detect
from einvoice.errors import UnsafeXmlError
from einvoice.svrl import Issue, Severity
from einvoice.validate import (
    ENGINE,
    _status,
    apply_custom_levels,
    matching_scenario,
    validate,
    validate_xml,
)
from einvoice.xmlsafe import parse_xml, to_text

TESTSUITE = Path(__file__).resolve().parents[2] / "vendor" / "xrechnung-testsuite" / "instances"
VALID_UBL = (TESTSUITE / "standard" / "01.01a-INVOICE_ubl.xml").read_bytes()
VALID_CII = (TESTSUITE / "standard" / "01.01a-INVOICE_uncefact.xml").read_bytes()


def without(xml: bytes, path: str, namespaces: dict[str, str]) -> bytes:
    root = parse_xml(xml)
    for element in root.findall(path, namespaces=namespaces):
        parent = element.getparent()
        assert parent is not None
        parent.remove(element)
    return etree.tostring(root)


def with_spec_id(xml: bytes, spec_id: str) -> bytes:
    root = parse_xml(xml)
    paths = [
        ("cbc:CustomizationID", ns.UBL_NS),
        (
            "rsm:ExchangedDocumentContext/ram:GuidelineSpecifiedDocumentContextParameter/ram:ID",
            ns.CII_NS,
        ),
    ]
    for path, namespaces in paths:
        for element in root.findall(path, namespaces=namespaces):
            element.text = spec_id
    return etree.tostring(root)


def fatal_ids(xml: bytes) -> list[str]:
    report = validate(detect(xml, "a.xml"))
    return [issue.rule_id for issue in report.issues if issue.severity == "fatal"]


def test_valid_xrechnung_in_both_syntaxes() -> None:
    for xml in (VALID_UBL, VALID_CII):
        report = validate(detect(xml, "a.xml"))
        assert report.status in ("valid", "warnings")
        assert report.xsd_ok is True
        assert report.fatal_count == 0
        assert report.engine == ENGINE


def test_engine_names_the_configuration_cen_rules_and_saxon() -> None:
    assert ENGINE.startswith("xrechnung-config v2026-01-31; CEN 1.3.15; saxonche ")


def test_BR_DE_15_missing_buyer_reference_ubl() -> None:
    assert fatal_ids(without(VALID_UBL, "cbc:BuyerReference", ns.UBL_NS)) == ["BR-DE-15"]


def test_BR_DE_15_missing_buyer_reference_cii() -> None:
    xml = without(VALID_CII, ".//ram:BuyerReference", ns.CII_NS)
    assert fatal_ids(xml) == ["BR-DE-15"]


def test_xsd_failure_is_invalid_and_skips_schematron() -> None:
    root = parse_xml(VALID_UBL)
    etree.SubElement(root, f"{{{ns.CBC}}}NotInTheSchema").text = "x"
    report = validate(detect(etree.tostring(root), "a.xml"))
    assert report.status == "invalid"
    assert report.xsd_ok is False
    assert {issue.rule_id for issue in report.issues} == {"XSD"}
    assert all(issue.source == "xsd" for issue in report.issues)
    assert report.issues[0].location.isdigit()  # the line number


def test_en16931_profile_runs_cen_rules_only() -> None:
    xml = with_spec_id(
        without(VALID_UBL, "cbc:BuyerReference", ns.UBL_NS), "urn:cen.eu:en16931:2017"
    )
    report = validate(detect(xml, "a.xml"))
    assert report.status in ("valid", "warnings")  # BR-DE-15 is an XRechnung rule
    assert all(issue.source != "xrechnung" for issue in report.issues)


def test_xrechnung_2x_is_checked_against_en16931_rules_only() -> None:
    spec_id = "urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_2.3"
    xml = with_spec_id(without(VALID_UBL, "cbc:BuyerReference", ns.UBL_NS), spec_id)
    detection = detect(xml, "a.xml")
    assert (detection.profile, detection.profile_version) == (Profile.XRECHNUNG, "2.3")
    assert all(issue.source != "xrechnung" for issue in validate(detection).issues)


@pytest.mark.parametrize(
    ("spec_id", "profile"),
    [
        ("urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic", Profile.BASIC),
        ("urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended", Profile.EXTENDED),
    ],
)
def test_basic_and_extended_get_xsd_and_en16931_rules_only(spec_id: str, profile: Profile) -> None:
    # ASSUMED E3: no Factur-X profile rules and no XRechnung rules (BR-DE-15 would fire).
    xml = with_spec_id(without(VALID_CII, ".//ram:BuyerReference", ns.CII_NS), spec_id)
    detection = detect(xml, "a.xml")
    assert detection.profile is profile
    report = validate(detection)
    assert report.xsd_ok is True
    assert {issue.source for issue in report.issues} <= {"en16931"}
    assert "BR-DE-15" not in {issue.rule_id for issue in report.issues}


@pytest.mark.parametrize("profile", [Profile.MINIMUM, Profile.BASIC_WL])
def test_minimum_and_basic_wl_are_not_applicable(profile: Profile) -> None:
    report = validate_xml(VALID_CII, Syntax.CII, profile, None)
    assert report.status == "not_applicable"
    assert report.issues == []
    assert report.xsd_ok is None


@pytest.mark.parametrize(
    "kind", [Kind.PDF_TEXT, Kind.PDF_NO_TEXT, Kind.LEGACY_ZUGFERD1, Kind.HYBRID_PDF_UNSUPPORTED]
)
def test_plain_and_legacy_pdfs_are_not_applicable(kind: Kind) -> None:
    assert validate(Detection(kind=kind)).status == "not_applicable"


@pytest.mark.parametrize(
    ("severities", "status"),
    [
        ([], "valid"),
        (["information"], "valid"),
        (["information", "warning"], "warnings"),
        (["warning", "fatal"], "invalid"),
    ],
)
def test_status_follows_the_most_severe_issue(severities: list[Severity], status: str) -> None:
    issues = [Issue("R", severity, "m", "/", "t", "en16931") for severity in severities]
    assert _status(issues) == status


def test_custom_levels_of_the_matching_scenario_are_applied() -> None:
    scenario = matching_scenario(to_text(parse_xml(VALID_UBL)))
    assert scenario is not None
    assert scenario.name == "EN16931 XRechnung (UBL Invoice)"
    fatal = Issue("BR-CL-23", "fatal", "m", "/", "t", "en16931")
    other = Issue("BR-01", "fatal", "m", "/", "t", "en16931")
    adjusted = apply_custom_levels([fatal, other], scenario)
    assert [issue.severity for issue in adjusted] == ["warning", "fatal"]


def test_no_matching_scenario_keeps_the_rule_levels() -> None:
    document = to_text(parse_xml(with_spec_id(VALID_UBL, "urn:example:other")))
    assert matching_scenario(document) is None
    issues = [Issue("BR-CL-23", "fatal", "m", "/", "t", "en16931")]
    assert apply_custom_levels(issues, None) == issues


def test_xxe_never_reaches_validation() -> None:
    payload = b'<!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>'
    with pytest.raises(UnsafeXmlError):
        validate_xml(payload, Syntax.UBL, Profile.XRECHNUNG, "3.0")

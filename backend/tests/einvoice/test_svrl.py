import pytest

from einvoice.svrl import Issue, normalise_severity, parse_svrl

REPORT = """<?xml version="1.0" encoding="UTF-8"?>
<svrl:schematron-output xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
  <svrl:active-pattern id="p1"/>
  <svrl:failed-assert id="BR-DE-15" flag="fatal" test="cbc:BuyerReference"
      location="/*:Invoice[namespace-uri()='urn:x'][1]">
    <svrl:text>[BR-DE-15] Das Element
        "Buyer reference" (BT-10) muss
        übermittelt werden.</svrl:text>
  </svrl:failed-assert>
  <svrl:fired-rule context="/"/>
  <svrl:successful-report id="BR-DE-21" role="warning" test="true()" location="/a">
    <svrl:text>Hinweis</svrl:text>
  </svrl:successful-report>
  <svrl:failed-assert id="X-1" test="false()" location="/b">
    <svrl:text>no flag at all</svrl:text>
  </svrl:failed-assert>
</svrl:schematron-output>
""".encode()


def test_every_failed_assert_and_successful_report_is_an_issue() -> None:
    assert parse_svrl(REPORT, "xrechnung") == [
        Issue(
            rule_id="BR-DE-15",
            severity="fatal",
            message='[BR-DE-15] Das Element "Buyer reference" (BT-10) muss übermittelt werden.',
            location="/*:Invoice[namespace-uri()='urn:x'][1]",
            test="cbc:BuyerReference",
            source="xrechnung",
        ),
        Issue(
            rule_id="BR-DE-21",
            severity="warning",
            message="Hinweis",
            location="/a",
            test="true()",
            source="xrechnung",
        ),
        Issue(
            rule_id="X-1",
            severity="fatal",
            message="no flag at all",
            location="/b",
            test="false()",
            source="xrechnung",
        ),
    ]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("fatal", "fatal"),
        ("error", "fatal"),
        ("warning", "warning"),
        ("WARN", "warning"),
        ("information", "information"),
        ("info", "information"),
        ("caution", "fatal"),
        (None, "fatal"),
    ],
)
def test_severity_normalisation_unknown_is_fatal(value: str | None, expected: str) -> None:
    assert normalise_severity(value) == expected


def test_flag_wins_over_role() -> None:
    report = (
        b'<svrl:schematron-output xmlns:svrl="http://purl.oclc.org/dsdl/svrl">'
        b'<svrl:failed-assert id="R" flag="warning" role="fatal"><svrl:text>t</svrl:text>'
        b"</svrl:failed-assert></svrl:schematron-output>"
    )
    assert parse_svrl(report, "en16931")[0].severity == "warning"


def test_empty_report_has_no_issues() -> None:
    assert parse_svrl(b'<s xmlns="http://purl.oclc.org/dsdl/svrl"/>', "en16931") == []

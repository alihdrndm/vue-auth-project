from concurrent.futures import ThreadPoolExecutor

from einvoice import resources, saxon
from einvoice.scenarios import bundled_scenarios, load_scenarios
from einvoice.svrl import Issue, parse_svrl
from einvoice.xmlsafe import parse_xml, to_text
from tests.fixtures import xml

SCENARIOS = b"""<scenarios xmlns="http://www.xoev.de/de/validator/framework/1/scenarios">
  <scenario>
    <name> First </name>
    <namespace prefix="cbc">urn:cbc</namespace>
    <match>exists(/a)</match>
    <createReport>
      <customLevel level="warning">BR-CL-23</customLevel>
      <customLevel level="error">UBL-CR-646</customLevel>
      <customLevel level="information">BR-CO-16</customLevel>
    </createReport>
  </scenario>
  <scenario><name>Second</name><match>true()</match></scenario>
</scenarios>"""


def test_scenarios_are_read_with_their_custom_levels() -> None:
    first, second = load_scenarios(SCENARIOS)
    assert first.name == "First"
    assert first.match == "exists(/a)"
    assert first.namespaces == {"cbc": "urn:cbc"}
    assert first.custom_levels == {
        "BR-CL-23": "warning",
        "UBL-CR-646": "fatal",
        "BR-CO-16": "information",
    }
    assert second.custom_levels == {}


def test_bundled_scenarios_cover_xrechnung_and_plain_en16931() -> None:
    names = [scenario.name for scenario in bundled_scenarios()]
    assert names[0] == "EN16931 XRechnung (UBL Invoice)"
    assert "EN16931 (CII)" in names
    assert len(names) == 11


def test_first_matching_xpath2_expression_wins() -> None:
    document = to_text(parse_xml(xml.ubl()))
    ubl = {"invoice": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"}
    expressions = [("exists(/nothing)", {}), ("exists(/invoice:Invoice)", ubl), ("true()", {})]
    assert saxon.first_match(document, expressions) == 1
    assert saxon.first_match(document, [("false()", {})]) is None


def test_transform_runs_from_several_threads() -> None:
    # Saxon work is handed to its own thread; callers may be any worker thread.
    document = to_text(parse_xml(xml.ubl()))

    def run(_: int) -> list[Issue]:
        return parse_svrl(saxon.transform(resources.EN16931_UBL_XSL, document).encode(), "en16931")

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, range(8)))
    assert all(result == results[0] for result in results)
    assert results[0]  # the bare fixture breaks EN 16931 rules, so there are findings

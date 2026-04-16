"""The KoSIT validator's scenarios: which one a document matches, and its custom levels.

The official validator picks the first scenario whose `match` XPath is true and lets
that scenario raise or lower individual rules ("customLevel"), for example BR-CL-23 to
a warning. Eingang applies the same levels so its verdicts agree with the validator.
"""

from dataclasses import dataclass, field

from einvoice import resources
from einvoice.svrl import Severity
from einvoice.xmlsafe import parse_xml

SCENARIOS_NS = "http://www.xoev.de/de/validator/framework/1/scenarios"
_LEVELS: dict[str, Severity] = {
    "error": "fatal",
    "warning": "warning",
    "information": "information",
}


@dataclass(frozen=True)
class Scenario:
    name: str
    match: str  # an XPath 2.0 expression, evaluated by Saxon
    namespaces: dict[str, str]
    custom_levels: dict[str, Severity] = field(default_factory=dict)


def load_scenarios(xml: bytes) -> list[Scenario]:
    root = parse_xml(xml)
    ns = {"s": SCENARIOS_NS}
    scenarios = []
    for element in root.findall("s:scenario", namespaces=ns):
        namespaces = {
            namespace.get("prefix", ""): (namespace.text or "").strip()
            for namespace in element.findall("s:namespace", namespaces=ns)
        }
        levels = {
            (level.text or "").strip(): _LEVELS[level.get("level", "error")]
            for level in element.iter(f"{{{SCENARIOS_NS}}}customLevel")
        }
        scenarios.append(
            Scenario(
                name=(element.findtext("s:name", namespaces=ns) or "").strip(),
                match=(element.findtext("s:match", namespaces=ns) or "").strip(),
                namespaces=namespaces,
                custom_levels=levels,
            )
        )
    return scenarios


def bundled_scenarios() -> list[Scenario]:
    return load_scenarios(resources.SCENARIOS.read_bytes())

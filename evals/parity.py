"""Validation parity with the official KoSIT validator (HANDOFF "Validation parity").

Reference set: (a) every XML of the vendored XRechnung test suite, (b) every corpus XML in
`XML-Rechnung/`, (c) the embedded XML of every corpus PDF in `ZUGFeRDv2/correct` and
`ZUGFeRDv2/fail`. Each file is validated by Eingang and by the KoSIT validator v1.6.0 (Java,
in the `eclipse-temurin:21-jre` Docker image) with the same configuration release, and the
two are compared per file: the verdict (`valid`/`warnings` accept, `invalid` reject) and the
set of fatal rule IDs. Files that are `not_applicable` for Eingang, or that match no KoSIT
scenario, are excluded and counted.

Run from backend/: `uv run poe eval-parity` (needs Docker; downloads nothing but the image
and the two pinned KoSIT release zips into data/kosit/, which is git-ignored).
"""

import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for entry in (REPO, REPO / "backend" / "src"):  # evals runs outside the backend package
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from einvoice.detect import Kind, detect  # noqa: E402
from einvoice.errors import CorruptPdfError, UnsupportedFileError  # noqa: E402
from einvoice.validate import validate_xml  # noqa: E402

CORPUS = REPO / "data" / "corpus"
TESTSUITE = REPO / "backend" / "vendor" / "xrechnung-testsuite" / "instances"
WORK = REPO / "data" / "kosit"
VALIDATOR_VERSION = "1.6.0"
VALIDATOR_URL = (
    "https://github.com/itplr-kosit/validator/releases/download/"
    f"v{VALIDATOR_VERSION}/validator-{VALIDATOR_VERSION}.zip"
)
VALIDATOR_SHA256 = "dd441387c9cba53c78f2a629779ea350e0d372695bd5cb1108b01160996b7185"
CONFIG_URL = (
    "https://github.com/itplr-kosit/validator-configuration-xrechnung/releases/download/"
    "v2026-01-31/xrechnung-3.0.2-validator-configuration-2026-01-31.zip"
)
CONFIG_SHA256 = "6a5a5911a421b25fbc423f62f93f894df7b236f5d73ca4f84bb222a945082704"
JAVA_IMAGE = "eclipse-temurin:21-jre"
XSD_RULE = "XSD"  # Eingang reports every schema error under this ID

_MESSAGE = re.compile(r"<rep:message\b[^>]*>")
_LEVEL = re.compile(r"\blevel=\"(\w+)\"")
_CODE = re.compile(r"\bcode=\"([^\"]*)\"")
_STEP = re.compile(r"<rep:validationStepResult\b[^>]*\bid=\"([^\"]+)\"[^>]*?(/?)>")


@dataclass(frozen=True)
class Source:
    name: str  # a unique, file-system-safe name for the extracted XML
    origin: str  # where it came from, relative to the repository
    xml: bytes


@dataclass
class Verdict:
    accept: bool
    fatal: frozenset[str]


@dataclass
class FileResult:
    name: str
    origin: str
    eingang: str | None = None  # valid, warnings, invalid; None when excluded
    kosit: str | None = None  # accept, reject; None when excluded
    eingang_fatal: list[str] = field(default_factory=list)
    kosit_fatal: list[str] = field(default_factory=list)
    excluded: str | None = None  # why the file is not compared

    @property
    def verdict_agrees(self) -> bool:
        return (self.eingang in ("valid", "warnings")) == (self.kosit == "accept")

    @property
    def rules_agree(self) -> bool:
        return self.eingang_fatal == self.kosit_fatal


# --- the reference set ------------------------------------------------------------------


def _safe(relative: Path) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", relative.as_posix())


def reference_set() -> list[Source]:
    sources: list[Source] = []
    for path in sorted(TESTSUITE.rglob("*.xml")):
        relative = path.relative_to(REPO)
        sources.append(Source(_safe(relative), relative.as_posix(), path.read_bytes()))
    for path in sorted((CORPUS / "XML-Rechnung").rglob("*.xml")):
        relative = path.relative_to(REPO)
        sources.append(Source(_safe(relative), relative.as_posix(), path.read_bytes()))
    for folder in ("correct", "fail"):
        for path in sorted((CORPUS / "ZUGFeRDv2" / folder).rglob("*.pdf")):
            relative = path.relative_to(REPO)
            xml = _embedded_xml(path)
            if xml is not None:
                sources.append(Source(_safe(relative) + ".xml", relative.as_posix(), xml))
    return sources


def _embedded_xml(path: Path) -> bytes | None:
    try:
        detection = detect(path.read_bytes(), path.name)
    except (UnsupportedFileError, CorruptPdfError):
        return None
    return detection.xml


# --- Eingang ------------------------------------------------------------------------------


def eingang_verdict(source: Source) -> tuple[str | None, list[str], str | None]:
    """(status, sorted fatal rule IDs, exclusion reason)."""
    try:
        detection = detect(source.xml, source.name)
    except UnsupportedFileError as error:
        return None, [], f"unsupported: {error.reason}"
    if detection.kind != Kind.XML or detection.syntax is None or detection.profile is None:
        return None, [], f"not validated: {detection.kind.value}"
    report = validate_xml(
        source.xml, detection.syntax, detection.profile, detection.profile_version
    )
    if report.status == "not_applicable":
        return None, [], f"not applicable: {detection.profile.value}"
    fatal = sorted({issue.rule_id for issue in report.issues if issue.severity == "fatal"})
    return report.status, fatal, None


# --- KoSIT --------------------------------------------------------------------------------


def _download(url: str, sha256: str, target: Path) -> None:
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == sha256:
        return
    with urllib.request.urlopen(url) as response:  # noqa: S310 - pinned https URL
        data = response.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != sha256:
        raise SystemExit(f"parity: {url} has SHA-256 {digest}, expected {sha256}")
    target.write_bytes(data)


def prepare_kosit() -> tuple[Path, Path]:
    """The validator folder and the full configuration folder (both pinned by SHA-256)."""
    WORK.mkdir(parents=True, exist_ok=True)
    validator_zip, config_zip = WORK / "validator.zip", WORK / "config.zip"
    _download(VALIDATOR_URL, VALIDATOR_SHA256, validator_zip)
    _download(CONFIG_URL, CONFIG_SHA256, config_zip)
    validator, config = WORK / "validator", WORK / "config"
    for archive, folder in ((validator_zip, validator), (config_zip, config)):
        if not folder.exists():
            with zipfile.ZipFile(archive) as opened:
                opened.extractall(folder)
    return validator, config


def run_kosit(sources: list[Source], validator: Path, config: Path) -> dict[str, Path]:
    """Run the validator once over every file; returns each file's report path."""
    inputs, outputs = WORK / "parity-in", WORK / "parity-out"
    for folder in (inputs, outputs):
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
    for source in sources:
        (inputs / source.name).write_bytes(source.xml)
    jar = f"/v/validator-{VALIDATOR_VERSION}-standalone.jar"
    command = [
        "docker", "run", "--rm",
        "-v", f"{validator.as_posix()}:/v:ro",
        "-v", f"{config.as_posix()}:/c:ro",
        "-v", f"{inputs.as_posix()}:/in:ro",
        "-v", f"{outputs.as_posix()}:/out",
        JAVA_IMAGE,
        "sh", "-c", f"java -jar {jar} -s /c/scenarios.xml -r /c -o /out /in/*",
    ]  # fmt: skip
    # The validator exits non-zero when any file is rejected; the reports are what count.
    subprocess.run(command, check=False, capture_output=True)  # noqa: S603 - fixed arguments
    return {source.name: outputs / f"{Path(source.name).stem}-report.xml" for source in sources}


def custom_levels(config: Path) -> dict[str, dict[str, str]]:
    """Each scenario's custom rule levels from scenarios.xml, by scenario name.

    KoSIT's report prints every message with the rule's original level and applies the
    scenario's `customLevel` only when it assesses the file, so the comparison applies
    the same levels to decide which rules were fatal.
    """
    text = (config / "scenarios.xml").read_text(encoding="utf-8")
    levels: dict[str, dict[str, str]] = {}
    for scenario in re.findall(r"<scenario>(.*?)</scenario>", text, re.S):
        name = re.search(r"<name>(.*?)</name>", scenario, re.S)
        if name is None:
            continue
        levels[" ".join(name.group(1).split())] = {
            rule.strip(): level
            for level, rule in re.findall(
                r"<customLevel level=\"(\w+)\">([^<]+)</customLevel>", scenario
            )
        }
    return levels


def kosit_verdict(
    report: Path, levels: dict[str, dict[str, str]]
) -> tuple[str | None, list[str], str | None]:
    """(accept/reject, sorted fatal rule IDs, exclusion reason) from one KoSIT report."""
    if not report.exists():
        return None, [], "no KoSIT report"
    text = report.read_text(encoding="utf-8")
    if "<rep:scenarioMatched" not in text:
        return None, [], "no KoSIT scenario"
    name = re.search(r"<s:scenario>\s*<s:name>(.*?)</s:name>", text, re.S)
    custom = levels.get(" ".join(name.group(1).split()), {}) if name else {}
    fatal: set[str] = set()
    for step, body in _steps(text):
        for message in _MESSAGE.findall(body):
            code_match = _CODE.search(message)
            code = code_match.group(1) if code_match else ""
            level_match = _LEVEL.search(message)
            level = custom.get(code, level_match.group(1) if level_match else "error")
            if level != "error":
                continue
            # Schema and well-formedness errors carry no rule code; Eingang calls them XSD.
            fatal.add(XSD_RULE if step in ("val-xsd", "val-xml") or not code else code)
    verdict = "accept" if "<rep:accept" in text else "reject"
    return verdict, sorted(fatal), None


def _steps(text: str) -> list[tuple[str, str]]:
    """Each validation step's ID with the report text up to the next step."""
    matches = list(_STEP.finditer(text))
    steps = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        steps.append((match.group(1), text[match.end() : end]))
    return steps


# --- comparison ---------------------------------------------------------------------------


@dataclass
class Parity:
    files: int
    excluded: int
    verdict_agreement: float
    rule_set_agreement: float
    results: list[FileResult]

    @property
    def disagreements(self) -> list[FileResult]:
        return [
            result
            for result in self.results
            if result.excluded is None and not (result.verdict_agrees and result.rules_agree)
        ]


def compare(
    sources: list[Source], reports: dict[str, Path], levels: dict[str, dict[str, str]]
) -> Parity:
    results = []
    for source in sources:
        result = FileResult(name=source.name, origin=source.origin)
        result.eingang, result.eingang_fatal, ours_excluded = eingang_verdict(source)
        result.kosit, result.kosit_fatal, theirs_excluded = kosit_verdict(
            reports[source.name], levels
        )
        result.excluded = ours_excluded or theirs_excluded
        results.append(result)
    compared = [result for result in results if result.excluded is None]
    count = len(compared) or 1
    return Parity(
        files=len(compared),
        excluded=len(results) - len(compared),
        verdict_agreement=sum(result.verdict_agrees for result in compared) / count,
        rule_set_agreement=sum(result.rules_agree for result in compared) / count,
        results=results,
    )


def main() -> int:
    sources = reference_set()
    validator, config = prepare_kosit()
    reports = run_kosit(sources, validator, config)
    parity = compare(sources, reports, custom_levels(config))
    out = REPO / "evals" / "data" / "cache" / "parity.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "files": parity.files,
        "excluded": parity.excluded,
        "verdict_agreement": parity.verdict_agreement,
        "rule_set_agreement": parity.rule_set_agreement,
        "results": [asdict(result) for result in parity.results],
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    from evals.report import update_latest
    from evals.schema import Parity as ParitySummary

    update_latest(
        parity=ParitySummary(
            files=parity.files,
            excluded=parity.excluded,
            verdict_agreement=parity.verdict_agreement,
            rule_set_agreement=parity.rule_set_agreement,
        )
    )
    print(
        f"parity: {parity.files} files compared, {parity.excluded} excluded; "
        f"verdicts {parity.verdict_agreement:.1%}, rule sets {parity.rule_set_agreement:.1%}"
    )
    for result in parity.disagreements:
        print(
            f"  {result.origin}: eingang {result.eingang} {result.eingang_fatal} / "
            f"kosit {result.kosit} {result.kosit_fatal}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

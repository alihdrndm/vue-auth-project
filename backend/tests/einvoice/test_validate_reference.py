"""Validation against reference files: the KoSIT test suite and the corpus `fail` folders."""

from pathlib import Path

from einvoice.detect import Kind, detect
from einvoice.validate import validate

TESTSUITE = Path(__file__).resolve().parents[2] / "vendor" / "xrechnung-testsuite" / "instances"

# Corpus files in a `fail` folder that we do not reject, each with the reason
# (also listed in docs/DECISIONS.md, "Corpus fail files that are not rejected").
NOT_REJECTED = {
    # MINIMUM and BASIC WL are not EN 16931 invoices; their rules are not applied.
    "Avoir_FR_type380_MINIMUM.pdf": "not_applicable",
    "Avoir_FR_type381_BASICWL.pdf": "not_applicable",
    "Avoir_FR_type381_MINIMUM.pdf": "not_applicable",
    # Net price x quantity differs from the line amount; no EN 16931 rule checks that.
    "noNetPriceValidation.xml": "valid",
    # The attachment is named factur-y.xml: a container problem, the XML itself is valid.
    "wrongFilename.pdf": "valid",
    # Valid XML; the PDF container (iTextSharp 4.1) is not checked (ASSUMED E1).
    "ZUGFeRD_2_fully_compliant_complete.pdf": "valid",
}


def test_testsuite_instances_all_validate() -> None:
    paths = sorted(TESTSUITE.rglob("*.xml"))
    assert len(paths) == 86
    failures = {}
    for path in paths:
        report = validate(detect(path.read_bytes(), path.name))
        if report.status not in ("valid", "warnings"):
            fatal = [issue.rule_id for issue in report.issues if issue.severity == "fatal"]
            failures[str(path.relative_to(TESTSUITE))] = (report.status, fatal)
    assert failures == {}


def test_corpus_fail_files_are_not_hybrid_or_invalid_or_listed(corpus: Path) -> None:
    paths = sorted(path for path in corpus.glob("ZUGFeRDv*/fail/**/*") if path.is_file())
    assert len(paths) == 26
    unexplained = {}
    seen_listed = set()
    for path in paths:
        detection = detect(path.read_bytes(), path.name)
        if detection.kind not in (Kind.XML, Kind.HYBRID_PDF):
            continue  # not detected as hybrid: handled as a plain PDF
        status = validate(detection).status
        if path.name in NOT_REJECTED:
            seen_listed.add(path.name)
            assert status == NOT_REJECTED[path.name], path.name
        elif status != "invalid":
            unexplained[path.name] = status
    assert unexplained == {}
    assert seen_listed == set(NOT_REJECTED)

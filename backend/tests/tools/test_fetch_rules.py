import io
import zipfile
from pathlib import Path

import fetch_rules
import pytest


def make_zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_only_needed_config_files_are_kept() -> None:
    keep = fetch_rules._config_files
    assert keep("resources/xrechnung/3.0.2/xsl/XRechnung-UBL-validation.xsl")
    assert keep("resources/ubl/2.1/xsd/maindoc/UBL-Invoice-2.1.xsd")
    assert keep("resources/ubl/2.1/xsd/common/UBL-CommonBasicComponents-2.1.xsd")
    assert not keep("resources/ubl/2.1/xsd/maindoc/UBL-Order-2.1.xsd")
    assert not keep("EN16931-UBL-validation.xsl")  # the duplicate at the zip root


def test_visualization_keeps_html_parts_only() -> None:
    keep = fetch_rules._visualization_files
    assert keep("xsl/xrechnung-html.xsl")
    assert keep("xsl/l10n/de.xml")
    assert keep("xsl/xrechnung-viewer.css")
    assert keep("xsl/xrechnung-viewer.js")  # read by xrechnung-html.xsl, stripped afterwards
    assert not keep("xsl/xr-pdf.xsl")
    assert not keep("conf/fonts/OFL.txt")


def test_extract_strips_a_shared_top_folder(tmp_path: Path) -> None:
    data = make_zip({"release/README.md": b"x", "release/instances/a.xml": b"<a/>"})
    written = fetch_rules.extract(data, fetch_rules._testsuite_files, tmp_path)
    assert sorted(written) == ["README.md", "instances/a.xml"]
    assert (tmp_path / "instances" / "a.xml").read_bytes() == b"<a/>"


def test_extract_refuses_path_traversal(tmp_path: Path) -> None:
    data = make_zip({"instances/../../evil.xml": b"x", "README.md": b"x"})
    with pytest.raises(fetch_rules.RulesError, match="unsafe"):
        fetch_rules.extract(data, fetch_rules._testsuite_files, tmp_path)


def test_first_download_records_the_hash_and_later_ones_must_match() -> None:
    lock: dict[str, str] = {}
    fetch_rules.verify("https://example.invalid/a.zip", b"one", lock)
    fetch_rules.verify("https://example.invalid/a.zip", b"one", lock)
    with pytest.raises(fetch_rules.RulesError, match="SHA-256 mismatch"):
        fetch_rules.verify("https://example.invalid/a.zip", b"two", lock)


def test_download_refuses_non_https() -> None:
    with pytest.raises(fetch_rules.RulesError, match="non-HTTPS"):
        fetch_rules.download("file:///etc/passwd")

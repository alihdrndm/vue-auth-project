"""Download the pinned KoSIT releases and vendor only the files Eingang needs.

Run as `uv run poe fetch-rules`. The first run records each download's SHA-256 in
backend/vendor/rules.lock.json (committed); later runs refuse any file whose hash differs.
The extracted files are committed too, so tests and Docker builds never need the network.
"""

import argparse
import hashlib
import io
import json
import shutil
import sys
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

BACKEND_DIR = Path(__file__).resolve().parents[1]
VENDOR_DIR = BACKEND_DIR / "vendor"
LOCK_FILE = VENDOR_DIR / "rules.lock.json"
TAG = "v2026-01-31"
GITHUB = "https://github.com/itplr-kosit"
RAW = "https://raw.githubusercontent.com/itplr-kosit"
TIMEOUT_SECONDS = 120


def _config_files(name: str) -> bool:
    return (
        name in ("README.md", "scenarios.xml")
        or name.startswith("resources/cii/16b/")
        or name.startswith("resources/xrechnung/")
        or name.startswith("resources/ubl/2.1/xsl/")
        or name.startswith("resources/ubl/2.1/xsd/common/")
        or name
        in (
            "resources/ubl/2.1/xsd/maindoc/UBL-Invoice-2.1.xsd",
            "resources/ubl/2.1/xsd/maindoc/UBL-CreditNote-2.1.xsd",
        )
    )


def _visualization_files(name: str) -> bool:
    # The HTML transformation only; the PDF (XSL-FO) part and the browser scripts are not used.
    if name in ("README.md", "CHANGELOG.md"):
        return True
    if not name.startswith("xsl/") or name.startswith("xsl/xr-pdf"):
        return False
    return name.endswith((".xsl", ".css")) or name.startswith("xsl/l10n/")


def _testsuite_files(name: str) -> bool:
    return name in ("README.md", "CHANGELOG.md", "test-overview.md") or name.startswith(
        "instances/"
    )


@dataclass(frozen=True)
class Release:
    repository: str
    asset: str
    target: str  # folder under backend/vendor/
    keep: Callable[[str], bool]
    extra_files: tuple[str, ...]  # fetched from the repository at the tag (licences)


RELEASES = (
    Release(
        "validator-configuration-xrechnung",
        "xrechnung-3.0.2-validator-configuration-2026-01-31.zip",
        "xrechnung-config",
        _config_files,
        ("LICENSE", "NOTICE"),
    ),
    Release(
        "xrechnung-visualization",
        "xrechnung-3.0.2-visualization-2026-01-31.zip",
        "xrechnung-visualization",
        _visualization_files,
        ("LICENSE",),
    ),
    Release(
        "xrechnung-testsuite",
        "xrechnung-3.0.2-testsuite-2026-01-31.zip",
        "xrechnung-testsuite",
        _testsuite_files,
        ("LICENSE",),
    ),
)


class RulesError(Exception):
    """A download did not match the lock file, or a zip entry was unsafe."""


def download(url: str) -> bytes:
    if not url.startswith("https://"):
        raise RulesError(f"refusing a non-HTTPS URL: {url}")
    # The scheme is checked above, so urlopen cannot read local files.
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
        data: bytes = response.read()
    return data


def verify(url: str, data: bytes, lock: dict[str, str]) -> None:
    digest = hashlib.sha256(data).hexdigest()
    expected = lock.setdefault(url, digest)
    if expected != digest:
        raise RulesError(f"SHA-256 mismatch for {url}: expected {expected}, got {digest}")


def _top_folder(names: list[str]) -> str:
    # Some release zips wrap everything in one folder; strip it if every entry shares it.
    first = names[0].split("/", 1)[0] + "/"
    return first if all(name.startswith(first) for name in names) else ""


def extract(data: bytes, keep: Callable[[str], bool], target: Path) -> list[str]:
    written = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = [info.filename for info in archive.infolist()]
        prefix = _top_folder(names)
        for info in archive.infolist():
            if info.is_dir():
                continue
            relative = info.filename[len(prefix) :]
            path = PurePosixPath(relative)
            if path.is_absolute() or ".." in path.parts or "\\" in relative:
                raise RulesError(f"unsafe entry in archive: {info.filename}")
            if not keep(relative):
                continue
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(info))
            written.append(relative)
    return written


def fetch(release: Release, lock: dict[str, str], vendor_dir: Path) -> int:
    target = vendor_dir / release.target
    zip_url = f"{GITHUB}/{release.repository}/releases/download/{TAG}/{release.asset}"
    data = download(zip_url)
    verify(zip_url, data, lock)
    if target.exists():
        shutil.rmtree(target)
    written = extract(data, release.keep, target)
    for name in release.extra_files:
        url = f"{RAW}/{release.repository}/{TAG}/{name}"
        content = download(url)
        verify(url, content, lock)
        (target / name).write_bytes(content)
    return len(written) + len(release.extra_files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    lock: dict[str, str] = (
        json.loads(LOCK_FILE.read_text(encoding="utf-8")) if LOCK_FILE.exists() else {}
    )
    try:
        for release in RELEASES:
            count = fetch(release, lock, VENDOR_DIR)
            print(f"{release.repository} {TAG}: {count} files in vendor/{release.target}/")
    except RulesError as error:
        print(f"fetch-rules: {error}", file=sys.stderr)
        return 1
    LOCK_FILE.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

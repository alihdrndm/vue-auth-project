"""Download the pinned ZUGFeRD corpus into data/corpus/ (git-ignored).

The archive of one fixed commit is downloaded, checked against a known SHA-256 and extracted
without its top-level folder. `data/corpus/.commit` records the commit, so a second run does
nothing. Pass --force to download and extract again.

Run from backend/ as `uv run python tools/fetch_corpus.py`.
"""

import argparse
import hashlib
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

CORPUS_COMMIT = "d891458e9822e34271a5438497bf924e89955979"
ARCHIVE_URL = f"https://codeload.github.com/ZUGFeRD/corpus/zip/{CORPUS_COMMIT}"
ARCHIVE_SHA256 = "d5359c24404c9b076b631ddce01f2f96ea717683b0240e464c90129ef830c833"

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = REPO_ROOT / "data" / "corpus"
COMMIT_MARKER = ".commit"
DOWNLOAD_TIMEOUT_SECONDS = 120
CHUNK_SIZE = 1024 * 1024


class CorpusError(Exception):
    """The archive could not be verified or safely extracted."""


def download(url: str, destination: Path) -> None:
    """Stream `url` into `destination`."""
    if not url.startswith("https://"):
        raise CorpusError(f"refusing to download from a non-HTTPS URL: {url}")
    # The scheme is checked above, so urlopen cannot read local files.
    with (
        urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response,  # noqa: S310
        destination.open("wb") as out,
    ):
        shutil.copyfileobj(response, out, CHUNK_SIZE)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_present(target: Path, commit: str = CORPUS_COMMIT) -> bool:
    marker = target / COMMIT_MARKER
    return marker.is_file() and marker.read_text(encoding="utf-8").strip() == commit


def _relative_parts(name: str) -> tuple[str, ...]:
    """Split a zip entry name into safe path parts, or raise CorpusError."""
    normalised = name.replace("\\", "/")
    if PurePosixPath(normalised).is_absolute() or PureWindowsPath(normalised).drive:
        raise CorpusError(f"zip entry has an absolute path: {name!r}")
    parts = tuple(part for part in normalised.split("/") if part not in ("", "."))
    if ".." in parts:
        raise CorpusError(f"zip entry escapes the target directory: {name!r}")
    return parts


def _plan(archive: zipfile.ZipFile, target: Path) -> list[tuple[zipfile.ZipInfo, Path]]:
    """Map every file entry to its destination below `target`, stripping the top folder."""
    root = target.resolve()
    entries: list[tuple[zipfile.ZipInfo, tuple[str, ...]]] = []
    top_folders: set[str] = set()
    for info in archive.infolist():
        parts = _relative_parts(info.filename)
        if not parts:
            continue
        top_folders.add(parts[0])
        entries.append((info, parts))
    if len(top_folders) != 1:
        raise CorpusError("archive must contain exactly one top-level folder")
    plan: list[tuple[zipfile.ZipInfo, Path]] = []
    for info, parts in entries:
        if info.is_dir() or len(parts) < 2:
            continue
        destination = root.joinpath(*parts[1:]).resolve()
        if not destination.is_relative_to(root):
            raise CorpusError(f"zip entry escapes the target directory: {info.filename!r}")
        plan.append((info, destination))
    return plan


def extract(archive_path: Path, target: Path) -> int:
    """Replace `target` with the archive's files (top folder stripped). Returns the file count.

    Every entry is checked before anything is written, so a rejected archive leaves `target`
    untouched.
    """
    staging = target.with_name(target.name + ".partial")
    if staging.exists():
        shutil.rmtree(staging)
    with zipfile.ZipFile(archive_path) as archive:
        plan = _plan(archive, staging)
        staging.mkdir(parents=True)
        for info, destination in plan:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, destination.open("wb") as out:
                shutil.copyfileobj(source, out, CHUNK_SIZE)
    if target.exists():
        shutil.rmtree(target)
    staging.rename(target)
    return len(plan)


def fetch(
    target: Path,
    *,
    force: bool = False,
    url: str = ARCHIVE_URL,
    expected_sha256: str = ARCHIVE_SHA256,
    commit: str = CORPUS_COMMIT,
) -> int | None:
    """Download, verify and extract the corpus. Returns the file count, or None if present."""
    if not force and is_present(target, commit):
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        archive_path = Path(directory) / "corpus.zip"
        download(url, archive_path)
        actual = sha256_of(archive_path)
        if actual != expected_sha256:
            raise CorpusError(f"SHA-256 mismatch: expected {expected_sha256}, got {actual}")
        count = extract(archive_path, target)
    (target / COMMIT_MARKER).write_text(commit + "\n", encoding="utf-8", newline="\n")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="download and extract again")
    args = parser.parse_args()
    try:
        count = fetch(DEFAULT_TARGET, force=args.force)
    except (CorpusError, OSError, zipfile.BadZipFile) as error:
        print(f"fetch_corpus: {error}", file=sys.stderr)
        return 1
    if count is None:
        print("corpus already present")
    else:
        print(f"Extracted {count} files at commit {CORPUS_COMMIT} into {DEFAULT_TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

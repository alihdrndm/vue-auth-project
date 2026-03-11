"""fetch_corpus: download, verification and safe extraction, all without network."""

import hashlib
import io
import zipfile
from collections.abc import Callable
from pathlib import Path

import fetch_corpus
import pytest

TOP = "corpus-abc123/"
COMMIT = "abc123"


def make_zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def sample_zip() -> bytes:
    return make_zip(
        {
            TOP: b"",
            f"{TOP}LICENSE": b"license",
            f"{TOP}XML-Rechnung/": b"",
            f"{TOP}XML-Rechnung/UBL/XRECHNUNG_Einfach.ubl.xml": b"<Invoice/>",
        }
    )


def fake_download(payload: bytes, calls: list[str]) -> Callable[[str, Path], None]:
    def download(url: str, destination: Path) -> None:
        calls.append(url)
        destination.write_bytes(payload)

    return download


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    recorded: list[str] = []
    monkeypatch.setattr(fetch_corpus, "download", fake_download(sample_zip(), recorded))
    return recorded


def test_extracts_and_strips_top_folder(tmp_path: Path, calls: list[str]) -> None:
    target = tmp_path / "data" / "corpus"

    count = fetch_corpus.fetch(target, expected_sha256=sha(sample_zip()), commit=COMMIT)

    assert count == 2
    assert (target / "LICENSE").read_bytes() == b"license"
    xml = target / "XML-Rechnung" / "UBL" / "XRECHNUNG_Einfach.ubl.xml"
    assert xml.read_bytes() == b"<Invoice/>"
    assert not (target / "corpus-abc123").exists()
    assert (target / ".commit").read_text(encoding="utf-8") == f"{COMMIT}\n"
    assert not (tmp_path / "data" / "corpus.partial").exists()
    assert calls == [fetch_corpus.ARCHIVE_URL]


def test_second_run_is_a_no_op(tmp_path: Path, calls: list[str]) -> None:
    target = tmp_path / "corpus"
    fetch_corpus.fetch(target, expected_sha256=sha(sample_zip()), commit=COMMIT)

    again = fetch_corpus.fetch(target, expected_sha256=sha(sample_zip()), commit=COMMIT)

    assert again is None
    assert len(calls) == 1


def test_force_downloads_again_and_replaces_files(tmp_path: Path, calls: list[str]) -> None:
    target = tmp_path / "corpus"
    fetch_corpus.fetch(target, expected_sha256=sha(sample_zip()), commit=COMMIT)
    (target / "stale.txt").write_text("old", encoding="utf-8")

    count = fetch_corpus.fetch(target, force=True, expected_sha256=sha(sample_zip()), commit=COMMIT)

    assert count == 2
    assert len(calls) == 2
    assert not (target / "stale.txt").exists()


def test_different_commit_marker_triggers_download(tmp_path: Path, calls: list[str]) -> None:
    target = tmp_path / "corpus"
    target.mkdir()
    (target / ".commit").write_text("other\n", encoding="utf-8")

    count = fetch_corpus.fetch(target, expected_sha256=sha(sample_zip()), commit=COMMIT)

    assert count == 2
    assert fetch_corpus.is_present(target, COMMIT)


def test_sha_mismatch_fails_and_writes_nothing(tmp_path: Path, calls: list[str]) -> None:
    target = tmp_path / "corpus"

    with pytest.raises(fetch_corpus.CorpusError, match="SHA-256 mismatch"):
        fetch_corpus.fetch(target, expected_sha256="0" * 64, commit=COMMIT)

    assert not target.exists()


@pytest.mark.parametrize(
    "evil_name",
    [f"{TOP}../evil", "../evil", f"{TOP}a/../../evil", "/evil", "C:/evil", rf"{TOP}..\evil"],
)
def test_rejects_entries_escaping_the_target(tmp_path: Path, evil_name: str) -> None:
    archive = tmp_path / "evil.zip"
    archive.write_bytes(make_zip({f"{TOP}ok.txt": b"ok", evil_name: b"evil"}))
    target = tmp_path / "out" / "corpus"

    with pytest.raises(fetch_corpus.CorpusError):
        fetch_corpus.extract(archive, target)

    assert not (tmp_path / "evil").exists()
    assert not (tmp_path / "out" / "evil").exists()
    assert not target.exists()


def test_rejects_archive_without_single_top_folder(tmp_path: Path) -> None:
    archive = tmp_path / "flat.zip"
    archive.write_bytes(make_zip({"a/one.txt": b"1", "b/two.txt": b"2"}))

    with pytest.raises(fetch_corpus.CorpusError, match="top-level folder"):
        fetch_corpus.extract(archive, tmp_path / "corpus")


def test_download_refuses_non_https(tmp_path: Path) -> None:
    with pytest.raises(fetch_corpus.CorpusError, match="non-HTTPS"):
        fetch_corpus.download("file:///etc/passwd", tmp_path / "x")


def test_main_reports_present_corpus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "corpus"
    target.mkdir()
    (target / ".commit").write_text(f"{fetch_corpus.CORPUS_COMMIT}\n", encoding="utf-8")
    monkeypatch.setattr(fetch_corpus, "DEFAULT_TARGET", target)
    monkeypatch.setattr("sys.argv", ["fetch_corpus.py"])

    assert fetch_corpus.main() == 0
    assert capsys.readouterr().out.strip() == "corpus already present"


def test_main_returns_1_on_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(fetch_corpus, "DEFAULT_TARGET", tmp_path / "corpus")
    monkeypatch.setattr(fetch_corpus, "download", fake_download(b"not a zip", []))
    monkeypatch.setattr("sys.argv", ["fetch_corpus.py"])

    assert fetch_corpus.main() == 1
    assert "SHA-256 mismatch" in capsys.readouterr().err

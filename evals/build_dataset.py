"""Build the extraction dataset from the pinned ZUGFeRD corpus (HANDOFF "Extraction accuracy").

A document is every PDF under a folder named `correct` or under `XML-Rechnung/FX/` whose
embedded XML is CII, parses to a `CanonicalInvoice`, and has a text layer (rule D3). A PDF
whose bytes equal an earlier one's is counted once. The ground truth is the parsed XML; the
input is the PDF's visible text, made exactly as the app makes it for the LLM
(`einvoice.pdf.extract_text` and `invoices.extraction.prepare_text`: six pages, cut at
12,000 characters).

Writes `evals/data/manifest.json` (committed; the same bytes on every run) and, per document,
the input text and the truth to `evals/data/cache/dataset/` (git-ignored), which the runners
read with `load_documents`. Prints the count and every skip reason.

Run from backend/ as `uv run poe eval-dataset` (the corpus comes from `uv run poe fetch-corpus`).
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, ValidationError

from einvoice import detect, pdf
from einvoice.errors import EinvoiceError, UnsafeXmlError
from einvoice.model import CanonicalInvoice
from einvoice.parse_cii import parse_cii
from evals import CORPUS_DIR, DATA_DIR, setup_django

DATASET_NAME = "zugferd-corpus-hybrid-cii"
COMMIT_MARKER = ".commit"
FX_FOLDER = ("XML-Rechnung", "FX")
CORRECT_FOLDER = "correct"

# Skip reasons, as printed and written to the manifest.
NOT_READABLE = "PDF cannot be read"
UNSAFE_XML = "embedded XML refused (DOCTYPE)"
NO_XML = "no embedded XML"
NOT_CII = "embedded XML is not CII"
NOT_PARSED = "embedded XML does not parse to a CanonicalInvoice"
NO_TEXT = "no text layer"
DUPLICATE = "same bytes as an earlier document"

# --- language guess -------------------------------------------------------------------------

# Words that appear on nearly every invoice of one language and rarely in the others. The
# guess is the language with the most occurrences; no hits at all gives "unknown", and a tie
# goes to the language listed first. Good enough to describe the dataset, not to route on.
LANGUAGE_WORDS: dict[str, frozenset[str]] = {
    "de": frozenset(
        {
            "rechnung", "rechnungsnummer", "rechnungsdatum", "datum", "betrag", "summe",
            "gesamt", "gesamtbetrag", "netto", "brutto", "mwst", "ust", "umsatzsteuer",
            "steuer", "zahlbar", "lieferung", "menge", "preis", "bankverbindung", "und", "der",
        }
    ),
    "en": frozenset(
        {
            "invoice", "date", "amount", "total", "due", "payment", "tax", "vat", "quantity",
            "price", "bank", "account", "description", "and", "the",
        }
    ),
    "fr": frozenset(
        {
            "facture", "montant", "tva", "échéance", "paiement", "prix", "quantité",
            "désignation", "règlement", "ht", "ttc", "et", "le", "la", "les", "des",
        }
    ),
}  # fmt: skip
_WORD = re.compile(r"[^\W\d_]+")


def guess_language(text: str) -> str:
    """The language, "de", "en", "fr" or "unknown", from keyword counts (LANGUAGE_WORDS)."""
    counts = Counter(_WORD.findall(text.lower()))
    hits = {
        language: sum(counts[word] for word in words) for language, words in LANGUAGE_WORDS.items()
    }
    best = max(hits, key=lambda language: hits[language])  # first listed wins a tie
    return best if hits[best] > 0 else "unknown"


# --- manifest -------------------------------------------------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ManifestDocument(_Strict):
    id: str
    path: str  # relative to data/corpus, forward slashes
    sha256: str
    language: str
    profile: str
    text_chars: int  # characters of the extraction input after truncation
    text_truncated: bool


class Skipped(_Strict):
    path: str
    reason: str


class Manifest(_Strict):
    name: str
    corpus_commit: str
    documents: int
    selection: str
    entries: list[ManifestDocument]
    skipped: list[Skipped]
    skipped_counts: dict[str, int]


class CachedDocument(_Strict):
    """What the cache holds per document next to its `<id>.txt` input text."""

    sha256: str
    truth: CanonicalInvoice


@dataclass(frozen=True)
class DatasetDocument:
    """One document as the runners use it."""

    id: str
    path: str
    language: str
    profile: str
    text: str
    truth: CanonicalInvoice


class DatasetError(Exception):
    """The corpus or the cache is missing or out of date."""


SELECTION = (
    "PDFs under a folder named `correct` or under XML-Rechnung/FX/ whose embedded XML is CII, "
    "parses to a CanonicalInvoice and has a text layer; identical files counted once"
)


def document_id(path: str) -> str:
    """A file-name-safe ID from the corpus path, e.g. `ZUGFeRDv2__correct__...__EN16931_Einfach`."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", path.removesuffix(".pdf").replace("/", "__"))


def cache_dir(data_dir: Path) -> Path:
    """Where the per-document inputs and truths are cached; other scripts cache next to it."""
    return data_dir / "cache" / "dataset"


def corpus_commit(corpus: Path) -> str:
    marker = corpus / COMMIT_MARKER
    if not marker.is_file():
        raise DatasetError(f"No corpus at {corpus}. Run: cd backend && uv run poe fetch-corpus")
    return marker.read_text(encoding="utf-8").strip()


def candidates(corpus: Path) -> list[str]:
    """Corpus-relative paths (forward slashes) of the PDFs the dataset considers, sorted."""
    found = []
    for path in corpus.rglob("*"):
        if not path.is_file() or path.suffix.lower() != ".pdf":
            continue
        relative = PurePosixPath(path.relative_to(corpus).as_posix())
        folders = relative.parts[:-1]
        if CORRECT_FOLDER in folders or folders[: len(FX_FOLDER)] == FX_FOLDER:
            found.append(str(relative))
    return sorted(found)


@dataclass(frozen=True)
class _Accepted:
    entry: ManifestDocument
    text: str
    truth: CanonicalInvoice


def _examine(path: str, data: bytes) -> _Accepted | str:
    """The accepted document, or the reason it is skipped."""
    from invoices.extraction import prepare_text  # needs Django (setup_django)

    try:
        detection = detect.detect(data, path)
    except UnsafeXmlError:
        return UNSAFE_XML
    except EinvoiceError:
        return NOT_READABLE
    if detection.kind in (detect.Kind.PDF_TEXT, detect.Kind.PDF_NO_TEXT):
        return NO_XML
    if detection.kind is not detect.Kind.HYBRID_PDF or detection.xml is None:
        return NOT_CII
    try:
        truth = parse_cii(detection.xml)
    except (EinvoiceError, ValidationError):
        return NOT_PARSED
    if not detection.has_text_layer:
        return NO_TEXT
    text, truncated = prepare_text(pdf.extract_text(data).pages)
    entry = ManifestDocument(
        id=document_id(path),
        path=path,
        sha256=hashlib.sha256(data).hexdigest(),
        language=guess_language(text),
        profile=(detection.profile or detect.Profile.UNKNOWN).value,
        text_chars=len(text),
        text_truncated=truncated,
    )
    return _Accepted(entry=entry, text=text, truth=truth)


def _write_text(path: Path, text: str) -> None:
    # Same bytes on every OS: LF line endings.
    path.write_text(text, encoding="utf-8", newline="\n")


def build(corpus: Path, data_dir: Path) -> Manifest:
    """Examine the corpus, write the manifest and the cache, and return the manifest."""
    commit = corpus_commit(corpus)
    cache = cache_dir(data_dir)
    cache.mkdir(parents=True, exist_ok=True)
    for stale in [*cache.glob("*.txt"), *cache.glob("*.json")]:
        stale.unlink()
    entries: list[ManifestDocument] = []
    skipped: list[Skipped] = []
    first_with_hash: dict[str, str] = {}
    for path in candidates(corpus):
        data = (corpus / path).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest in first_with_hash:
            skipped.append(Skipped(path=path, reason=DUPLICATE))
            continue
        first_with_hash[digest] = path
        result = _examine(path, data)
        if isinstance(result, str):
            skipped.append(Skipped(path=path, reason=result))
            continue
        entries.append(result.entry)
        _write_text(cache / f"{result.entry.id}.txt", result.text)
        cached = CachedDocument(sha256=result.entry.sha256, truth=result.truth)
        _write_text(cache / f"{result.entry.id}.json", cached.model_dump_json(indent=2) + "\n")
    ids = [entry.id for entry in entries]
    if len(ids) != len(set(ids)):
        raise DatasetError("two corpus paths map to the same document ID")
    manifest = Manifest(
        name=DATASET_NAME,
        corpus_commit=commit,
        documents=len(entries),
        selection=SELECTION,
        entries=entries,
        skipped=skipped,
        skipped_counts=dict(sorted(Counter(item.reason for item in skipped).items())),
    )
    text = json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
    _write_text(data_dir / "manifest.json", text)
    return manifest


# --- reading the dataset (for the runners) -------------------------------------------------


def load_manifest(data_dir: Path = DATA_DIR) -> Manifest:
    path = data_dir / "manifest.json"
    if not path.is_file():
        raise DatasetError(f"No manifest at {path}. Run: cd backend && uv run poe eval-dataset")
    return Manifest.model_validate_json(path.read_bytes())


def load_documents(data_dir: Path = DATA_DIR) -> Iterator[DatasetDocument]:
    """The documents of the manifest, in manifest order, from the cache."""
    cache = cache_dir(data_dir)
    for entry in load_manifest(data_dir).entries:
        try:
            text = (cache / f"{entry.id}.txt").read_text(encoding="utf-8")
            cached = CachedDocument.model_validate_json((cache / f"{entry.id}.json").read_bytes())
        except FileNotFoundError:
            raise DatasetError(
                f"{entry.id} is not cached. Run: cd backend && uv run poe eval-dataset"
            ) from None
        if cached.sha256 != entry.sha256:
            raise DatasetError(f"The cache of {entry.id} is stale. Run the dataset build again.")
        yield DatasetDocument(
            id=entry.id,
            path=entry.path,
            language=entry.language,
            profile=entry.profile,
            text=text,
            truth=cached.truth,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--corpus", type=Path, default=CORPUS_DIR)
    parser.add_argument("--out", type=Path, default=DATA_DIR, help="the evals/data directory")
    args = parser.parse_args(argv)
    setup_django()
    try:
        manifest = build(args.corpus, args.out)
    except DatasetError as error:
        print(error, file=sys.stderr)
        return 1
    languages = Counter(entry.language for entry in manifest.entries)
    profiles = Counter(entry.profile for entry in manifest.entries)
    print(f"{manifest.documents} documents (corpus {manifest.corpus_commit[:12]})")
    print("  languages: " + ", ".join(f"{k} {v}" for k, v in sorted(languages.items())))
    print("  profiles: " + ", ".join(f"{k} {v}" for k, v in sorted(profiles.items())))
    truncated = sum(entry.text_truncated for entry in manifest.entries)
    print(f"  input text cut at the limit: {truncated}")
    print(f"{len(manifest.skipped)} skipped:")
    for reason, count in manifest.skipped_counts.items():
        print(f"  {count:4d}  {reason}")
    print(f"Wrote {args.out / 'manifest.json'} and the cache in {cache_dir(args.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

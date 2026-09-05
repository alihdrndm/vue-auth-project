"""Prompt files (HANDOFF "Prompts"): `backend/prompts/<name>.v<N>.md`, loaded by name and version.

A changed prompt is a new version file; old files stay, because every ledger row and saved
result names the version it came from.
"""

from dataclasses import dataclass
from functools import cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


@dataclass(frozen=True)
class Prompt:
    name: str
    version: int
    text: str

    @property
    def label(self) -> str:
        """What the ledger stores as `prompt_version`, e.g. `extract_invoice.v1`."""
        return f"{self.name}.v{self.version}"


@cache
def load(name: str, version: int) -> Prompt:
    path = PROMPTS_DIR / f"{name}.v{version}.md"
    return Prompt(name=name, version=version, text=path.read_text(encoding="utf-8").strip())


def fenced(tag: str, text: str) -> str:
    """Untrusted text inside a fence; a closing tag inside the text cannot end the fence."""
    safe = text.replace(f"</{tag}>", f"</ {tag}>")
    return f"<{tag}>\n{safe}\n</{tag}>"

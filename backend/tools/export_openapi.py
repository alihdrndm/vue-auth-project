"""Write the OpenAPI schema (default backend/openapi.json), or with --check fail if it is stale.

Run as `uv run poe openapi` / `uv run poe openapi-check`.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = BACKEND_DIR / "openapi.json"


def generate(target: Path) -> None:
    sys.path.insert(0, str(BACKEND_DIR / "src"))
    # The process entry point names its settings module; this is not configuration.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eingang.settings")
    import django
    from django.core.management import call_command

    django.setup()
    call_command("spectacular", "--format", "openapi-json", "--validate", "--file", str(target))
    # Same bytes on every OS: LF line endings and a final newline (.editorconfig).
    text = target.read_text(encoding="utf-8").rstrip("\n") + "\n"
    target.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if openapi.json is stale")
    parser.add_argument("--file", type=Path, default=SCHEMA_PATH, help="where to write the schema")
    args = parser.parse_args()
    if not args.check:
        generate(args.file)
        print(f"Wrote {args.file}")
        return 0
    with tempfile.TemporaryDirectory() as directory:
        fresh = Path(directory) / "openapi.json"
        generate(fresh)
        current = SCHEMA_PATH.read_text(encoding="utf-8") if SCHEMA_PATH.exists() else ""
        if fresh.read_text(encoding="utf-8") != current:
            print("backend/openapi.json is stale. Run: pnpm gen:api", file=sys.stderr)
            return 1
    print("backend/openapi.json is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())

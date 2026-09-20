"""Evaluation of extraction accuracy and validation parity (HANDOFF "Evaluation").

The scripts are modules of this package. They run from `backend/` with the backend's
environment and `.env`, through poe tasks in `backend/pyproject.toml` that set
`PYTHONPATH=..` and run `python -m evals.<script>` (for example `uv run poe eval-dataset`).
Importing the package puts `backend/src` on the import path, so the scripts use the
application's own code (`einvoice`, `invoices`, `eingang`); code in `backend/src` never
imports from here.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = REPO_ROOT / "backend" / "src"
EVALS_DIR = REPO_ROOT / "evals"
CORPUS_DIR = REPO_ROOT / "data" / "corpus"
DATA_DIR = EVALS_DIR / "data"
REPORTS_DIR = EVALS_DIR / "reports"
LATEST_PATH = EVALS_DIR / "latest.json"

if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))


def setup_django() -> None:
    """Load the Django settings, for scripts that use application code tied to Django."""
    # The process entry point names its settings module; this is not configuration.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eingang.settings")
    import django

    django.setup()

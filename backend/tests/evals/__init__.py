"""Tests for the evaluation scripts in evals/ (a package at the repository root).

The repository root is put on the import path here, so the tests import the scripts as
`evals.<module>`, the way `python -m evals.<module>` runs them.
"""

import sys
from pathlib import Path

REPO_ROOT = str(Path(__file__).resolve().parents[3])
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

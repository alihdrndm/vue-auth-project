"""Tests for the scripts in backend/tools/.

The scripts are run as files, not imported as a package, so their directory is put on the
import path here; the tests import each script by its module name (`import fetch_corpus`).
"""

import sys
from pathlib import Path

TOOLS_DIR = str(Path(__file__).resolve().parents[2] / "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

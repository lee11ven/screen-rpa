from __future__ import annotations

import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp())
_db = _tmp / "pytest_rpa.db"
os.environ["DATABASE_PATH"] = str(_db)

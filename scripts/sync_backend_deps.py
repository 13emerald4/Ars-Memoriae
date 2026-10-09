"""Install backend dependencies when backend/pyproject.toml has changed.

The launchers auto-update with `git pull`, so a dependency added upstream must
reach venvs that were created long ago. Run this with the venv's own Python:

    backend/.venv/bin/python scripts/sync_backend_deps.py

It records a hash of pyproject.toml inside the venv and only runs pip when the
hash differs, so an unchanged checkout starts as fast as before.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
PYPROJECT = BACKEND / "pyproject.toml"
STAMP = Path(sys.prefix) / ".deps-stamp"


def main() -> int:
    digest = hashlib.sha256(PYPROJECT.read_bytes()).hexdigest()
    try:
        if STAMP.read_text().strip() == digest:
            print("  Backend dependencies are up to date.")
            return 0
    except OSError:
        pass

    print("  Installing backend dependencies (first run or after an update)...", flush=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,  # an outdated pip is fine; the real install below decides
    )
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(BACKEND)], check=False
    )
    if result.returncode != 0:
        return result.returncode
    STAMP.write_text(digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())

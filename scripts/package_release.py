"""Release Packaging Utility for Ars Memoria.

Builds the frontend for production, collects all required runtime assets,
and generates a clean, lightweight zip archive ready to distribute to friends
or upload to GitHub Releases.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def build_frontend() -> bool:
    print("[1/3] Building frontend production bundle...")
    frontend_dir = REPO_ROOT / "frontend"
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"

    try:
        subprocess.run([npm_cmd, "run", "build"], cwd=frontend_dir, check=True)
        print("  [OK] Frontend compiled successfully into frontend/dist")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  [WARN] Could not run npm run build ({e}). Checking if frontend/dist already exists...")
        if (frontend_dir / "dist" / "index.html").is_file():
            print("  [OK] Existing frontend/dist bundle found. Proceeding with existing build.")
            return True
        else:
            print("  [ERROR] frontend/dist not found and build failed.")
            return False


def create_release_zip() -> Path:
    print("[2/3] Preparing release archive...")
    output_dir = REPO_ROOT / "release"
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / "Ars-Memoria-Release.zip"

    # Exclude patterns
    exclude_dirs = {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "release",
        "tmp",
    }
    exclude_files = {
        ".env",
        ".env.local",
        "dev.db",
        "dev.db-shm",
        "dev.db-wal",
        "dev.db-journal",
        "memorization.db",
        ".DS_Store",
    }

    print(f"[3/3] Packaging files into: {zip_path.name}...")
    file_count = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(REPO_ROOT):
            root_path = Path(root)
            rel_root = root_path.relative_to(REPO_ROOT)

            # Skip excluded directories
            dirs[:] = [
                d for d in dirs
                if d not in exclude_dirs
                and not any(ex in rel_root.parts for ex in exclude_dirs)
            ]

            # Don't include raw frontend dev src if frontend/dist is included (reduces size drastically)
            if "frontend" in rel_root.parts and rel_root.parts[0] == "frontend":
                # Only include package.json and dist/
                if rel_root.name not in ("dist", "assets") and "dist" not in rel_root.parts:
                    continue

            for file in files:
                if file in exclude_files or file.endswith((".pyc", ".pyo")):
                    continue

                abs_file = root_path / file
                rel_file = abs_file.relative_to(REPO_ROOT)

                # Store inside top-level Ars-Memoria/ directory inside zip
                archive_name = Path("Ars-Memoria") / rel_file
                zf.write(abs_file, str(archive_name))
                file_count += 1

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  [OK] Packaged {file_count} files ({size_mb:.2f} MB)")
    print()
    print("===================================================================")
    print(f"  [SUCCESS] Release archive ready: {zip_path}")
    print("===================================================================")
    return zip_path


def main() -> None:
    if not build_frontend():
        sys.exit(1)
    create_release_zip()


if __name__ == "__main__":
    main()

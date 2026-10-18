"""Check for remote updates and prompt the user before pulling.

Used by start_windows.bat and start_mac.sh on startup.
If an update is found on the upstream Git branch, it shows the new commit
summaries and asks the user whether they want to update now.

Exit codes:
  0  - Up to date, update declined, offline, or standalone release package
  10 - Successfully pulled an update (signals the batch/shell launcher to reload)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def get_upstream_branch() -> str:
    """Detects upstream tracking branch, defaulting to origin/main."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "@{u}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return "origin/main"


def check_and_prompt_update() -> int:
    git_dir = REPO_ROOT / ".git"
    if not git_dir.exists():
        print("  Running from standalone release package.")
        return 0

    # 1. Check if git is available
    try:
        git_check = subprocess.run(
            ["git", "--version"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if git_check.returncode != 0:
            print("  Git not available. Continuing with current version.")
            return 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("  Git not available. Continuing with current version.")
        return 0

    # 2. Silently fetch from remote with a short timeout (never hang if offline)
    try:
        fetch_proc = subprocess.run(
            ["git", "fetch", "-q"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if fetch_proc.returncode != 0:
            print("  Note: Could not reach GitHub (offline). Continuing with current version.")
            return 0
    except subprocess.TimeoutExpired:
        print("  Note: Update check timed out (offline). Continuing with current version.")
        return 0
    except Exception as exc:
        print(f"  Note: Update check skipped ({exc}). Continuing with current version.")
        return 0

    upstream = get_upstream_branch()

    # 3. Check number of commits behind
    try:
        rev_proc = subprocess.run(
            ["git", "rev-list", f"HEAD..{upstream}", "--count"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if rev_proc.returncode != 0:
            print("  Repository is up to date.")
            return 0
        behind_count = int(rev_proc.stdout.strip() or "0")
    except Exception:
        print("  Repository is up to date.")
        return 0

    if behind_count <= 0:
        print("  Repository is up to date.")
        return 0

    # 4. An update is available! Retrieve recent commit summaries
    commits: list[str] = []
    try:
        log_proc = subprocess.run(
            ["git", "log", f"HEAD..{upstream}", "--oneline", "-n", "5"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if log_proc.returncode == 0:
            commits = [line.strip() for line in log_proc.stdout.splitlines() if line.strip()]
    except Exception:
        pass

    print()
    print("=" * 67)
    print(f"  [UPDATE AVAILABLE] A new version of Ars Memoriae has been pushed!")
    print(f"  Remote has {behind_count} new update{'s' if behind_count != 1 else ''}.")
    if commits:
        print("\n  Recent changes:")
        for c in commits:
            print(f"    * {c}")
    print("=" * 67)

    # 5. Non-interactive check (e.g. background tasks or CI)
    if not sys.stdin.isatty():
        print("  Non-interactive session detected. Continuing with current version.")
        return 0

    # 6. Prompt the user
    try:
        choice = input("  Would you like to update to the latest version now? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  Update skipped. Continuing with current version.")
        return 0

    if choice in ("", "y", "yes"):
        print("  Pulling latest updates from GitHub...")
        pull_proc = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if pull_proc.returncode == 0:
            print("  [OK] Successfully updated to the latest version!")
            return 10  # Signal launcher that an update was pulled
        else:
            print("  [WARN] Automatic update could not fast-forward.")
            print(f"         {pull_proc.stderr.strip() or pull_proc.stdout.strip()}")
            print("  Continuing with current local version.")
            return 0
    else:
        print("  Update postponed. Continuing with current version.")
        return 0


def main() -> int:
    try:
        return check_and_prompt_update()
    except Exception as exc:
        print(f"  Note: Update check encountered an error ({exc}). Continuing...")
        return 0


if __name__ == "__main__":
    sys.exit(main())

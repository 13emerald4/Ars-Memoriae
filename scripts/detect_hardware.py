"""CLI utility to inspect system hardware and recommend the optimal local AI model size.

Used by start_windows.bat, start_mac.sh, and users to determine which Qwen 2.5 Coder
size (1.5B, 3B, or 7B) should be pulled and run locally.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Safe terminal encoding on Windows legacy code pages
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add backend directory to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.hardware_service import detect_hardware


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect hardware and recommend local AI model size.")
    parser.add_argument("--model-only", "-m", action="store_true", help="Print only the recommended model ID (e.g. qwen2.5-coder:3b)")
    parser.add_argument("--size-only", "-s", action="store_true", help="Print only the size tag (e.g. 3b)")
    parser.add_argument("--json", "-j", action="store_true", help="Print output as JSON")
    args = parser.parse_args()

    profile = detect_hardware()

    if args.model_only:
        print(profile.recommended_model)
        return

    if args.size_only:
        print(profile.recommended_size)
        return

    if args.json:
        print(json.dumps(profile.to_dict(), indent=2))
        return

    # Formatted terminal output
    print("")
    print("===================================================================")
    print("   [Hardware Inspection & Model Recommendation]")
    print("===================================================================")
    print(f"  Operating System : {profile.os_name} ({profile.architecture})")
    print(f"  Processor        : {profile.cpu_name} ({profile.cpu_cores} threads)")
    print(f"  System Memory    : {profile.ram_gb:.1f} GB RAM")
    if profile.gpu_name:
        vram_text = f" ({profile.vram_gb:.1f} GB VRAM)" if profile.vram_gb is not None else ""
        print(f"  Graphics / GPU   : {profile.gpu_name}{vram_text}")
    else:
        print("  Graphics / GPU   : Integrated / CPU execution")
    print("-------------------------------------------------------------------")
    print(f"  Recommended      : {profile.headline}")
    print(f"  Rationale        : {profile.rationale}")
    print("-------------------------------------------------------------------")
    print("  Available Model Sizes:")
    for m in profile.models:
        rec_mark = " <-- RECOMMENDED" if m.status == "recommended" else ""
        print(f"   * {m.name} ({m.vram_approx}){rec_mark}")
        print(f"     {m.suitability}")
    print("===================================================================")
    print("")


if __name__ == "__main__":
    main()

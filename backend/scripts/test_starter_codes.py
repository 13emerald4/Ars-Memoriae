import asyncio
import json
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.code_runner_service import run_code  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


async def main():
    conn = sqlite3.connect(BACKEND_DIR / "dev.db")
    c = conn.cursor()
    c.execute("""
        SELECT c.id, d.name, n.field_values
        FROM cards c
        JOIN notes n ON c.note_id = n.id
        JOIN decks d ON c.deck_id = d.id
        ORDER BY d.position, d.name, c.id
    """)
    rows = c.fetchall()

    passed_starters = []
    failed_starters = []
    print(f"Testing starter_code for {len(rows)} cards in dev.db...\n")

    for card_id, deck_name, fv_str in rows:
        fv = json.loads(fv_str)
        title = fv.get("title") or fv.get("Front") or "Untitled"
        starter = fv.get("starter_code", "")
        lang = fv.get("language", "typescript")
        test_cases = fv.get("test_cases", [])

        if not starter:
            continue

        try:
            res = await run_code(
                code=starter,
                test_cases=test_cases,
                language=lang,
                timeout_sec=4.0,
            )
            status = res.get("status")
            passed = res.get("passed_count", 0)
            total = res.get("total_count", 0)
            err = res.get("error")
            if status == "Accepted":
                passed_starters.append((card_id, deck_name, title, passed, total))
                print(
                    f"[UNSOLVED PASSED!] {deck_name} | {title[:40]} | {status} ({passed}/{total})"
                )
            else:
                failed_starters.append((card_id, deck_name, title, status, passed, total, err))
        except Exception as e:
            failed_starters.append((card_id, deck_name, title, "Exception", 0, 0, str(e)))

    print(
        f"\nSummary: {len(passed_starters)} starter codes unexpectedly passed; {len(failed_starters)} properly failed."
    )


if __name__ == "__main__":
    asyncio.run(main())

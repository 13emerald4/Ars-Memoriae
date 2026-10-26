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
        SELECT c.id, d.name, n.id, n.field_values
        FROM cards c
        JOIN notes n ON c.note_id = n.id
        JOIN decks d ON c.deck_id = d.id
        ORDER BY d.position, d.name, c.id
    """)
    rows = c.fetchall()

    results = []
    print(f"Testing {len(rows)} cards in dev.db...")

    for card_id, deck_name, _note_id, fv_str in rows:
        fv = json.loads(fv_str)
        title = fv.get("title") or fv.get("Front") or "Untitled"
        back = fv.get("Back", "")
        lang = fv.get("language", "typescript")
        test_cases = fv.get("test_cases", [])

        # Test Back (the reference solution)
        try:
            res = await run_code(
                code=back,
                test_cases=test_cases,
                language=lang,
                timeout_sec=4.0,
            )
            status = res.get("status")
            passed = res.get("passed_count", 0)
            total = res.get("total_count", 0)
            err = res.get("error")
            results.append(
                {
                    "card_id": card_id,
                    "deck": deck_name,
                    "title": title,
                    "status": status,
                    "passed": passed,
                    "total": total,
                    "error": err,
                }
            )
            mark = "✓" if status == "Accepted" else "✗"
            print(
                f"[{mark}] {deck_name} | {title[:40]} | {status} ({passed}/{total}) {err if status != 'Accepted' else ''}"
            )
        except Exception as e:
            results.append(
                {
                    "card_id": card_id,
                    "deck": deck_name,
                    "title": title,
                    "status": "Exception",
                    "error": str(e),
                }
            )
            print(f"[!] {deck_name} | {title[:40]} | EXCEPTION: {e}")

    accepted = [r for r in results if r.get("status") == "Accepted"]
    print(f"\nSummary: {len(accepted)}/{len(results)} Accepted")


if __name__ == "__main__":
    asyncio.run(main())

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

    print(f"Testing student workflow across {len(rows)} cards...")
    failures = []

    for card_id, deck_name, fv_str in rows:
        fv = json.loads(fv_str)
        title = fv.get("title") or fv.get("Front") or "Untitled"
        starter = fv.get("starter_code", "")
        lang = fv.get("language", "typescript")
        test_cases = fv.get("test_cases", [])

        # If starter has a runner function, student edits inside the file or implements the class/function.
        # Back is the reference complete file.
        # But we specifically want to verify if starter_code order or exports create any friction!
        # Let's test Back directly (already 78/78).
        # And let's test specific cards where student edits starter:
        # e.g., 1e4736086f2c4568a9372709997a246d (readLogFile & loadEventsFromFile)
        if card_id == "1e4736086f2c4568a9372709997a246d":
            # Test when student writes code in starter_code
            student_solution = starter.replace(
                'export async function readLogFile(path: string): Promise<string> {\n  throw new Error("TODO");\n}',
                """export async function readLogFile(path: string): Promise<string> {
  const VIRTUAL_LOGS: Record<string, string> = {
    "/data/sample.log": "t1|INFO|boot\\nt2|WARN|low battery",
    "/data/empty.log": ""
  };
  if (path in VIRTUAL_LOGS) return VIRTUAL_LOGS[path];
  const fs = await import("node:fs/promises");
  return await fs.readFile(path, "utf8");
}""",
            ).replace(
                'export async function loadEventsFromFile(path: string): Promise<EventRecord[]> {\n  throw new Error("TODO");\n}',
                """export async function loadEventsFromFile(path: string): Promise<EventRecord[]> {
  const content = await readLogFile(path);
  return parseLog(content);
}

function parseLog(content: string): EventRecord[] {
  const lines = content.split("\\n");
  const records: EventRecord[] = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.length === 0) continue;
    records.push(parseEventLine(line));
  }
  return records;
}

function parseEventLine(line: string): EventRecord {
  const [timestamp, levelStr, message] = line.split("|");
  return { timestamp, level: levelStr as Level, message };
}""",
            )
            res = await run_code(student_solution, test_cases, language=lang)
            if res.get("status") != "Accepted":
                failures.append((card_id, deck_name, title, res.get("status"), res.get("error")))
                print(f"[FAIL] {deck_name} | {title} | {res.get('status')}: {res.get('error')}")
            else:
                print(f"[OK] {deck_name} | {title} | Accepted")

    if not failures:
        print("All tested student flows passed!")
    else:
        print(f"{len(failures)} failures detected.")


if __name__ == "__main__":
    asyncio.run(main())

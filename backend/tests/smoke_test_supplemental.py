import asyncio
import json
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.code_runner_service import run_node_code


async def main():
    deck_path = Path(r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\Midterm 2\Cards\cpsc210_mt2_supplemental.json")
    if not deck_path.exists():
        print(f"Deck not found at {deck_path}")
        return

    with open(deck_path, encoding="utf-8") as f:
        data = json.load(f)

    notes = data.get("notes", [])
    code_cards = [n for n in notes if n.get("kind") == "code"]
    print(f"Loaded {len(notes)} total notes, {len(code_cards)} code cards.")

    # 1. Run test_cases for each code card (using reference solution in back)
    print("\n--- RUNNING test_cases ---")
    total_tc_tested = 0
    total_tc_passed = 0

    for idx, card in enumerate(code_cards):
        title = card.get("title", f"Card {idx+1}")
        solution = card.get("back", "")
        test_cases = card.get("test_cases", [])

        if not test_cases:
            print(f"[{idx+1}/8] {title}: No test_cases defined (skipping)")
            continue

        res = await run_node_code(solution, test_cases)
        passed = res.get("passed_count", 0)
        total = res.get("total_count", len(test_cases))
        status = res.get("status")
        print(f"[{idx+1}/8] {title}: {status} ({passed}/{total})")
        if status != "Accepted":
            for r in res.get("results", []):
                if not r.get("passed"):
                    print(f"   Failed case: input={r.get('input')}, expected={r.get('expected')}, actual={r.get('actual')}, error={r.get('error')}")

        total_tc_tested += total
        total_tc_passed += passed

    print(f"\ntest_cases summary: {total_tc_passed}/{total_tc_tested} passed")

    # 2. Run starter_tests for each code card (combining solution with starter_tests)
    print("\n--- RUNNING starter_tests ---")
    total_st_tested = 0
    total_st_passed = 0

    for idx, card in enumerate(code_cards):
        title = card.get("title", f"Card {idx+1}")
        solution = card.get("back", "")
        starter_tests = card.get("starter_tests", "")

        if not starter_tests:
            print(f"[{idx+1}/8] {title}: No starter_tests (skipping)")
            continue

        # To run starter_tests, run_node_code takes test_code parameter:
        # Note: pass empty test_cases=[] or test_cases to see how starter_tests execute
        res = await run_node_code(solution, test_cases=[], test_code=starter_tests)
        passed = res.get("passed_count", 0)
        total = res.get("total_count", 0)
        status = res.get("status")
        print(f"[{idx+1}/8] {title}: {status} ({passed}/{total})")
        if status != "Accepted":
            for r in res.get("results", []):
                if not r.get("passed"):
                    print(f"   Failed test: name={r.get('name')}, error={r.get('error')}")

        total_st_tested += total
        total_st_passed += passed

    print(f"\nstarter_tests summary: {total_st_passed}/{total_st_tested} passed")

if __name__ == "__main__":
    asyncio.run(main())

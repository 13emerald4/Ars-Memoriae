"""TypeScript runner: `undefined` in test cases, TS-only syntax, and type checking.

The type-check tests need the TypeScript compiler, which the backend borrows
from the frontend's node_modules (`npm ci` in frontend/). Without it they skip;
the runner then reports `type_check: "unavailable"` and grades on behaviour.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.routers.review import (
    TYPE_ERROR_SCORE_CAP,
    _apply_execution_guardrails,
    _type_check_options,
)
from app.services.code_runner_service import run_code

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
HAS_TSC = (FRONTEND / "node_modules" / "typescript" / "package.json").exists()
needs_tsc = pytest.mark.skipif(not HAS_TSC, reason="TypeScript not installed (npm ci in frontend/)")


def _node_has_transform_types() -> bool:
    try:
        out = subprocess.run(
            [
                "node",
                "-p",
                "process.allowedNodeEnvironmentFlags.has('--experimental-transform-types')",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return out.stdout.strip() == "true"


UNDEFINED = {"$undefined": True}


# ── undefined in test cases ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_expected_undefined_matches_only_undefined():
    tests = [
        {"input": {"arr": [3, 4]}, "expected": 3},
        {"input": {"arr": []}, "expected": UNDEFINED},
    ]
    right = "function firstElement<T>(arr: T[]): T | undefined { return arr[0]; }"
    res = await run_code(right, tests, language="typescript")
    assert res["status"] == "Accepted", res
    assert res["passed_count"] == 2

    returns_null = (
        "function firstElement<T>(arr: T[]): T | null { return arr.length ? arr[0] : null; }"
    )
    res = await run_code(returns_null, tests, language="typescript")
    assert res["status"] == "Wrong Answer"
    assert [r["passed"] for r in res["results"]] == [True, False]
    # The case is reported as written, not as the decoded value.
    assert res["results"][1]["expected"] == UNDEFINED


@pytest.mark.asyncio
async def test_undefined_in_an_input_reaches_the_function():
    code = 'function label(name: string, role?: string): string { return `${name} (${role ?? "guest"})`; }'
    tests = [
        {"input": {"name": "Ada", "role": UNDEFINED}, "expected": "Ada (guest)"},
        {"input": {"name": "Ada", "role": "admin"}, "expected": "Ada (admin)"},
    ]
    res = await run_code(code, tests, language="typescript")
    assert res["status"] == "Accepted", res


@pytest.mark.asyncio
async def test_a_lookalike_object_is_not_decoded():
    code = "function same(x: unknown) { return x; }"
    tests = [
        {
            "input": {"x": {"$undefined": True, "other": 1}},
            "expected": {"$undefined": True, "other": 1},
        }
    ]
    res = await run_code(code, tests, language="typescript")
    assert res["status"] == "Accepted", res


# ── expected errors ────────────────────────────────────────────────────────

PARSE_AGE = """
class ValidationError extends Error {
  name = "ValidationError";
}
function parseAge(text: string): number {
  const n = Number(text);
  if (!Number.isInteger(n) || n < 0) throw new ValidationError(`invalid age: ${text}`);
  return n;
}
"""


@pytest.mark.asyncio
async def test_expected_throw_matches_name_and_message():
    tests = [
        {"input": ["42"], "expected": 42},
        {"input": ["-1"], "expected": {"$throws": "ValidationError: invalid age"}},
        {"input": ["abc"], "expected": {"$throws": True}},
    ]
    res = await run_code(PARSE_AGE, tests, language="typescript")
    assert res["status"] == "Accepted", res
    assert res["passed_count"] == 3


@pytest.mark.asyncio
async def test_expected_throw_fails_when_nothing_is_thrown_or_the_message_differs():
    lenient = "function parseAge(text: string): number { return Number(text) || 0; }"
    res = await run_code(
        lenient, [{"input": ["-1"], "expected": {"$throws": "invalid age"}}], language="typescript"
    )
    assert res["status"] == "Wrong Answer", res
    assert "Expected an error" in res["results"][0]["error"]

    other = 'function parseAge(text: string): number { throw new RangeError("nope"); }'
    res = await run_code(
        other, [{"input": ["-1"], "expected": {"$throws": "invalid age"}}], language="typescript"
    )
    assert res["status"] == "Wrong Answer", res
    assert "RangeError: nope" in res["results"][0]["error"]


@pytest.mark.asyncio
async def test_expected_rejection_of_an_async_function():
    code = (
        'async function load(ok: boolean) { if (!ok) throw new Error("HTTP 404"); return "body"; }'
    )
    tests = [
        {"input": [True], "expected": "body"},
        {"input": [False], "expected": {"$throws": "HTTP 404"}},
    ]
    res = await run_code(code, tests, language="typescript")
    assert res["status"] == "Accepted", res


# ── TypeScript-only syntax ─────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _node_has_transform_types(), reason="this Node has no --experimental-transform-types"
)
async def test_enum_and_parameter_properties_run():
    code = """
enum Level { Low = 1, High = 10 }
class Account {
  constructor(private readonly owner: string, public balance: number) {}
  describe(): string { return `${this.owner}:${this.balance}`; }
}
function score(level: Level, owner: string): string {
  return new Account(owner, level).describe();
}
"""
    res = await run_code(
        code,
        [{"input": {"level": 10, "owner": "ada"}, "expected": "ada:10"}],
        language="typescript",
    )
    assert res["status"] == "Accepted", res


# ── type checking ──────────────────────────────────────────────────────────

PLUCK_TESTS = [
    {"input": {"items": [{"id": 1}, {"id": 2}, {"id": 3}], "key": "id"}, "expected": [1, 2, 3]},
]
PLUCK_TYPE_TESTS = """\
const ids: number[] = pluck([{ id: 1, name: "a" }], "id");
// @ts-expect-error: "age" is not a key of the items
pluck([{ id: 1 }], "age");
"""
PLUCK_RIGHT = "function pluck<T, K extends keyof T>(items: T[], key: K): T[K][] { return items.map((i) => i[key]); }"


@pytest.mark.asyncio
@needs_tsc
async def test_type_check_accepts_correct_types():
    res = await run_code(
        PLUCK_RIGHT,
        PLUCK_TESTS,
        language="typescript",
        type_check=True,
        type_tests=PLUCK_TYPE_TESTS,
    )
    assert res["status"] == "Accepted", res
    assert res["type_check"] == "passed"


@pytest.mark.asyncio
@needs_tsc
async def test_type_check_rejects_loose_types_that_still_run():
    loose = "function pluck(items: any[], key: string): any[] { return items.map((i) => i[key]); }"
    res = await run_code(
        loose, PLUCK_TESTS, language="typescript", type_check=True, type_tests=PLUCK_TYPE_TESTS
    )
    assert res["status"] == "Type Error", res
    assert res["passed_count"] == 1  # runtime results are kept
    assert 'pluck([{ id: 1 }], "age");' in res["error"]
    assert "should be a type error" in res["error"]
    assert '"age" is not a key of the items' in res["error"]


@pytest.mark.asyncio
@needs_tsc
async def test_type_check_reports_errors_in_the_answer_by_line():
    wrong = (
        "function double(n: number): number {\n  const s: string = n * 2;\n  return s as any;\n}"
    )
    res = await run_code(
        wrong, [{"input": {"n": 2}, "expected": 4}], language="typescript", type_check=True
    )
    assert res["status"] == "Type Error", res
    assert "Line 2:" in res["error"]
    assert res["type_errors"][0]["where"] == "code"


@pytest.mark.asyncio
@needs_tsc
async def test_type_check_runs_as_a_module_with_console():
    # `name` would clash with the DOM's window.name in a script; console must exist.
    code = 'const name = "x";\nfunction greet(): string { console.log(name); return name; }'
    res = await run_code(
        code, [{"input": {}, "expected": "x"}], language="typescript", type_check=True
    )
    assert res["status"] == "Accepted", res


@pytest.mark.asyncio
async def test_without_type_check_wrong_types_still_run():
    wrong = "function double(n: number): string { return (n * 2) as any; }"
    res = await run_code(wrong, [{"input": {"n": 2}, "expected": 4}], language="typescript")
    assert res["status"] == "Accepted"
    assert "type_check" not in res


# ── grading ────────────────────────────────────────────────────────────────


def _graded(score: int, exec_res: dict) -> int:
    result = {"score": score, "grade": "easy"}
    _apply_execution_guardrails(result, exec_res)
    return result["score"]


def test_a_type_error_caps_the_score_in_the_hard_band():
    assert (
        _graded(95, {"status": "Type Error", "passed_count": 3, "total_count": 3})
        == TYPE_ERROR_SCORE_CAP
    )
    assert _graded(30, {"status": "Type Error", "passed_count": 3, "total_count": 3}) == 30
    # Runtime failures still cap lower.
    assert _graded(95, {"status": "Type Error", "passed_count": 0, "total_count": 3}) == 39


def test_accepted_runs_keep_their_floor():
    assert _graded(20, {"status": "Accepted", "passed_count": 2, "total_count": 2}) == 70


def test_type_check_options_follow_the_card_fields():
    assert _type_check_options({}) == {}
    assert _type_check_options({"type_check": False, "type_tests": "x"}) == {}
    assert _type_check_options({"type_check": True}) == {"type_check": True, "type_tests": None}
    assert _type_check_options({"type_check": True, "type_tests": "f(1);"}) == {
        "type_check": True,
        "type_tests": "f(1);",
    }


# ── end to end: import a card, run an answer against it ───────────────────


@pytest.mark.asyncio
@needs_tsc
async def test_imported_type_checked_card_runs_with_its_type_tests(auth_client):
    imported = await auth_client.post(
        "/api/import/json",
        json={
            "deck": "Type check deck",
            "notes": [
                {
                    "kind": "code",
                    "front": "Implement pluck",
                    "back": PLUCK_RIGHT,
                    "starter_code": "function pluck<T, K extends keyof T>(items: T[], key: K): T[K][] {\n  return [];\n}",
                    "test_cases": PLUCK_TESTS,
                    "language": "typescript",
                    "type_check": True,
                    "type_tests": PLUCK_TYPE_TESTS,
                }
            ],
        },
    )
    assert imported.status_code in (200, 201), imported.text
    deck_id = imported.json()["deck_id"]
    cards = (await auth_client.get("/api/cards", params={"deck_id": deck_id})).json()
    assert len(cards) == 1
    card_id = cards[0]["id"]

    loose = "function pluck(items: any[], key: string): any[] { return items.map((i) => i[key]); }"
    run = await auth_client.post(
        f"/api/review/{card_id}/run-code", json={"code": loose, "language": "typescript"}
    )
    assert run.status_code == 200, run.text
    assert run.json()["status"] == "Type Error"

    run = await auth_client.post(
        f"/api/review/{card_id}/run-code", json={"code": PLUCK_RIGHT, "language": "typescript"}
    )
    assert run.json()["status"] == "Accepted"

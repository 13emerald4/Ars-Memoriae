"""Tests for Coding Practice, LeetCode Studio, and Pre-LeetCode Fundamentals."""

from __future__ import annotations

import pytest

from app.services.code_runner_service import run_python_code


@pytest.mark.asyncio
async def test_python_code_runner_function():
    code = """def convert_types(val_str: str, num: int):
    return (int(val_str), str(num), float(val_str), bool(num))
"""
    test_cases = [
        {"input": {"val_str": "42", "num": 10}, "expected": [42, "10", 42.0, True]},
        {"input": {"val_str": "-5", "num": 0}, "expected": [-5, "0", -5.0, False]},
    ]
    res = await run_python_code(code, test_cases)
    assert res["status"] == "Accepted"
    assert res["passed_count"] == 2
    assert res["total_count"] == 2
    assert len(res["results"]) == 2
    assert res["results"][0]["passed"] is True


@pytest.mark.asyncio
async def test_python_code_runner_solution_class():
    code = """class Solution:
    def largestInteger(self, nums: list[int], k: int) -> int:
        from collections import defaultdict
        n = len(nums)
        subarray_count = defaultdict(int)
        for i in range(n - k + 1):
            unique_in_sub = set(nums[i : i + k])
            for val in unique_in_sub:
                subarray_count[val] += 1
        candidates = [x for x, count in subarray_count.items() if count == 1]
        return max(candidates) if candidates else -1
"""
    test_cases = [
        {"input": {"nums": [3, 9, 2, 1, 7], "k": 3}, "expected": 7},
        {"input": {"nums": [0, 0], "k": 1}, "expected": -1},
    ]
    res = await run_python_code(code, test_cases)
    assert res["status"] == "Accepted"
    assert res["passed_count"] == 2


@pytest.mark.asyncio
async def test_python_code_runner_syntax_error():
    code = "def bad_syntax( -- :"
    test_cases = [{"input": {}, "expected": None}]
    res = await run_python_code(code, test_cases)
    assert res["status"] == "Compile Error"
    assert "SyntaxError" in (res.get("error") or "")


@pytest.mark.asyncio
async def test_python_code_runner_timeout_kill():
    code = """def infinite_loop():
    while True:
        pass
"""
    test_cases = [{"input": {}, "expected": None}]
    res = await run_python_code(code, test_cases, timeout_sec=0.5)
    assert res["status"] == "Time Limit Exceeded"
    assert "Time Limit Exceeded" in (res.get("error") or "")
    assert res["passed_count"] == 0



@pytest.mark.asyncio
async def test_typescript_code_runner():
    from app.services.code_runner_service import run_code

    code = """
function twoSum(nums: number[], target: number): number[] {
    const map = new Map<number, number>();
    for (let i = 0; i < nums.length; i++) {
        const diff = target - nums[i];
        if (map.has(diff)) return [map.get(diff)!, i];
        map.set(nums[i], i);
    }
    return [];
}
"""
    test_cases = [
        {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]},
        {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2]},
    ]
    res = await run_code(code, test_cases, language="typescript")
    assert res["status"] == "Accepted"
    assert res["passed_count"] == 2
    assert res["total_count"] == 2


@pytest.mark.asyncio
async def test_code_practice_api_endpoints(auth_client):
    # 1. List problems (catalogs seeded automatically)
    resp = await auth_client.get("/api/code/problems")
    assert resp.status_code == 200
    problems = resp.json()
    assert len(problems) >= 10

    # Filter by fundamental
    resp_fund = await auth_client.get("/api/code/problems?kind=fundamental")
    assert resp_fund.status_code == 200
    fund_list = resp_fund.json()
    assert any(p["slug"] == "py-basics-type-casting" for p in fund_list)
    assert any(p["track"] == "track_0_python_basics" for p in fund_list)

    # Filter by problem
    resp_prob = await auth_client.get("/api/code/problems?kind=problem")
    assert resp_prob.status_code == 200
    prob_list = resp_prob.json()
    assert any(p["slug"] == "find-the-largest-almost-missing-integer" for p in prob_list)

    # 2. Get single problem
    resp_get = await auth_client.get("/api/code/problems/find-the-largest-almost-missing-integer")
    assert resp_get.status_code == 200
    detail = resp_get.json()
    assert "Find the Largest Almost Missing Integer" in detail["title"]
    assert len(detail["test_cases"]) >= 2
    assert "python" in detail["starter_codes"]

    # 3. Run code on problem
    run_resp = await auth_client.post(
        "/api/code/problems/find-the-largest-almost-missing-integer/run",
        json={
            "code": detail["solutions"]["python"],
            "language": "python",
        },
    )
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["status"] == "Accepted"
    assert run_data["passed_count"] == run_data["total_count"]

    # 4. Submit code
    submit_resp = await auth_client.post(
        "/api/code/problems/find-the-largest-almost-missing-integer/submit",
        json={
            "code": detail["solutions"]["python"],
            "language": "python",
        },
    )
    assert submit_resp.status_code == 200
    sub_data = submit_resp.json()
    assert sub_data["status"] == "Accepted"
    assert "submission_id" in sub_data

    # 5. List submissions
    subs_resp = await auth_client.get("/api/code/submissions")
    assert subs_resp.status_code == 200
    subs = subs_resp.json()
    assert len(subs) >= 1
    assert subs[0]["status"] == "Accepted"

    # 6. Export to deck
    # Create deck first
    deck_resp = await auth_client.post("/api/decks", json={"name": "Coding Mastery"})
    assert deck_resp.status_code in (200, 201)
    deck_id = deck_resp.json()["id"]

    export_resp = await auth_client.post(
        "/api/code/problems/find-the-largest-almost-missing-integer/export-card",
        json={"deck_id": deck_id},
    )
    assert export_resp.status_code == 200
    assert "note_id" in export_resp.json()

    # 7. Progression Stats
    stats_resp = await auth_client.get("/api/code/stats")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()
    assert "totals" in stats_data
    assert stats_data["totals"]["cards"] >= 75
    assert stats_data["totals"]["reviews_logged"] >= 1
    assert "velocity" in stats_data
    assert "heatmap" in stats_data
    assert "categories" in stats_data
    assert len(stats_data["categories"]) >= 18
    assert "difficulty" in stats_data
    assert stats_data["difficulty"]["easy"]["total"] > 0


@pytest.mark.asyncio
async def test_tdd_student_unit_tests_typescript():
    from app.services.code_runner_service import run_code

    code = """
function clamp(val: number, min: number, max: number): number {
    return Math.max(min, Math.min(val, max));
}
"""
    test_code = """
test('clamps below range', () => {
    assertEquals(clamp(-5, 0, 10), 0);
});

test('clamps above range', () => {
    assertEquals(clamp(15, 0, 10), 10);
});

test('within range unchanged', () => {
    assertTrue(clamp(5, 0, 10) === 5);
});
"""
    res = await run_code(code, [], language="typescript", test_code=test_code)
    assert res["status"] == "Accepted"
    assert res["student_passed_count"] == 3
    assert res["student_total_count"] == 3
    assert len(res["student_tests"]) == 3
    assert all(t["passed"] for t in res["student_tests"])


@pytest.mark.asyncio
async def test_tdd_student_unit_tests_failing_assertion():
    from app.services.code_runner_service import run_code

    code = """
function clamp(val: number, min: number, max: number): number {
    return val; // buggy: does not clamp!
}
"""
    test_code = """
test('clamps below range', () => {
    assertEquals(0, clamp(-5, 0, 10));
});
"""
    res = await run_code(code, [], language="typescript", test_code=test_code)
    assert res["status"] == "Wrong Answer"
    assert res["student_passed_count"] == 0
    assert res["student_total_count"] == 1
    assert res["student_tests"][0]["passed"] is False
    assert "Expected 0, but got -5" in res["student_tests"][0]["error"]


@pytest.mark.asyncio
async def test_tdd_student_unit_tests_python():
    from app.services.code_runner_service import run_code

    code = """
def clamp(val: int, low: int, high: int) -> int:
    return max(low, min(val, high))
"""
    test_code = """
import unittest

class TestClamp(unittest.TestCase):
    def test_lower_bound(self):
        self.assertEqual(clamp(-5, 0, 10), 0)

    def test_upper_bound(self):
        self.assertEqual(clamp(15, 0, 10), 10)
"""
    res = await run_code(code, [], language="python", test_code=test_code)
    assert res["status"] == "Accepted"
    assert res["student_passed_count"] == 2
    assert res["student_total_count"] == 2
    assert len(res["student_tests"]) == 2
    assert all(t["passed"] for t in res["student_tests"])


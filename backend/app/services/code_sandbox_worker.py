"""Standalone Worker Process for Isolated Python Code Execution.

Invoked as a separate child process by code_runner_service to isolate user code
execution from the main backend process, prevent memory contamination, and allow
clean process-level termination on timeout.
"""

from __future__ import annotations

import ast
import io
import json
import sys
import time
import traceback
from typing import Any


def _find_entrypoint(code: str) -> tuple[str, bool]:
    """Finds the function or method name to invoke. Returns (func_name, is_method)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ("", False)

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Solution":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and not item.name.startswith("__"):
                    return (item.name, True)
        elif isinstance(node, ast.FunctionDef) and not node.name.startswith("__"):
            return (node.name, False)

    return ("", False)


def _deep_equal(a: Any, b: Any) -> bool:
    """Tolerant structural comparison (tuples vs lists, float precision)."""
    if isinstance(a, tuple) and isinstance(b, list):
        return len(a) == len(b) and all(_deep_equal(x, y) for x, y in zip(a, b, strict=False))
    if isinstance(a, list) and isinstance(b, tuple):
        return len(a) == len(b) and all(_deep_equal(x, y) for x, y in zip(a, b, strict=False))
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_deep_equal(x, y) for x, y in zip(a, b, strict=False))
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a.keys()) != set(b.keys()):
            return False
        return all(_deep_equal(a[k], b[k]) for k in a)
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) < 1e-5
        except (ValueError, TypeError):
            return False
    return a == b


def _run_student_tests(glob: dict[str, Any], test_code: str) -> tuple[list[dict], int, int]:
    student_tests: list[dict] = []
    student_passed_count = 0
    if not test_code or not test_code.strip():
        return student_tests, 0, 0

    try:
        compiled_test = compile(test_code, "<student_tests>", "exec")
        exec(compiled_test, glob)
    except Exception:
        err = traceback.format_exc().strip().split("\n")[-1]
        student_tests.append({
            "test_name": "Test Suite Syntax / Execution",
            "passed": False,
            "error": err,
            "runtime_ms": 0.0,
        })
        return student_tests, 0, 1

    import unittest
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for obj in list(glob.values()):
        if isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj is not unittest.TestCase:
            suite.addTests(loader.loadTestsFromTestCase(obj))

    if suite.countTestCases() > 0:
        for test in suite:
            test_name = test._testMethodName
            t_start = time.perf_counter()
            res = unittest.TestResult()
            test.run(res)
            t_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
            if res.wasSuccessful():
                student_tests.append({
                    "test_name": test_name,
                    "passed": True,
                    "error": None,
                    "runtime_ms": t_ms,
                })
                student_passed_count += 1
            else:
                err_line = ""
                if res.failures:
                    err_line = res.failures[0][1].strip().split("\n")[-1]
                elif res.errors:
                    err_line = res.errors[0][1].strip().split("\n")[-1]
                student_tests.append({
                    "test_name": test_name,
                    "passed": False,
                    "error": err_line or "Assertion failed",
                    "runtime_ms": t_ms,
                })
    else:
        student_tests.append({
            "test_name": "Top-level Test Execution",
            "passed": True,
            "error": None,
            "runtime_ms": 1.0,
        })
        student_passed_count = 1

    return student_tests, student_passed_count, len(student_tests)


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input)
    except Exception as e:
        sys.stdout.write(
            json.dumps({
                "status": "Compile Error",
                "passed_count": 0,
                "total_count": 0,
                "runtime_ms": 0.0,
                "error": f"Invalid payload: {e}",
                "results": [],
            })
        )
        return

    code = payload.get("code", "")
    test_code = payload.get("test_code")
    test_cases = payload.get("test_cases", [])
    custom_entrypoint = payload.get("custom_entrypoint")

    # Pre-compile the code
    try:
        compiled_code = compile(code, "<user_code>", "exec")
    except SyntaxError as e:
        sys.stdout.write(
            json.dumps({
                "status": "Compile Error",
                "passed_count": 0,
                "total_count": len(test_cases) or 1,
                "runtime_ms": 0.0,
                "error": f"SyntaxError: {e.msg} on line {e.lineno}",
                "results": [],
            })
        )
        return
    except Exception as e:
        sys.stdout.write(
            json.dumps({
                "status": "Compile Error",
                "passed_count": 0,
                "total_count": len(test_cases) or 1,
                "runtime_ms": 0.0,
                "error": f"Compilation error: {e}",
                "results": [],
            })
        )
        return

    # If no test cases are provided, execute directly and capture stdout / exceptions
    if not test_cases:
        stdout_buf = io.StringIO()
        tc_start = time.perf_counter()
        old_stdout = sys.stdout
        sys.stdout = stdout_buf
        error_msg = None
        glob: dict[str, Any] = {}
        try:
            exec(compiled_code, glob)
        except Exception:
            err = traceback.format_exc()
            error_msg = err.strip().split("\n")[-1]
        finally:
            sys.stdout = old_stdout

        tc_runtime = (time.perf_counter() - tc_start) * 1000.0
        captured_stdout = stdout_buf.getvalue()

        st_tests, st_passed, st_total = ([], 0, 0)
        if test_code and not error_msg:
            st_tests, st_passed, st_total = _run_student_tests(glob, test_code)

        st_all_passed = (st_passed == st_total) if st_total > 0 else True
        final_status = "Runtime Error" if error_msg else ("Accepted" if st_all_passed else "Wrong Answer")

        sys.stdout.write(
            json.dumps({
                "status": final_status,
                "passed_count": 0 if (error_msg or not st_all_passed) else 1,
                "total_count": 1,
                "runtime_ms": round(tc_runtime, 2),
                "error": error_msg,
                "results": [
                    {
                        "test_index": 1,
                        "passed": not bool(error_msg) and st_all_passed,
                        "stdout": captured_stdout,
                        "error": error_msg,
                        "runtime_ms": round(tc_runtime, 2),
                    }
                ],
                "student_tests": st_tests,
                "student_passed_count": st_passed,
                "student_total_count": st_total,
            })
        )
        return

    entrypoint, is_method = _find_entrypoint(code)
    if custom_entrypoint:
        entrypoint = custom_entrypoint

    if not entrypoint:
        sys.stdout.write(
            json.dumps({
                "status": "Compile Error",
                "passed_count": 0,
                "total_count": len(test_cases),
                "runtime_ms": 0.0,
                "error": "No callable function or Solution method found.",
                "results": [],
            })
        )
        return

    results = []
    passed_count = 0
    total_start = time.perf_counter()
    overall_status = "Accepted"

    for idx, tc in enumerate(test_cases):
        inputs = tc.get("input", {})
        expected = tc.get("expected")

        stdout_buf = io.StringIO()
        tc_start = time.perf_counter()
        error_msg = None
        actual_output = None
        is_passed = False

        old_stdout = sys.stdout
        sys.stdout = stdout_buf
        glob: dict[str, Any] = {}
        try:
            exec(compiled_code, glob)
            if is_method:
                sol_cls = glob.get("Solution")
                if sol_cls is None:
                    error_msg = "Solution class not found."
                else:
                    instance = sol_cls()
                    func = getattr(instance, entrypoint, None)
            else:
                func = glob.get(entrypoint)

            if not error_msg:
                if not callable(func):
                    error_msg = f"Function '{entrypoint}' is not callable."
                else:
                    if isinstance(inputs, dict):
                        actual_output = func(**inputs)
                    elif isinstance(inputs, (list, tuple)):
                        actual_output = func(*inputs)
                    else:
                        actual_output = func(inputs)
        except Exception:
            err = traceback.format_exc()
            error_msg = err.strip().split("\n")[-1]
        finally:
            sys.stdout = old_stdout

        tc_runtime = (time.perf_counter() - tc_start) * 1000.0
        captured_stdout = stdout_buf.getvalue()

        if error_msg:
            overall_status = "Runtime Error" if overall_status == "Accepted" else overall_status
            is_passed = False
        else:
            is_passed = _deep_equal(actual_output, expected)
            if is_passed:
                passed_count += 1
            else:
                if overall_status == "Accepted":
                    overall_status = "Wrong Answer"

        results.append({
            "test_index": idx + 1,
            "passed": is_passed,
            "input": inputs,
            "expected": expected,
            "actual": actual_output,
            "stdout": captured_stdout,
            "error": error_msg,
            "runtime_ms": round(tc_runtime, 2),
        })

    st_tests, st_passed, st_total = ([], 0, 0)
    if test_code:
        st_glob: dict[str, Any] = {}
        try:
            exec(compiled_code, st_glob)
            st_tests, st_passed, st_total = _run_student_tests(st_glob, test_code)
        except Exception:
            err = traceback.format_exc().strip().split("\n")[-1]
            st_tests = [{"test_name": "Test Suite Setup", "passed": False, "error": err, "runtime_ms": 0.0}]
            st_total = 1

    st_all_passed = (st_passed == st_total) if st_total > 0 else True
    if not st_all_passed and overall_status == "Accepted":
        overall_status = "Wrong Answer"

    total_runtime = (time.perf_counter() - total_start) * 1000.0

    sys.stdout.write(
        json.dumps({
            "status": overall_status if (passed_count == len(test_cases) and st_all_passed) else (overall_status or "Wrong Answer"),
            "passed_count": passed_count,
            "total_count": len(test_cases),
            "runtime_ms": round(total_runtime, 2),
            "results": results,
            "student_tests": st_tests,
            "student_passed_count": st_passed,
            "student_total_count": st_total,
        })
    )


if __name__ == "__main__":
    main()

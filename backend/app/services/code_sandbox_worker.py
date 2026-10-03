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

        sys.stdout.write(
            json.dumps({
                "status": "Runtime Error" if error_msg else "Accepted",
                "passed_count": 0 if error_msg else 1,
                "total_count": 1,
                "runtime_ms": round(tc_runtime, 2),
                "error": error_msg,
                "results": [
                    {
                        "test_index": 1,
                        "passed": not bool(error_msg),
                        "stdout": captured_stdout,
                        "error": error_msg,
                        "runtime_ms": round(tc_runtime, 2),
                    }
                ],
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

    total_runtime = (time.perf_counter() - total_start) * 1000.0

    sys.stdout.write(
        json.dumps({
            "status": overall_status if passed_count == len(test_cases) else (overall_status or "Wrong Answer"),
            "passed_count": passed_count,
            "total_count": len(test_cases),
            "runtime_ms": round(total_runtime, 2),
            "results": results,
        })
    )


if __name__ == "__main__":
    main()

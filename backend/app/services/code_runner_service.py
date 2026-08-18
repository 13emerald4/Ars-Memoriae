"""Safe Python Code Execution Sandbox & Test Harness Runner.

Executes user code against test cases, capturing stdout, execution runtime,
and verifying expected output with AST introspection and timeout guards.
"""

from __future__ import annotations

import ast
import asyncio
import io
import sys
import time
import traceback
from typing import Any


def _find_entrypoint(code: str) -> tuple[str, bool]:
    """Finds the function or method name to invoke.
    
    Returns (func_name, is_method).
    """
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
        return len(a) == len(b) and all(_deep_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, list) and isinstance(b, tuple):
        return len(a) == len(b) and all(_deep_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_deep_equal(x, y) for x, y in zip(a, b))
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


async def run_python_code(
    code: str,
    test_cases: list[dict],
    custom_entrypoint: str | None = None,
    timeout_sec: float = 3.0,
) -> dict[str, Any]:
    """Executes Python code against a list of test cases in an async worker."""
    entrypoint, is_method = _find_entrypoint(code)
    if custom_entrypoint:
        entrypoint = custom_entrypoint

    if not entrypoint:
        # Check if syntax error
        try:
            ast.parse(code)
        except SyntaxError as e:
            return {
                "status": "Compile Error",
                "passed_count": 0,
                "total_count": len(test_cases),
                "runtime_ms": 0.0,
                "error": f"SyntaxError: {e.msg} on line {e.lineno}",
                "results": [],
            }
        return {
            "status": "Compile Error",
            "passed_count": 0,
            "total_count": len(test_cases),
            "runtime_ms": 0.0,
            "error": "No callable function or Solution method found.",
            "results": [],
        }

    results = []
    passed_count = 0
    total_start = time.perf_counter()

    # Pre-compile the code
    try:
        compiled_code = compile(code, "<user_code>", "exec")
    except Exception as e:
        return {
            "status": "Compile Error",
            "passed_count": 0,
            "total_count": len(test_cases),
            "runtime_ms": 0.0,
            "error": f"Compilation error: {e}",
            "results": [],
        }

    overall_status = "Accepted"

    for idx, tc in enumerate(test_cases):
        inputs = tc.get("input", {})
        expected = tc.get("expected")

        stdout_buf = io.StringIO()
        tc_start = time.perf_counter()
        tc_runtime = 0.0
        error_msg = None
        actual_output = None
        is_passed = False

        def _execute_sync() -> tuple[Any, str, str | None]:
            old_stdout = sys.stdout
            sys.stdout = stdout_buf
            glob: dict[str, Any] = {}
            try:
                exec(compiled_code, glob)
                if is_method:
                    sol_cls = glob.get("Solution")
                    if sol_cls is None:
                        return None, stdout_buf.getvalue(), "Solution class not found."
                    instance = sol_cls()
                    func = getattr(instance, entrypoint, None)
                else:
                    func = glob.get(entrypoint)

                if not callable(func):
                    return None, stdout_buf.getvalue(), f"Function '{entrypoint}' is not callable."

                # Call function with kwargs or positional args
                if isinstance(inputs, dict):
                    output = func(**inputs)
                elif isinstance(inputs, (list, tuple)):
                    output = func(*inputs)
                else:
                    output = func(inputs)

                return output, stdout_buf.getvalue(), None
            except Exception:
                return None, stdout_buf.getvalue(), traceback.format_exc()
            finally:
                sys.stdout = old_stdout

        try:
            # Run with timeout
            output, captured_stdout, err = await asyncio.wait_for(
                asyncio.to_thread(_execute_sync),
                timeout=timeout_sec,
            )
            tc_runtime = (time.perf_counter() - tc_start) * 1000.0

            if err:
                error_msg = err.strip().split("\n")[-1]  # Last line of traceback
                overall_status = "Runtime Error" if overall_status == "Accepted" else overall_status
                is_passed = False
            else:
                actual_output = output
                is_passed = _deep_equal(actual_output, expected)
                if is_passed:
                    passed_count += 1
                else:
                    if overall_status == "Accepted":
                        overall_status = "Wrong Answer"

        except TimeoutError:
            tc_runtime = timeout_sec * 1000.0
            error_msg = f"Time Limit Exceeded (> {timeout_sec}s)"
            overall_status = "Time Limit Exceeded"
            is_passed = False

        results.append(
            {
                "test_index": idx + 1,
                "passed": is_passed,
                "input": inputs,
                "expected": expected,
                "actual": actual_output,
                "stdout": captured_stdout if 'captured_stdout' in locals() else "",
                "error": error_msg,
                "runtime_ms": round(tc_runtime, 2),
            }
        )

    total_runtime = (time.perf_counter() - total_start) * 1000.0

    return {
        "status": overall_status if passed_count == len(test_cases) else (overall_status or "Wrong Answer"),
        "passed_count": passed_count,
        "total_count": len(test_cases),
        "runtime_ms": round(total_runtime, 2),
        "results": results,
    }

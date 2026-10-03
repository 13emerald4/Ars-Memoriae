"""Safe Python Code Execution Sandbox & Test Harness Runner.

Executes user code against test cases, capturing stdout, execution runtime,
and verifying expected output with AST introspection and timeout guards.
"""

from __future__ import annotations

import ast
import asyncio
import json
import os
import sys
import time
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


async def run_python_code(
    code: str,
    test_cases: list[dict],
    custom_entrypoint: str | None = None,
    timeout_sec: float = 3.0,
) -> dict[str, Any]:
    """Executes Python code against a list of test cases in an isolated child subprocess."""
    payload = json.dumps({
        "code": code,
        "test_cases": test_cases,
        "custom_entrypoint": custom_entrypoint,
    }).encode("utf-8")

    total_start = time.perf_counter()

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "app.services.code_sandbox_worker",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as e:
        return {
            "status": "Runtime Error",
            "passed_count": 0,
            "total_count": len(test_cases),
            "runtime_ms": 0.0,
            "error": f"Failed to spawn execution worker: {e}",
            "results": [],
        }

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(input=payload),
            timeout=timeout_sec,
        )
    except TimeoutError:
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        return {
            "status": "Time Limit Exceeded",
            "passed_count": 0,
            "total_count": len(test_cases),
            "runtime_ms": round(timeout_sec * 1000.0, 2),
            "error": f"Time Limit Exceeded (> {timeout_sec}s)",
            "results": [
                {
                    "test_index": idx + 1,
                    "passed": False,
                    "input": tc.get("input", {}),
                    "expected": tc.get("expected"),
                    "actual": None,
                    "stdout": "",
                    "error": f"Time Limit Exceeded (> {timeout_sec}s)",
                    "runtime_ms": round(timeout_sec * 1000.0, 2),
                }
                for idx, tc in enumerate(test_cases)
            ],
        }

    try:
        data = json.loads(stdout_bytes.decode("utf-8"))
    except Exception:
        err_msg = (
            stderr_bytes.decode("utf-8", errors="replace").strip()
            or "Execution worker returned invalid output."
        )
        return {
            "status": "Runtime Error",
            "passed_count": 0,
            "total_count": len(test_cases),
            "runtime_ms": round((time.perf_counter() - total_start) * 1000.0, 2),
            "error": err_msg,
            "results": [],
        }

    return data


async def run_node_code(
    code: str,
    test_cases: list[dict],
    custom_entrypoint: str | None = None,
    timeout_sec: float = 4.0,
) -> dict[str, Any]:
    """Executes TypeScript / JavaScript code against test cases using isolated Node.js worker."""
    payload = json.dumps({
        "code": code,
        "test_cases": test_cases,
        "custom_entrypoint": custom_entrypoint,
    }).encode("utf-8")

    total_start = time.perf_counter()
    worker_script = os.path.join(os.path.dirname(__file__), "ts_sandbox_worker.mjs")

    try:
        proc = await asyncio.create_subprocess_exec(
            "node",
            worker_script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as e:
        return {
            "status": "Runtime Error",
            "passed_count": 0,
            "total_count": len(test_cases),
            "runtime_ms": 0.0,
            "error": f"Failed to spawn Node execution worker (is Node.js installed?): {e}",
            "results": [],
        }

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(input=payload),
            timeout=timeout_sec,
        )
    except TimeoutError:
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        return {
            "status": "Time Limit Exceeded",
            "passed_count": 0,
            "total_count": len(test_cases),
            "runtime_ms": round(timeout_sec * 1000.0, 2),
            "error": f"Time Limit Exceeded (> {timeout_sec}s)",
            "results": [
                {
                    "test_index": idx + 1,
                    "passed": False,
                    "input": tc.get("input", {}),
                    "expected": tc.get("expected"),
                    "actual": None,
                    "stdout": "",
                    "error": f"Time Limit Exceeded (> {timeout_sec}s)",
                    "runtime_ms": round(timeout_sec * 1000.0, 2),
                }
                for idx, tc in enumerate(test_cases)
            ],
        }

    try:
        data = json.loads(stdout_bytes.decode("utf-8"))
    except Exception:
        err_msg = (
            stderr_bytes.decode("utf-8", errors="replace").strip()
            or "Node execution worker returned invalid output."
        )
        return {
            "status": "Runtime Error",
            "passed_count": 0,
            "total_count": len(test_cases),
            "runtime_ms": round((time.perf_counter() - total_start) * 1000.0, 2),
            "error": err_msg,
            "results": [],
        }

    return data


async def run_code(
    code: str,
    test_cases: list[dict],
    language: str = "python",
    custom_entrypoint: str | None = None,
    timeout_sec: float = 4.0,
) -> dict[str, Any]:
    """Universal sandbox runner supporting Python, TypeScript, and JavaScript."""
    lang = (language or "python").lower().strip()
    if lang in ("typescript", "javascript", "ts", "js"):
        return await run_node_code(
            code=code,
            test_cases=test_cases,
            custom_entrypoint=custom_entrypoint,
            timeout_sec=timeout_sec,
        )
    return await run_python_code(
        code=code,
        test_cases=test_cases,
        custom_entrypoint=custom_entrypoint,
        timeout_sec=timeout_sec,
    )

"""Safe Python Code Execution Sandbox & Test Harness Runner.

Executes user code against test cases, capturing stdout, execution runtime,
and verifying expected output with AST introspection and timeout guards.
"""

from __future__ import annotations

import ast
import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
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


# Just enough environment to start an interpreter. User code runs with the
# backend's OS privileges, so it must not also inherit the backend's secrets
# (SECRET_KEY, DATABASE_URL, ...) for free.
_WORKER_ENV_KEYS = frozenset({
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC",
    "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL", "NODE_OPTIONS",
})

_PYTHON_WORKER = Path(__file__).with_name("code_sandbox_worker.py")
_NODE_WORKER = Path(__file__).with_name("ts_sandbox_worker.mjs")


def _worker_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k.upper() in _WORKER_ENV_KEYS}


def _failure(status: str, error: str, test_cases: list[dict], runtime_ms: float) -> dict[str, Any]:
    return {
        "status": status,
        "passed_count": 0,
        "total_count": len(test_cases),
        "runtime_ms": runtime_ms,
        "error": error,
        "results": [],
    }


async def _run_worker(
    cmd: list[str],
    code: str,
    test_cases: list[dict],
    test_code: str | None,
    custom_entrypoint: str | None,
    timeout_sec: float,
    spawn_error: str,
    invalid_output_error: str,
) -> dict[str, Any]:
    """Runs one worker process over a JSON payload on stdin.

    The worker gets a scrubbed environment and an empty scratch directory as
    its cwd, so neither ``os.environ`` nor a relative path like ``.env`` or
    ``dev.db`` reaches backend secrets. This is NOT a sandbox: the code still
    runs as the backend's OS user and can read any file that user can.
    """
    payload = json.dumps({
        "code": code,
        "test_code": test_code,
        "test_cases": test_cases,
        "custom_entrypoint": custom_entrypoint,
    }).encode("utf-8")

    total_start = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="code-run-", ignore_cleanup_errors=True) as workdir:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
                env=_worker_env(),
            )
        except Exception as e:
            return _failure("Runtime Error", f"{spawn_error}: {e}", test_cases, 0.0)

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
        return json.loads(stdout_bytes.decode("utf-8"))
    except Exception:
        err_msg = stderr_bytes.decode("utf-8", errors="replace").strip() or invalid_output_error
        return _failure(
            "Runtime Error",
            err_msg,
            test_cases,
            round((time.perf_counter() - total_start) * 1000.0, 2),
        )


async def run_python_code(
    code: str,
    test_cases: list[dict],
    test_code: str | None = None,
    custom_entrypoint: str | None = None,
    timeout_sec: float = 3.0,
) -> dict[str, Any]:
    """Executes Python code against a list of test cases in an isolated child subprocess."""
    # -I: ignore PYTHON* variables and keep the cwd/user site off sys.path. The
    # worker is stdlib-only, so it runs by path rather than as `-m app...`.
    return await _run_worker(
        [sys.executable, "-I", str(_PYTHON_WORKER)],
        code,
        test_cases,
        test_code,
        custom_entrypoint,
        timeout_sec,
        spawn_error="Failed to spawn execution worker",
        invalid_output_error="Execution worker returned invalid output.",
    )


async def run_node_code(
    code: str,
    test_cases: list[dict],
    test_code: str | None = None,
    custom_entrypoint: str | None = None,
    timeout_sec: float = 4.0,
) -> dict[str, Any]:
    """Executes TypeScript / JavaScript code against test cases using isolated Node.js worker."""
    node_bin = shutil.which("node") or shutil.which("node.exe") or r"C:\Program Files\nodejs\node.EXE"
    return await _run_worker(
        [node_bin, str(_NODE_WORKER)],
        code,
        test_cases,
        test_code,
        custom_entrypoint,
        timeout_sec,
        spawn_error="Failed to spawn Node execution worker (is Node.js installed?)",
        invalid_output_error="Node execution worker returned invalid output.",
    )


async def run_code(
    code: str,
    test_cases: list[dict],
    language: str = "python",
    test_code: str | None = None,
    custom_entrypoint: str | None = None,
    timeout_sec: float = 4.0,
) -> dict[str, Any]:
    """Universal sandbox runner supporting Python, TypeScript, and JavaScript."""
    lang = (language or "python").lower().strip()
    if lang in ("typescript", "javascript", "ts", "js"):
        return await run_node_code(
            code=code,
            test_cases=test_cases,
            test_code=test_code,
            custom_entrypoint=custom_entrypoint,
            timeout_sec=timeout_sec,
        )
    return await run_python_code(
        code=code,
        test_cases=test_cases,
        test_code=test_code,
        custom_entrypoint=custom_entrypoint,
        timeout_sec=timeout_sec,
    )

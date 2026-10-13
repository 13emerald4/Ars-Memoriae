"""Safe Python Code Execution Sandbox & Test Harness Runner.

Executes user code against test cases, capturing stdout, execution runtime,
and verifying expected output with AST introspection and timeout guards.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import weakref
from pathlib import Path
from typing import Any

# Just enough environment to start an interpreter. User code runs with the
# backend's OS privileges, so it must not also inherit the backend's secrets
# (SECRET_KEY, DATABASE_URL, ...) for free.
_WORKER_ENV_KEYS = frozenset({
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC",
    "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL", "NODE_OPTIONS",
})

_PYTHON_WORKER = Path(__file__).with_name("code_sandbox_worker.py")
_NODE_WORKER = Path(__file__).with_name("ts_sandbox_worker.mjs")

# Bounds on what one run can consume. Still NOT a sandbox (see _run_worker);
# these stop a runaway program from taking the whole machine with it.
MAX_CONCURRENT_RUNS = 2
MAX_OUTPUT_BYTES = 2 * 1024 * 1024
PYTHON_MEMORY_LIMIT_BYTES = 512 * 1024 * 1024

# One semaphore per event loop: a loop-bound primitive created at import time
# breaks as soon as a second loop (e.g. each test's) contends for it.
_run_slots: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = (
    weakref.WeakKeyDictionary()
)


def _worker_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k.upper() in _WORKER_ENV_KEYS}


def _slots() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    sem = _run_slots.get(loop)
    if sem is None:
        sem = _run_slots[loop] = asyncio.Semaphore(MAX_CONCURRENT_RUNS)
    return sem


def _posix_limits(cpu_seconds: int, memory_bytes: int | None):
    """preexec_fn for POSIX workers. Limits are inherited by anything the user
    code spawns. Each is best-effort: macOS rejects some, and a failure here
    must not stop the worker from starting."""
    import resource

    def apply() -> None:
        limits = [(resource.RLIMIT_CPU, cpu_seconds)]
        if memory_bytes is not None:
            limits.append((resource.RLIMIT_AS, memory_bytes))
        for which, value in limits:
            with contextlib.suppress(ValueError, OSError):
                resource.setrlimit(which, (value, value))

    return apply


def _kill_tree(proc: asyncio.subprocess.Process) -> None:
    """Kill the worker *and* anything it spawned; proc.kill() alone leaves
    grandchildren running after a timeout."""
    if proc.returncode is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            # The worker leads its own session (start_new_session), so its
            # process group is exactly the worker and its descendants.
            os.killpg(proc.pid, signal.SIGKILL)
    except OSError:
        pass
    with contextlib.suppress(ProcessLookupError):
        proc.kill()


class _OutputLimitExceeded(Exception):
    pass


async def _read_capped(
    stream: asyncio.StreamReader, limit: int, proc: asyncio.subprocess.Process
) -> bytes:
    """Read to EOF, killing the worker once output passes `limit`. Draining
    continues after the kill (discarding): until both pipes hit EOF, asyncio
    on Python 3.11 never completes proc.wait()."""
    buf = bytearray()
    over = False
    while chunk := await stream.read(65536):
        if over:
            continue
        buf += chunk
        if len(buf) > limit:
            over = True
            _kill_tree(proc)
    if over:
        raise _OutputLimitExceeded
    return bytes(buf)


async def _reap(proc: asyncio.subprocess.Process) -> None:
    """After a kill, drain both pipes and wait for exit (see _read_capped),
    giving up after a few seconds rather than hanging the request."""

    async def drain(stream: asyncio.StreamReader | None) -> None:
        while stream is not None and await stream.read(65536):
            pass

    with contextlib.suppress(Exception):
        await asyncio.wait_for(
            asyncio.gather(drain(proc.stdout), drain(proc.stderr), proc.wait()), timeout=5
        )


async def _communicate(proc: asyncio.subprocess.Process, payload: bytes) -> tuple[bytes, bytes]:
    assert proc.stdin and proc.stdout and proc.stderr
    try:
        proc.stdin.write(payload)
        await proc.stdin.drain()
    except (BrokenPipeError, ConnectionResetError):
        pass  # the worker exited early; its stderr says why
    finally:
        proc.stdin.close()
    readers = [
        asyncio.ensure_future(_read_capped(proc.stdout, MAX_OUTPUT_BYTES, proc)),
        asyncio.ensure_future(_read_capped(proc.stderr, MAX_OUTPUT_BYTES, proc)),
    ]
    try:
        out, err = await asyncio.gather(*readers)
    except BaseException:
        # Overflow or timeout: stop the readers so _reap can own the pipes.
        for r in readers:
            r.cancel()
        await asyncio.gather(*readers, return_exceptions=True)
        raise
    await proc.wait()
    return out, err


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
    memory_limit_bytes: int | None = None,
) -> dict[str, Any]:
    """Runs one worker process over a JSON payload on stdin.

    The worker gets a scrubbed environment and an empty scratch directory as
    its cwd, so neither ``os.environ`` nor a relative path like ``.env`` or
    ``dev.db`` reaches backend secrets. This is NOT a sandbox: the code still
    runs as the backend's OS user and can read any file that user can.

    At most MAX_CONCURRENT_RUNS workers run at once, output is capped at
    MAX_OUTPUT_BYTES, and a timeout kills the worker's whole process tree. On
    POSIX the worker also gets CPU-time and (Python only) address-space
    limits.
    """
    async with _slots():
        return await _run_worker_now(
            cmd,
            code,
            test_cases,
            test_code,
            custom_entrypoint,
            timeout_sec,
            spawn_error,
            invalid_output_error,
            memory_limit_bytes,
        )


async def _run_worker_now(
    cmd: list[str],
    code: str,
    test_cases: list[dict],
    test_code: str | None,
    custom_entrypoint: str | None,
    timeout_sec: float,
    spawn_error: str,
    invalid_output_error: str,
    memory_limit_bytes: int | None,
) -> dict[str, Any]:
    payload = json.dumps({
        "code": code,
        "test_code": test_code,
        "test_cases": test_cases,
        "custom_entrypoint": custom_entrypoint,
    }).encode("utf-8")

    total_start = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="code-run-", ignore_cleanup_errors=True) as workdir:
        posix: dict[str, Any] = {}
        if os.name != "nt":
            posix = {
                "start_new_session": True,
                "preexec_fn": _posix_limits(int(timeout_sec) + 1, memory_limit_bytes),
            }
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
                env=_worker_env(),
                **posix,
            )
        except Exception as e:
            return _failure("Runtime Error", f"{spawn_error}: {e}", test_cases, 0.0)

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                _communicate(proc, payload),
                timeout=timeout_sec,
            )
        except _OutputLimitExceeded:
            _kill_tree(proc)
            await _reap(proc)
            return _failure(
                "Output Limit Exceeded",
                f"Output Limit Exceeded (> {MAX_OUTPUT_BYTES // (1024 * 1024)} MB)",
                test_cases,
                round((time.perf_counter() - total_start) * 1000.0, 2),
            )
        except TimeoutError:
            _kill_tree(proc)
            await _reap(proc)
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
        memory_limit_bytes=PYTHON_MEMORY_LIMIT_BYTES,
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
        # V8 reserves far more address space than it uses, so Node gets a
        # heap cap instead of RLIMIT_AS.
        [node_bin, "--max-old-space-size=256", str(_NODE_WORKER)],
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

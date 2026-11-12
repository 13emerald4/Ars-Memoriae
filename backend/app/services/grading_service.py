"""LLM grading subsystem (§4) — local Ollama models and Antigravity subscription CLI (`agy`).

Ollama calls go to the local daemon at OLLAMA_BASE_URL; Antigravity calls invoke
the local `agy` CLI using your signed-in Antigravity subscription (no API key).

1. JSON output is requested (Ollama's ``format: "json"`` or ``agy --json-schema``)
   but still parsed tolerantly, since models wrap JSON in prose or code fences.
2. Every outbound call is wrapped so an unreachable daemon/CLI, an unavailable
   model, or a malformed response raises ``GradingUnavailable``, which the router
   turns into ``degraded_to_manual`` (§4.3) rather than a 500.
3. The model scores correctness 0-100 rather than picking a grade directly —
   that's the actual feedback the user sees and the LLM reasons about. The
   4-point grade FSRS schedules on is derived from the score
   (``grade_for_score``); it can't be scored away, since py-fsrs's
   stability/difficulty transitions are only defined per discrete rating.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.services.document_service import quote_is_grounded
from app.services.grading_profiles import (
    ALWAYS_ESCALATE,
    CARD_GEN_PROMPT,
    DOC_CARD_GEN_PROMPT,
    LEECH_PROMPT,
    LESSON_PROMPT,
    SOCRATIC_LINE_HINT_PROMPT,
    SOCRATIC_PROMPT,
    WEAKNESS_HINT_PROMPT,
    build_prompt,
)
from app.services.question_format_service import format_question_with_code_blocks

log = logging.getLogger(__name__)

SCORE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "score": {"type": "NUMBER"},
        "confidence": {"type": "NUMBER"},
        "matched_points": {"type": "ARRAY", "items": {"type": "STRING"}},
        "missed_points": {"type": "ARRAY", "items": {"type": "STRING"}},
        "overlooked_phrases": {"type": "ARRAY", "items": {"type": "STRING"}},
        "weaknesses": {"type": "ARRAY", "items": {"type": "STRING"}},
        "improvements": {"type": "ARRAY", "items": {"type": "STRING"}},
        "persistent_weaknesses": {"type": "ARRAY", "items": {"type": "STRING"}},
        "reasoning": {"type": "STRING"},
    },
    "required": ["score", "confidence", "reasoning"],
}

GRADES = ("again", "hard", "good", "easy")
# High to low so the first band a score clears wins; below all of these is
# "again". These mirror the scale described to the model in BASE_PROMPT.
SCORE_BANDS: tuple[tuple[float, str], ...] = ((90, "easy"), (70, "good"), (40, "hard"))
# Score points per grade step of accumulated calibration bias (apply_bias).
# Bands are 30-40 points wide, so 20 moves a mid-band score into the next one
# without letting a modest bias leapfrog two grades.
BIAS_SCORE_STEP = 20.0
# §Socratic AI Guide: how much of the reference answer's content words a
# guide message can echo before it counts as leaking the answer rather than
# hinting at it. The same overlap heuristic §4.3 uses to sanity-check grades.
SOCRATIC_LEAK_THRESHOLD = 0.75
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "in", "is", "it",
    "of", "on", "or", "that", "the", "to", "was", "were", "with",
}


class GradingUnavailable(RuntimeError):
    """Raised when grading cannot complete; callers degrade to manual (§4.3)."""


class VramExhaustedError(GradingUnavailable):
    """Raised when the local Ollama model ran out of GPU VRAM or host memory."""

    def __init__(
        self,
        message: str,
        failed_model: str,
        fallback_model: str | None = None,
        available_models: list[str] | None = None,
    ):
        super().__init__(message)
        self.failed_model = failed_model
        self.fallback_model = fallback_model
        self.available_models = available_models or []


def is_memory_or_vram_error(exc: Exception | str) -> bool:
    """Detects whether an Ollama error is caused by VRAM or host memory exhaustion."""
    parts: list[str] = []
    if isinstance(exc, str):
        parts.append(exc)
    else:
        parts.append(str(exc))
        resp = getattr(exc, "response", None)
        if resp is not None:
            with contextlib.suppress(Exception):
                parts.append(resp.text)
        cause = getattr(exc, "__cause__", None)
        if cause is not None:
            parts.append(str(cause))
            cause_resp = getattr(cause, "response", None)
            if cause_resp is not None:
                with contextlib.suppress(Exception):
                    parts.append(cause_resp.text)
    text = " ".join(parts).lower()
    return any(
        phrase in text
        for phrase in (
            "cudamalloc failed",
            "out of memory",
            "unable to allocate",
            "memory layout cannot be allocated",
            "cuda0 buffer",
            "cpu buffer",
            "exit status 2",
            "exit status 1",
            "panic: unable to load model",
            "exit status -1073741819",
            "llama runner process has terminated",
            "model runner has unexpectedly stopped",
            "unexpectedly stopped",
            "resource limitations or an internal error",
            "wsarecv",
            "connection was forcibly closed",
            "cuda error",
        )
    )


ALLOWED_QWEN_CODER_SIZES: tuple[str, ...] = ("7b", "3b", "1.5b")

ANTIGRAVITY_MODEL_PREFIX = "antigravity:"
ANTIGRAVITY_CATALOG: tuple[dict[str, str], ...] = (
    {
        "id": "antigravity:gemini-3.8-flash-low",
        "slug": "gemini-3.8-flash-low",
        "name": "Gemini 3.8 Flash (Low)",
        "tier": "Fast / Low Quota",
    },
    {
        "id": "antigravity:gemini-3.8-flash-medium",
        "slug": "gemini-3.8-flash-medium",
        "name": "Gemini 3.8 Flash (Medium)",
        "tier": "Balanced",
    },
    {
        "id": "antigravity:gemini-3.8-flash-high",
        "slug": "gemini-3.8-flash-high",
        "name": "Gemini 3.8 Flash (High)",
        "tier": "Deep Reasoning",
    },
    {
        "id": "antigravity:claude-sonnet-4-6",
        "slug": "claude-sonnet-4-6",
        "name": "Claude Sonnet 4.6 (Thinking)",
        "tier": "Coding & Prose",
    },
    {
        "id": "antigravity:claude-opus-4-6-thinking",
        "slug": "claude-opus-4-6-thinking",
        "name": "Claude Opus 4.6 (Thinking)",
        "tier": "Max Reasoning",
    },
    {
        "id": "antigravity:gpt-oss-120b-medium",
        "slug": "gpt-oss-120b-medium",
        "name": "GPT-OSS 120B (Medium)",
        "tier": "Open Weights",
    },
)
ANTIGRAVITY_KNOWN_SLUGS: frozenset[str] = frozenset(m["slug"] for m in ANTIGRAVITY_CATALOG)
_AGY_SLUG_RE = re.compile(r"^(?:gemini|claude|gpt-oss)-[a-z0-9._-]{1,64}$")
_AGY_MODELS_CACHE: tuple[float, list[str], str | None, str | None] | None = None


def is_allowed_qwen_coder_model(model_name: str | None) -> bool:
    """Returns True for the 3 approved local model archetypes:
    - Qwen 3.5 9B (The Heavy Generalist)
    - Qwen2.5-Coder 7B (The Technical Specialist)
    - Qwen 3.5 4B / Gemma 4 E4B (The Speed Demon)
    Also supports tag variants and backwards-compatible legacy fallback sizes.
    """
    if not model_name:
        return False
    m = model_name.lower().strip()
    # Never allow embeddings or rerankers
    if "embed" in m or "rerank" in m:
        return False
    # Model 1 & Model 3: Qwen 3.5 (9B The Heavy Generalist, 4B The Speed Demon)
    if "qwen3.5" in m or "qwen-3.5" in m:
        return bool(re.search(r"(^|[:\-_])(9b|4b)([:\-_]|$)", m))
    # Model 3: Gemma 4 E4B / Gemma models (The Speed Demon)
    if "gemma" in m:
        return bool(re.search(r"(^|[:\-_])(e4b|4b|2b|gemma4|gemma3|gemma2)([:\-_]|$)", m))
    # Model 2: Qwen 2.5 Coder 7B (The Technical Specialist), plus legacy 3B/1.5B
    if "qwen2.5-coder" in m:
        for size in ALLOWED_QWEN_CODER_SIZES:
            pattern = rf"(^|[:\-_]){re.escape(size)}([:\-_]|$)"
            if re.search(pattern, m):
                return True
    return False


def is_antigravity_model(model_name: str | None) -> bool:
    """Returns True when model_name selects an Antigravity CLI subscription model."""
    if not model_name:
        return False
    m = model_name.lower().strip()
    if not m.startswith(ANTIGRAVITY_MODEL_PREFIX):
        return False
    slug = m[len(ANTIGRAVITY_MODEL_PREFIX) :]
    return slug in ANTIGRAVITY_KNOWN_SLUGS or bool(_AGY_SLUG_RE.fullmatch(slug))


def strip_antigravity_prefix(model_name: str) -> str:
    """Converts `antigravity:<slug>` to the bare CLI `--model <slug>` string."""
    m = model_name.strip()
    if m.lower().startswith(ANTIGRAVITY_MODEL_PREFIX):
        return m[len(ANTIGRAVITY_MODEL_PREFIX) :].lower()
    return m


def is_allowed_grading_model(model_name: str | None) -> bool:
    """Returns True for approved local Ollama models and Antigravity subscription models."""
    return is_allowed_qwen_coder_model(model_name) or is_antigravity_model(model_name)


def validate_grading_model_name(model_name: str | None) -> str | None:
    """Shared Pydantic validator helper for user/request grading model selection."""
    if model_name is None:
        return None
    cleaned = model_name.strip()
    if not is_allowed_grading_model(cleaned):
        raise ValueError(
            f"Model '{model_name}' is not permitted. Choose an approved local model "
            "(Qwen 3.5 9B, Qwen2.5-Coder 7B, Qwen 3.5 4B / Gemma 4 E4B) or an "
            "Antigravity subscription model (antigravity:<slug>)."
        )
    return cleaned.lower() if is_antigravity_model(cleaned) else cleaned


def model_provider(model_name: str | None) -> str:
    """Returns 'antigravity' for subscription models, otherwise 'ollama'."""
    return "antigravity" if is_antigravity_model(model_name) else "ollama"


def is_antigravity_authorized(user: Any | None) -> bool:
    """True only when user's verified email is explicitly allowlisted to use host Antigravity subscription."""
    allowed = settings.antigravity_allowed_email_set
    if not allowed or user is None:
        return False
    email = (getattr(user, "email", None) or "").strip().lower()
    return bool(email) and email in allowed


def resolve_model(model_name: str | None, *, allow_antigravity: bool = False) -> str:
    """The requested model if permitted for this caller (Ollama or authorized Antigravity), else default."""
    if model_name:
        cleaned = model_name.strip()
        if is_allowed_qwen_coder_model(cleaned):
            return cleaned
        if allow_antigravity and is_antigravity_model(cleaned):
            return cleaned.lower()
    return settings.default_grading_model


def _to_standard_json_schema(schema: Any) -> Any:
    """Recursively lowers uppercase GenAI/Ollama JSON Schema types for standard JSON Schema."""
    if isinstance(schema, list):
        return [_to_standard_json_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    out: dict[str, Any] = {}
    for k, v in schema.items():
        if k == "type" and isinstance(v, str):
            out[k] = v.lower()
        else:
            out[k] = _to_standard_json_schema(v)
    return out


def resolve_antigravity_executable() -> str | None:
    """Locate the local `agy` CLI executable if installed."""
    configured = (settings.antigravity_cli_path or "agy").strip()
    found = shutil.which(configured)
    if found:
        return found
    candidate_path = Path(configured)
    if candidate_path.is_file():
        return str(candidate_path)
    win_default = Path.home() / "AppData" / "Local" / "agy" / "bin" / "agy.exe"
    if win_default.is_file():
        return str(win_default)
    return None


def _antigravity_sandbox_dir() -> Path:
    """Persistent empty working directory for headless `agy` calls.

    Reusing one empty directory avoids both repo context bloat and Windows
    WinError 32 failures when background child processes keep a handle on cwd.
    """
    sandbox = Path(tempfile.gettempdir()) / "ars_memoriae_agy"
    sandbox.mkdir(parents=True, exist_ok=True)
    return sandbox


def _parse_agy_models_output(raw_stdout: str) -> list[str]:
    models: list[str] = []
    seen: set[str] = set()
    for line in raw_stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        slug = line.split("\t", 1)[0].split(None, 1)[0].strip().lower()
        prefixed = f"{ANTIGRAVITY_MODEL_PREFIX}{slug}"
        if is_antigravity_model(prefixed) and prefixed not in seen:
            seen.add(prefixed)
            models.append(prefixed)
    return models


async def discover_antigravity_models(
    force_refresh: bool = False,
) -> tuple[list[str], str | None, str | None]:
    """Query `agy models` asynchronously using cached subscription credentials.

    Returns ``(models, cli_path, error_message)``. Positive results are cached
    briefly to avoid spawning subprocesses on every UI poll.
    """
    global _AGY_MODELS_CACHE
    now = time.monotonic()
    if not force_refresh and _AGY_MODELS_CACHE is not None:
        cached_at, cached_models, cached_cli, cached_err = _AGY_MODELS_CACHE
        if cached_models and (now - cached_at) < 60.0:
            return list(cached_models), cached_cli, cached_err

    cli_path = resolve_antigravity_executable()
    if not cli_path:
        return (
            [],
            None,
            "Antigravity CLI ('agy') was not found on PATH or in AppData\\Local\\agy\\bin\\agy.exe.",
        )

    proc: asyncio.subprocess.Process | None = None
    try:
        proc = await asyncio.create_subprocess_exec(
            cli_path,
            "models",
            cwd=str(_antigravity_sandbox_dir()),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=15.0)
        stdout = stdout_b.decode("utf-8", errors="replace")
        stderr = stderr_b.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            msg = stderr or stdout.strip() or f"agy models exited with code {proc.returncode}"
            return [], cli_path, msg
        models = _parse_agy_models_output(stdout)
        if not models:
            return [], cli_path, stderr or "No Antigravity models were returned by `agy models`."
        _AGY_MODELS_CACHE = (now, list(models), cli_path, None)
        return models, cli_path, None
    except TimeoutError:
        if proc is not None:
            with contextlib.suppress(ProcessLookupError, OSError):
                proc.kill()
        return (
            [],
            cli_path,
            "Timed out querying `agy models`. Run `agy` in a terminal once to confirm your Antigravity sign-in.",
        )
    except Exception as exc:
        return [], cli_path, f"Failed to run `agy models`: {exc}"


async def find_local_fallback_models(
    base_url: str,
    current_model: str,
) -> tuple[str | None, list[str]]:
    """Returns (next_biggest_model, all_smaller_models) from installed local Ollama models.
    Strictly restricted to allowed quantized Qwen 2.5 Coder models (7B, 3B, 1.5B).
    """
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code != 200:
                return None, []
            data = resp.json()
            models = data.get("models", [])
    except Exception as exc:
        log.warning("Could not query Ollama tags: %s", exc)
        return None, []

    installed: list[dict[str, Any]] = []
    for m in models:
        name = m.get("name", "")
        if not is_allowed_qwen_coder_model(name):
            continue
        size = m.get("size", 0)
        installed.append({"name": name, "size": size})

    # Sort descending by size (e.g. 7B -> 3B -> 1.5B)
    installed.sort(key=lambda x: x["size"], reverse=True)

    current_size = None
    for m in installed:
        if m["name"] == current_model:
            current_size = m["size"]
            break

    smaller: list[str] = []
    for m in installed:
        if m["name"] == current_model:
            continue
        if (current_size is not None and m["size"] < current_size) or (current_size is None and m["name"] != current_model):
            smaller.append(m["name"])

    if not smaller:
        return None, []

    next_biggest = smaller[0]
    return next_biggest, smaller


UNICODE_PROMPT_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("→", "->"),
    ("←", "<-"),
    ("⇒", "=>"),
    ("⇐", "<="),
    ("↔", "<->"),
    ("—", "--"),
    ("–", "-"),  # noqa: RUF001
    ("“", '"'),
    ("”", '"'),
    ("‘", "'"),  # noqa: RUF001
    ("’", "'"),  # noqa: RUF001
    ("…", "..."),
    ("•", "*"),
    ("≤", "<="),
    ("≥", ">="),
    ("≠", "!="),
    ("≈", "~="),
)


def sanitize_prompt_for_ollama(text: str) -> str:
    """Normalizes Unicode characters that can cause Ollama's model runner on Windows to crash."""
    if not text:
        return text
    for old, new in UNICODE_PROMPT_REPLACEMENTS:
        text = text.replace(old, new)
    return text


class GradingService:
    def __init__(
        self,
        model: str | None = None,
        escalation_model: str | None = None,
        base_url: str | None = None,
        *,
        allow_antigravity: bool = False,
    ) -> None:
        self.allow_antigravity = allow_antigravity
        self.model = resolve_model(model, allow_antigravity=allow_antigravity)
        self.escalation_model = escalation_model or settings.escalation_grading_model
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.last_used_model: str | None = None

    @classmethod
    def for_user(
        cls,
        user: Any | None,
        requested_model: str | None = None,
        *,
        escalation_model: str | None = None,
        base_url: str | None = None,
    ) -> GradingService:
        """Build a GradingService scoped to `user`'s Antigravity authorization."""
        authorized = is_antigravity_authorized(user)
        if requested_model and is_antigravity_model(requested_model) and not authorized:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Antigravity subscription models are only available for authorized owner accounts.",
            )
        candidate = requested_model or getattr(user, "grading_model", None)
        resolved = resolve_model(candidate, allow_antigravity=authorized)
        resolved_escalation = (
            resolve_model(escalation_model, allow_antigravity=authorized)
            if escalation_model is not None
            else resolved
        )
        return cls(
            model=resolved,
            escalation_model=resolved_escalation,
            base_url=base_url,
            allow_antigravity=authorized,
        )

    # ── transport ───────────────────────────────────────────────────────────

    async def _generate_ollama(
        self,
        prompt: str,
        model: str,
        schema: dict | None = None,
        **kwargs: Any,
    ) -> str:
        num_ctx = kwargs.get("num_ctx") or settings.ollama_num_ctx
        keep_alive = kwargs.get("keep_alive") or settings.ollama_keep_alive
        payload: dict[str, Any] = {
            "model": model,
            "prompt": sanitize_prompt_for_ollama(prompt),
            "stream": False,
            "keep_alive": keep_alive,
            "options": {
                # Ollama silently drops the *start* of an over-long prompt —
                # the instructions — so this must fit the longest prompt.
                "num_ctx": num_ctx,
                # Greedy decoding on every call: Ollama's default temperature
                # samples, so the same answer could get a different grade.
                "temperature": 0,
            },
        }
        if schema is not None or kwargs.get("response_schema") is not None:
            payload["format"] = "json"

        last_exc = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/api/generate",
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    self.last_used_model = model
                    return data.get("response", "")
            except httpx.ConnectError as exc:
                raise GradingUnavailable(
                    f"Could not connect to Ollama at {self.base_url}. Make sure Ollama is running (`ollama run {model}`)."
                ) from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    raise GradingUnavailable(
                        f"Model '{model}' not found in Ollama. Run: ollama pull {model}"
                    ) from exc
                err_detail = ""
                try:
                    err_body = exc.response.json()
                    err_detail = err_body.get("error") or exc.response.text
                except Exception:
                    err_detail = exc.response.text

                # If this is a VRAM / out of memory error, don't sleep & retry the exact same failing model
                if is_memory_or_vram_error(err_detail or exc):
                    raise GradingUnavailable(f"Ollama generation failed: {err_detail or exc}") from exc

                last_exc = exc
                await asyncio.sleep(0.5 * (attempt + 1))
            except Exception as exc:
                if is_memory_or_vram_error(exc):
                    raise
                last_exc = exc
                await asyncio.sleep(0.5 * (attempt + 1))

        if last_exc:
            detail = str(last_exc)
            if isinstance(last_exc, httpx.HTTPStatusError):
                try:
                    detail = last_exc.response.json().get("error", last_exc.response.text)
                except Exception:
                    detail = last_exc.response.text or str(last_exc)
            raise GradingUnavailable(f"Ollama generation failed: {detail}") from last_exc
        return ""

    async def _generate_antigravity(
        self,
        prompt: str,
        model: str,
        schema: dict | None = None,
        **kwargs: Any,
    ) -> str:
        """Invoke the local `agy` CLI in non-interactive print mode on the user's subscription."""
        if not self.allow_antigravity:
            raise GradingUnavailable("Antigravity subscription is not authorized for this account.")
        exe = resolve_antigravity_executable()
        if not exe:
            raise GradingUnavailable(
                "Antigravity CLI ('agy') was not found. Install Antigravity CLI and run `agy` once to sign in."
            )

        timeout_sec = max(15.0, float(kwargs.get("timeout_seconds") or settings.antigravity_timeout_seconds))
        cli_slug = strip_antigravity_prefix(model)
        raw_schema = schema or kwargs.get("response_schema")
        norm_schema = _to_standard_json_schema(raw_schema) if isinstance(raw_schema, dict) else None

        preamble = (
            "Respond directly using only the prompt below. "
            "Do not inspect workspace files or run terminal commands.\n\n"
        )
        full_prompt = f"{preamble}{sanitize_prompt_for_ollama(prompt)}"
        # Guard against Windows CreateProcess 32k command-line limits on giant passages.
        if len(full_prompt) > 28000:
            full_prompt = full_prompt[:28000]

        cmd: list[str] = [
            exe,
            "-p",
            full_prompt,
            "--model",
            cli_slug,
            "--output-format",
            "json",
            "--disable-slash-commands",
            "--print-timeout",
            f"{int(timeout_sec)}s",
        ]
        if norm_schema is not None:
            cmd.extend(["--json-schema", json.dumps(norm_schema, separators=(",", ":"))])

        proc: asyncio.subprocess.Process | None = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(_antigravity_sandbox_dir()),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_sec + 10.0,
            )
        except asyncio.CancelledError:
            if proc is not None and proc.returncode is None:
                with contextlib.suppress(ProcessLookupError, OSError):
                    proc.kill()
            raise
        except TimeoutError as exc:
            if proc is not None and proc.returncode is None:
                with contextlib.suppress(ProcessLookupError, OSError):
                    proc.kill()
            raise GradingUnavailable(
                f"Antigravity CLI timed out after {int(timeout_sec)}s on '{cli_slug}'."
            ) from exc
        except OSError as exc:
            raise GradingUnavailable(f"Failed to launch Antigravity CLI ('{exe}'): {exc}") from exc

        stdout = stdout_b.decode("utf-8", errors="replace").strip()
        stderr = stderr_b.decode("utf-8", errors="replace").strip()

        envelope: dict[str, Any] | None = None
        for line in reversed(stdout.splitlines()):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                candidate = json.loads(line)
                if isinstance(candidate, dict) and ("status" in candidate or "response" in candidate):
                    envelope = candidate
                    break
            except json.JSONDecodeError:
                continue

        if envelope is None and stdout:
            try:
                candidate = json.loads(stdout)
                if isinstance(candidate, dict):
                    envelope = candidate
            except json.JSONDecodeError:
                envelope = None

        if proc.returncode != 0 or (envelope is not None and envelope.get("status") != "SUCCESS"):
            err_msg = (
                (envelope.get("error") if isinstance(envelope, dict) else None)
                or stderr
                or stdout
                or f"agy exited with code {proc.returncode}"
            )
            lowered = str(err_msg).lower()
            if any(tok in lowered for tok in ("auth", "login", "sign in", "credential", "unauthenticated")):
                raise GradingUnavailable(
                    f"Antigravity CLI requires sign-in ({err_msg}). Run `agy` in a terminal once with your Antigravity subscription."
                )
            raise GradingUnavailable(f"Antigravity CLI generation failed: {err_msg}")

        self.last_used_model = model
        if envelope is not None:
            if norm_schema is not None and isinstance(envelope.get("structured_output"), (dict, list)):
                return json.dumps(envelope["structured_output"])
            return str(envelope.get("response") or "")
        return stdout

    async def _call_ollama(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        """Compatibility helper for two-part (system, user) callers; routes via _generate."""
        combined = f"{system_prompt.strip()}\n\n{user_prompt.strip()}" if system_prompt else user_prompt
        return await self._generate(combined, model=self.model, **kwargs)

    async def _generate(
        self,
        prompt: str,
        model: str | None = None,
        schema: dict | None = None,
        thinking_budget: int | None = None,
        allow_smaller_model: bool = False,
        **kwargs: Any,
    ) -> str:
        target_model = resolve_model(model or self.model, allow_antigravity=self.allow_antigravity)
        self.last_used_model = target_model
        active_schema = schema or kwargs.get("response_schema")
        if is_antigravity_model(target_model):
            return await self._generate_antigravity(
                prompt,
                model=target_model,
                schema=active_schema,
                **kwargs,
            )
        try:
            return await self._generate_ollama(
                prompt,
                model=target_model,
                schema=active_schema,
                **kwargs,
            )
        except Exception as exc:
            # Check if this failure is caused by VRAM or host memory exhaustion
            if is_memory_or_vram_error(exc):
                next_model, smaller_models = await find_local_fallback_models(self.base_url, target_model)
                log.warning(
                    "Ollama model '%s' hit VRAM/memory limit (%s). Fallback model: %s, all smaller: %s",
                    target_model,
                    exc,
                    next_model,
                    smaller_models,
                )
                if allow_smaller_model and next_model:
                    log.info("Auto-falling back to next biggest local model: %s", next_model)
                    self.last_used_model = next_model
                    return await self._generate_ollama(
                        prompt,
                        model=next_model,
                        schema=active_schema,
                        **kwargs,
                    )
                else:
                    clean_msg = str(exc)
                    if hasattr(exc, "__cause__") and exc.__cause__:
                        cause_str = str(exc.__cause__)
                        if "cudaMalloc failed" in cause_str or "out of memory" in cause_str:
                            clean_msg = cause_str
                    raise VramExhaustedError(
                        message=f"Local model '{target_model}' ran out of GPU VRAM / host memory: {clean_msg}",
                        failed_model=target_model,
                        fallback_model=next_model,
                        available_models=smaller_models,
                    ) from exc
            raise

    # ── grading (§4.1) ──────────────────────────────────────────────────────

    async def grade(
        self,
        front: str,
        back: str,
        user_answer: str,
        profile: str = "short_answer",
        card_type: str = "basic",
        test_code: str | None = None,
        previous_weaknesses: list[str] | None = None,
        model: str | None = None,
        allow_smaller_model: bool = False,
        num_ctx: int | None = None,
        execution_summary: str | None = None,
    ) -> dict:
        prompt = build_prompt(
            profile,
            front=front,
            back=back,
            user_answer=user_answer,
            card_type=card_type,
            test_code=test_code,
            previous_weaknesses=previous_weaknesses,
            execution_summary=execution_summary,
        )
        target_model = model or self.model
        extra_kwargs: dict[str, Any] = {}
        if num_ctx is not None:
            extra_kwargs["num_ctx"] = num_ctx
        if allow_smaller_model:
            raw = await self._generate(prompt, target_model, SCORE_SCHEMA, allow_smaller_model=True, **extra_kwargs)
        else:
            raw = await self._generate(prompt, target_model, SCORE_SCHEMA, **extra_kwargs)
        return _normalize_result(parse_json(raw))

    async def grade_with_escalation(
        self,
        front: str,
        back: str,
        user_answer: str,
        profile: str = "short_answer",
        card_type: str = "basic",
        test_code: str | None = None,
        previous_weaknesses: list[str] | None = None,
        model: str | None = None,
        allow_smaller_model: bool = False,
        force_escalate: bool = False,
        num_ctx: int | None = None,
        execution_summary: str | None = None,
    ) -> dict:
        """§4.2 escalation: a disputed card or a math/code profile goes straight
        to the escalation model; a low-confidence grade is retried on it.

        A no-op when the escalation model is the grading model (the default),
        or when an Antigravity subscription model is explicitly chosen (never
        falls down to local Ollama on code/math profiles). If the escalation
        model isn't pulled, the grading model's answer is kept rather than lost.
        """
        primary_model = model or self.model

        async def grade_on(m: str) -> dict:
            result = await self.grade(
                front,
                back,
                user_answer,
                profile,
                card_type,
                test_code=test_code,
                previous_weaknesses=previous_weaknesses,
                model=m,
                allow_smaller_model=allow_smaller_model,
                num_ctx=num_ctx,
                execution_summary=execution_summary,
            )
            result["model_used"] = self.last_used_model or m
            result["escalated"] = m != primary_model
            return result

        can_escalate = (not is_antigravity_model(primary_model)) and (self.escalation_model != primary_model)
        if can_escalate and (force_escalate or profile in ALWAYS_ESCALATE):
            return await grade_on(self.escalation_model)

        result = await grade_on(primary_model)
        if can_escalate and result["confidence"] < settings.grading_confidence_threshold:
            return await grade_on(self.escalation_model)
        return result

    # ── IR card generation (§8.3) — reuses this same client ─────────────────

    async def generate_cards(
        self,
        passage: str,
        max_cards: int = 5,
        model: str | None = None,
        thinking_budget: int | None = None,
    ) -> list[dict]:
        raw = await self._generate(
            CARD_GEN_PROMPT.format(passage=passage[:8000], max_cards=max_cards),
            model or self.model,
            thinking_budget=thinking_budget,
        )
        data = parse_json(raw)
        cards = data.get("cards") if isinstance(data, dict) else None
        if not isinstance(cards, list):
            raise GradingUnavailable("card generation returned no cards")
        out = [_normalize_generated_card(c) for c in cards[:max_cards] if isinstance(c, dict)]
        return [c for c in out if c["front"] or c["cloze_text"]]

    async def generate_cards_with_citations(
        self,
        passage: str,
        locator: str,
        max_cards: int = 5,
        model: str | None = None,
        thinking_budget: int | None = None,
    ) -> list[dict]:
        """Cards from a document passage, each carrying the span it came from.

        The quote is *checked* against the passage rather than trusted: a
        citation the reader can't find in the source is worse than none, so an
        ungrounded quote is kept but flagged, and the UI falls back to showing
        the real passage instead of a sentence the model may have invented.
        """
        raw = await self._generate(
            DOC_CARD_GEN_PROMPT.format(
                passage=passage[:8000], max_cards=max_cards, locator=locator or "this document"
            ),
            model or self.model,
            thinking_budget=thinking_budget,
        )
        data = parse_json(raw)
        cards = data.get("cards") if isinstance(data, dict) else None
        if not isinstance(cards, list):
            raise GradingUnavailable("card generation returned no cards")

        out = []
        for c in cards[:max_cards]:
            if not isinstance(c, dict):
                continue
            item = _normalize_generated_card(c)
            quote = str(c.get("quote", "")).strip()
            item["quote"] = quote
            item["quote_verified"] = quote_is_grounded(quote, passage)
            item["locator"] = locator
            out.append(item)
        return [c for c in out if c["front"] or c["cloze_text"]]

    # ── Learn & Practice lessons ────────────────────────────────────────────

    async def generate_lesson(
        self,
        front: str,
        back: str,
        passages: list[str],
        max_words: int = 160,
        model: str | None = None,
    ) -> dict:
        """A short lesson teaching the idea a card tests, from its citations.

        Grounded the same way card generation is: the passages are the only
        permitted source. Teaching material that quietly invents an
        explanation is worse than none, because the user has no reason to
        doubt it — they are reading it precisely because they don't know the
        material yet.
        """
        if not passages:
            raise GradingUnavailable("no source passages to teach from")
        joined = "\n\n---\n\n".join(p.strip() for p in passages if p and p.strip())[:8000]
        raw = await self._generate(
            LESSON_PROMPT.format(
                front=front, back=back, passages=joined, max_words=max_words
            ),
            model or self.model,
        )
        data = parse_json(raw)
        lesson = str(data.get("lesson", "")).strip() if isinstance(data, dict) else ""
        if not lesson:
            raise GradingUnavailable("lesson generation returned nothing")
        points = data.get("key_points") or []
        return {
            "lesson": lesson,
            "key_points": [str(p).strip() for p in points if str(p).strip()][:6],
        }

    # ── Socratic AI Guide & Targeted Weakness Hint ───────────────────────────

    async def generate_weakness_hint(
        self,
        front: str,
        back: str,
        active_weaknesses: list[str],
        model: str | None = None,
        allow_smaller_model: bool = True,
    ) -> dict:
        """Generates a targeted diagnostic hint based on prior recorded weaknesses."""
        if not active_weaknesses:
            return {
                "hint": "No prior weaknesses recorded for this card. Focus on recalling the core principles and key definitions.",
                "has_past_weaknesses": False,
            }

        weaknesses_text = "\n".join(f"- {w}" for w in active_weaknesses[:8])
        raw = await self._generate(
            WEAKNESS_HINT_PROMPT.format(
                front=front,
                back=back,
                weaknesses_text=weaknesses_text,
            ),
            model or self.model,
            schema={"type": "OBJECT", "properties": {"hint": {"type": "STRING"}}, "required": ["hint"]},
            allow_smaller_model=allow_smaller_model,
        )
        data = parse_json(raw)
        hint = str(data.get("hint", "")).strip() if isinstance(data, dict) else ""
        if not hint:
            hint = f"Focus on avoiding your past stumbling blocks: {', '.join(active_weaknesses[:2])}."

        if leaks_reference_answer(back, hint):
            log.warning("weakness hint leaked reference answer; substituting generic reminder")
            hint = f"Keep in mind your previous difficulty with: {active_weaknesses[0]}."

        return {
            "hint": hint,
            "has_past_weaknesses": True,
        }

    @staticmethod
    def _format_work_section(
        user_code: str | None = None,
        test_code: str | None = None,
        execution_summary: str | None = None,
    ) -> str:
        parts: list[str] = []
        if user_code and user_code.strip():
            parts.append(f"Student's current implementation draft:\n```\n{user_code.strip()[:4500]}\n```")
        if test_code and test_code.strip():
            parts.append(f"Student's current unit tests:\n```\n{test_code.strip()[:3000]}\n```")
        if execution_summary and execution_summary.strip():
            parts.append(f"Latest test / runtime output:\n{execution_summary.strip()[:2500]}")
        return ("\n" + "\n\n".join(parts) + "\n") if parts else "\n"

    async def ask_socratic_question(
        self,
        front: str,
        back: str,
        history: list[tuple[str, str]],
        latest: str,
        active_weaknesses: list[str] | None = None,
        model: str | None = None,
        allow_smaller_model: bool = True,
        user_code: str | None = None,
        test_code: str | None = None,
        execution_summary: str | None = None,
    ) -> dict:
        """One turn of Socratic hinting: a diagnostic question, never the answer.

        The prompt is the first line of defense — instructed never to reveal
        ``back`` — but prompts are not guarantees, so the reply is also
        checked the same way §4.3 cross-checks a grade: if it echoes most of
        the reference answer's content words, it's swapped for a generic
        nudge rather than trusted and shown.
        """
        weakness_intro = ""
        if active_weaknesses:
            weakness_intro = (
                f"[Tutor note: The student had previous difficulty on this card with: "
                f"{'; '.join(active_weaknesses[:4])}]\n"
            )

        convo = "\n".join(
            f"{'Guide' if role == 'guide' else 'Student'}: {text}" for role, text in history[-12:]
        )
        full_convo = f"{weakness_intro}{convo}" if weakness_intro else convo
        work_section = self._format_work_section(
            user_code=user_code,
            test_code=test_code,
            execution_summary=execution_summary,
        )
        raw = await self._generate(
            SOCRATIC_PROMPT.format(
                front=front,
                back=back,
                work_section=work_section,
                history=full_convo or "(none yet)",
                latest=latest.strip() or "(the student hasn't replied yet — ask an opening question)",
            ),
            model or self.model,
            allow_smaller_model=allow_smaller_model,
        )
        data = parse_json(raw)
        message = str(data.get("message", "")).strip() if isinstance(data, dict) else ""
        if not message:
            raise GradingUnavailable("guide returned no message")

        if leaks_reference_answer(back, message):
            log.warning("socratic guide reply echoed the reference answer; substituting a nudge")
            message = "Let's hold off on the full answer — what part of it are you already sure of?"

        return {"message": message, "on_track": bool(isinstance(data, dict) and data.get("on_track"))}

    async def ask_socratic_line_hint(
        self,
        front: str,
        back: str,
        code: str,
        line_number: int,
        language: str = "typescript",
        model: str | None = None,
        allow_smaller_model: bool = True,
        test_code: str | None = None,
        execution_summary: str | None = None,
    ) -> dict:
        """Generates a targeted Socratic hint for a specific line of code in the IDE.

        Grounded in the canonical reference solution (``back``) and the student's
        preceding code, without ever leaking the actual line or solution verbatim.
        """
        lines = code.split("\n")
        total_lines = len(lines)
        clamped_line = max(1, min(line_number, max(1, total_lines)))

        current_line_text = lines[clamped_line - 1] if clamped_line <= total_lines else ""
        code_before = "\n".join(lines[: clamped_line - 1]) or "(no preceding code)"

        code_with_lines = "\n".join(
            f"{'--> ' if i + 1 == clamped_line else '    '}{i + 1}: {line}"
            for i, line in enumerate(lines)
        )
        work_section = self._format_work_section(
            test_code=test_code,
            execution_summary=execution_summary,
        )

        raw = await self._generate(
            SOCRATIC_LINE_HINT_PROMPT.format(
                front=front,
                back=back,
                code_with_lines=code_with_lines,
                line_number=clamped_line,
                current_line_text=current_line_text or "(empty / cursor here)",
                code_before=code_before,
                work_section=work_section,
            ),
            model or self.model,
            allow_smaller_model=allow_smaller_model,
        )
        data = parse_json(raw)
        hint = str(data.get("hint", "")).strip() if isinstance(data, dict) else ""
        target_concept = str(data.get("target_concept", "")).strip() if isinstance(data, dict) else None

        if not hint:
            raise GradingUnavailable("Guide returned no hint for this line")

        def _leaks_code_line(reference_solution: str, text: str) -> bool:
            if leaks_reference_answer(reference_solution, text):
                return True
            for ref_line in reference_solution.split("\n"):
                stripped_line = ref_line.strip()
                if len(stripped_line) >= 6 and stripped_line in text:
                    return True
            return False

        if _leaks_code_line(back, hint):
            log.warning("Socratic line hint echoed reference answer code; substituting a pedagogical nudge")
            hint = f"Focus on line {clamped_line}: consider what operation or state change connects your previous setup to the expected return type."

        return {
            "hint": hint,
            "target_concept": target_concept,
            "line_number": clamped_line,
            "current_line_text": current_line_text,
        }

    # ── leech remediation (§3.2) ────────────────────────────────────────────

    async def suggest_leech_remediation(
        self, front: str, back: str, lapses: int, failed_answers: list[str]
    ) -> dict:
        answers = "\n".join(f"- {a}" for a in failed_answers[:8]) or "- (none recorded)"
        target_model = self.model
        raw = await self._generate(
            LEECH_PROMPT.format(front=front, back=back, lapses=lapses, failed_answers=answers),
            target_model,
        )
        data = parse_json(raw)
        kind = data.get("kind") if isinstance(data, dict) else None
        if kind not in ("rewrite", "split", "ambiguous"):
            kind = "ambiguous"
        cards = data.get("cards") if isinstance(data, dict) else []
        return {
            "kind": kind,
            "rationale": str(data.get("rationale", "")).strip() if isinstance(data, dict) else "",
            "cards": [c for c in (cards or []) if isinstance(c, dict)],
        }

    async def decompose_card_atomicity(self, front: str, back: str) -> list[dict[str, str]]:
        """Decomposes a complex, non-atomic card into 2-4 atomic question-answer pairs."""
        prompt = (
            "You are a cognitive science and spaced repetition expert specializing in the "
            "Minimum Information Principle (Rule of Atomicity).\n"
            "The user has a flashcard that is too complex, lengthy, or tests multiple facts at once.\n"
            "Deconstruct it into 2 to 4 simple, concise, and atomic flashcards. Each card must test exactly "
            "ONE fact with a clear, concise question and a short, direct answer (under 15 words).\n\n"
            f"Original Card Prompt:\n{front}\n\n"
            f"Original Card Answer:\n{back}\n\n"
            "Output JSON with a 'cards' array of objects with 'front' and 'back' fields."
        )
        schema = {
            "type": "OBJECT",
            "properties": {
                "cards": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "front": {"type": "STRING"},
                            "back": {"type": "STRING"},
                        },
                        "required": ["front", "back"],
                    },
                }
            },
            "required": ["cards"],
        }
        raw = await self._generate(prompt, self.model, response_schema=schema)
        data = parse_json(raw)
        cards = data.get("cards") if isinstance(data, dict) else []
        out = []
        for c in cards:
            if isinstance(c, dict) and c.get("front") and c.get("back"):
                out.append({"front": str(c["front"]).strip(), "back": str(c["back"]).strip()})
        return out

    async def _verify_ollama(self) -> list[str]:
        """Confirm Ollama daemon is reachable and list downloaded models."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                models = [
                    m.get("name", "")
                    for m in data.get("models", [])
                    if m.get("name") and is_allowed_qwen_coder_model(m.get("name"))
                ]
                return sorted(models)
            except Exception as exc:
                raise GradingUnavailable(
                    f"Could not connect to Ollama at {self.base_url} ({exc}). Is Ollama running?"
                ) from exc

    async def verify_engine(self) -> list[str]:
        """Confirm the active LLM engine (Antigravity CLI or local Ollama) is ready."""
        if is_antigravity_model(self.model):
            if not self.allow_antigravity:
                raise GradingUnavailable("Antigravity subscription is not authorized for this account.")
            models, _cli, err = await discover_antigravity_models()
            if err or not models:
                raise GradingUnavailable(err or "Antigravity CLI is not available.")
            return models
        return await self._verify_ollama()

    async def verify_all_engines(self) -> dict[str, Any]:
        """Concurrently inspect available LLM engines (Antigravity only when authorized)."""
        async def _check_ollama() -> tuple[list[str], str | None]:
            try:
                return await self._verify_ollama(), None
            except Exception as exc:
                return [], str(exc)

        if self.allow_antigravity:
            (ollama_models, ollama_err), (agy_models, agy_cli, agy_err) = await asyncio.gather(
                _check_ollama(),
                discover_antigravity_models(),
            )
            agy_payload = {
                "authorized": True,
                "connected": agy_err is None and len(agy_models) > 0,
                "installed": agy_cli is not None,
                "cli_path": agy_cli,
                "models": agy_models,
                "catalog": list(ANTIGRAVITY_CATALOG),
                "error": agy_err,
            }
        else:
            ollama_models, ollama_err = await _check_ollama()
            agy_payload = {
                "authorized": False,
                "connected": False,
                "installed": False,
                "cli_path": None,
                "models": [],
                "catalog": [],
                "error": None,
            }

        return {
            "ollama": {
                "connected": ollama_err is None,
                "base_url": self.base_url,
                "models": ollama_models,
                "error": ollama_err,
            },
            "antigravity": agy_payload,
        }


# ── parsing & sanity checks ─────────────────────────────────────────────────


def _normalize_generated_card(c: dict) -> dict:
    """One model-proposed card, coerced to the shape the accept endpoints take."""
    is_cloze = c.get("kind") == "cloze" and bool(c.get("cloze_text"))
    is_code = c.get("kind") == "code" or bool(c.get("starter_code")) or bool(c.get("starter_tests"))
    image = str(c.get("image") or c.get("image_url") or c.get("picture") or "").strip() or None
    raw_front = str(c.get("front", "")).strip()
    starter_code = c.get("starter_code")
    lang = c.get("language")
    item = {
        "kind": "cloze" if is_cloze else ("code" if is_code else "qa"),
        "front": format_question_with_code_blocks(
            raw_front,
            starter_code=starter_code,
            language=lang,
        ),
        "back": str(c.get("back", "")).strip(),
        "cloze_text": str(c.get("cloze_text", "")).strip() or None,
    }
    if image:
        item["image"] = image
    if is_code:
        item["title"] = c.get("title")
        item["starter_code"] = c.get("starter_code")
        item["starter_tests"] = c.get("starter_tests")
        item["test_cases"] = c.get("test_cases") or []
    return item


def parse_json(raw: str) -> dict:
    """Tolerant JSON extraction — models wrap output in prose, think blocks, or code fences
    when structured output isn't enforced by the schema path."""
    if not raw:
        raise GradingUnavailable("empty response")
    text = raw.strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise GradingUnavailable("unparseable grading response")


def grade_for_score(score: float) -> str:
    """Bucket a 0-100 correctness score into the 4-point scale FSRS's
    scheduling math is defined over (§4.1). The score is what the user sees
    and what grading reasons about; FSRS still needs one of Again/Hard/Good/
    Easy, since stability/difficulty transitions are only defined per rating —
    that's py-fsrs's API, not a choice this app can route around.
    """
    for threshold, grade in SCORE_BANDS:
        if score >= threshold:
            return grade
    return "again"


def parse_score(raw) -> int:
    """A 0-100 integer from whatever shape the model returned it in.

    Rounded to an integer *before* bucketing, because the UI renders the score
    rounded: a raw 89.6 displayed as "90%" while bucketed as "good" (70-89)
    would contradict the band the user is reading. One integer decides both.

    A trailing "%" is tolerated — models write "85%" often enough that letting
    it collapse the whole grading call into the manual fallback would be a
    silly way to lose an otherwise good response.
    """
    if isinstance(raw, str):
        raw = raw.strip().rstrip("%").strip()
    try:
        score = float(raw)
    except (TypeError, ValueError):
        raise GradingUnavailable(f"invalid score {raw!r}") from None
    return round(min(max(score, 0.0), 100.0))


def _normalize_result(data: dict) -> dict:
    if "score" not in data:
        raise GradingUnavailable("response missing score")
    score = parse_score(data["score"])
    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    return {
        "score": score,
        "grade": grade_for_score(score),
        "confidence": min(max(confidence, 0.0), 1.0),
        "matched_points": [str(x).strip() for x in (data.get("matched_points") or []) if str(x).strip()][:12],
        "missed_points": [str(x).strip() for x in (data.get("missed_points") or []) if str(x).strip()][:12],
        "overlooked_phrases": [str(x).strip() for x in (data.get("overlooked_phrases") or []) if str(x).strip()][:12],
        "weaknesses": [str(x).strip() for x in (data.get("weaknesses") or []) if str(x).strip()][:12],
        "improvements": [str(x).strip() for x in (data.get("improvements") or []) if str(x).strip()][:12],
        "persistent_weaknesses": [str(x).strip() for x in (data.get("persistent_weaknesses") or []) if str(x).strip()][:12],
        "reasoning": str(data.get("reasoning", "")).strip(),
    }


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS and len(w) > 2}


def heuristic_overlap(reference: str, answer: str) -> float:
    """Cheap keyword-overlap check that runs alongside the LLM call (§4.3):
    the fraction of the reference answer's content words the user reproduced."""
    ref, ans = _tokens(reference), _tokens(answer)
    if not ref:
        return 1.0 if ans else 0.0
    return len(ref & ans) / len(ref)


def leaks_reference_answer(back: str, message: str) -> bool:
    """Whether a Socratic Guide message gives the reference answer away.

    Two checks, because neither alone covers the range of answers:

    **Verbatim containment** is what catches short answers. ``_tokens`` drops
    anything under three characters, so a reference of "4" or "pH" reduces to
    an *empty* token set — and ``heuristic_overlap`` reports an empty
    reference as a perfect 1.0 match. That is the right call when grading a
    user's answer (nothing to miss means nothing was missed) and exactly
    backwards here, where it condemned every message on such a card. Matched
    on word boundaries so "4" doesn't fire on "40" and "pH" doesn't fire on
    "phase".

    **Token overlap** then catches the longer case the containment check
    can't: a multi-word answer restated in the model's own words.
    """
    ref = back.strip()
    if not ref:
        return False

    pattern = re.escape(ref)
    if ref[:1].isalnum():
        pattern = r"\b" + pattern
    if ref[-1:].isalnum():
        pattern = pattern + r"\b"
    if re.search(pattern, message, re.I):
        return True

    # No comparable tokens (a short or purely symbolic answer) means the
    # containment check above was the whole test — an empty-reference overlap
    # score would only ever produce a false positive.
    if not _tokens(ref):
        return False
    return heuristic_overlap(ref, message) > SOCRATIC_LEAK_THRESHOLD


def disagrees_with_heuristic(grade: str, overlap: float) -> bool:
    """True when heuristic and LLM diverge enough to ask the user (§4.3).

    Only the two unambiguous directions are flagged: the model called it right
    while the answer shares almost nothing with the reference, or it called it
    wrong while the answer reproduced nearly all of it.
    """
    if grade in ("good", "easy") and overlap < 0.15:
        return True
    return bool(grade == "again" and overlap > 0.8)


def apply_bias(score: int, bias: float) -> int:
    """Per-user calibration (§4.3): nudge the *score* by the running average of
    the user's own overrides instead of fine-tuning anything.

    This adjusts the score rather than the grade so the two can never
    contradict each other. Nudging the grade alone produced visible nonsense:
    a score of 85 shown next to a suggested "easy", while the Easy button in
    front of the user is labelled 90-100%.

    Bias is accumulated in grade steps (see confirm_review), so it is scaled
    into score points here. The step is wide enough that a full one-grade bias
    reliably carries a mid-band score into the neighbouring band, which is what
    a one-grade correction is asking for.
    """
    return round(min(max(score + bias * BIAS_SCORE_STEP, 0.0), 100.0))

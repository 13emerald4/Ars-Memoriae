"""Proves every card of the JavaScript & TypeScript course.

* Code cards: the reference answer passes its tests in the app's own runner
  (type-checked for TypeScript); the starter code and every listed wrong
  answer do not.
* Predict cards: Node really prints the stated output.
* Compile cards: the TypeScript compiler (strict) reports errors on exactly
  the stated lines.

The compile checks and the type-checked code cards need the frontend's
TypeScript compiler (`npm ci` in frontend/); without it those parts skip.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

import app.services.code_runner_service as runner
from app.content.js_ts_course import COURSE, CodeCard, CompileCard, PredictCard, iter_cards
from app.content.js_ts_course.render import card_fields, card_kind

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
HAS_TSC = (FRONTEND / "node_modules" / "typescript" / "package.json").exists()

CARDS = [card for _, _, card in iter_cards()]
CODE = [c for c in CARDS if isinstance(c, CodeCard)]
PREDICT = [c for c in CARDS if isinstance(c, PredictCard)]
COMPILE = [c for c in CARDS if isinstance(c, CompileCard)]


def _node_flags() -> list[str]:
    out = subprocess.run(
        ["node", "-p", "process.allowedNodeEnvironmentFlags.has('--experimental-transform-types')"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    flags = ["--no-warnings"]
    if out.stdout.strip() == "true":
        flags.append("--experimental-transform-types")
    return flags


async def _gather_limited(coros, limit: int = 8):
    sem = asyncio.Semaphore(limit)

    async def one(coro):
        async with sem:
            return await coro

    return await asyncio.gather(*(one(c) for c in coros))


# ── structure ──────────────────────────────────────────────────────────────


def test_keys_and_names_are_unique():
    keys = [c.key for c in CARDS]
    assert len(keys) == len(set(keys)), "duplicate card keys"
    names = [s.name for p in COURSE for s in p.subdecks]
    assert len(names) == len(set(names)), "duplicate subdeck names"
    assert all(s.cards for p in COURSE for s in p.subdecks), "empty subdeck"


def test_coding_is_the_primary_learning_method():
    # Every card is code to write, read or compile; most are code to write.
    assert all(isinstance(c, CodeCard | PredictCard | CompileCard) for c in CARDS)
    assert len(CODE) / len(CARDS) >= 0.5, f"only {len(CODE)} of {len(CARDS)} cards are code-writing"


def test_code_cards_are_well_formed():
    for card in CODE:
        assert card.tests, card.key
        assert card.starter.strip() != card.solution.strip(), card.key
        assert card.language in ("javascript", "typescript"), card.key
        if card.type_tests:
            assert card.language == "typescript", card.key


def test_sources_point_at_mdn_or_the_typescript_docs():
    for part in COURSE:
        for subdeck in part.subdecks:
            for source in [*subdeck.sources, *(c.source for c in subdeck.cards if c.source)]:
                assert source.url.startswith(
                    ("https://developer.mozilla.org/", "https://www.typescriptlang.org/")
                ), source.url
                assert len(source.quote) <= 4000


def _looks_like_code(text: str) -> bool:
    """Python port of frontend/src/utils/codeUtils.ts:looksLikeCode."""
    t = text.strip()
    if "```" in t:
        return True
    definition = re.search(
        r"(?:^|\n)\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?"
        r"(?:function\b|class\b|def\b|const\b|let\b|var\b|import\b|from\s+[\w.]+\s+import)",
        t,
    )
    if definition and any(s in t for s in ("{", "}", "=>", ";", "return ", "():", "->", "//", "#")):
        return True
    if re.search(r"(?:\w+|\([^)]*\))\s*=>\s*[{]", t):
        return True
    if re.search(r"(?:^|\n)\s*def\s+\w+\s*\([^)]*\)\s*:", t):
        return True
    return bool(
        re.search(r"(?:^|\n)\s{2,}(?:return\b|yield\b|raise\b|throw\b)", t)
        and ("{" in t or ":" in t)
    )


def test_read_only_cards_are_not_shown_as_code_editors():
    for _, subdeck, card in iter_cards():
        if isinstance(card, CodeCard):
            continue
        fields = card_fields(card, subdeck.name)
        assert not _looks_like_code(fields["Back"]), card.key
        assert fields["Back"].startswith(
            card.output if isinstance(card, PredictCard) else card.answer
        )


def test_code_cards_render_with_their_starter_and_tests():
    for _, subdeck, card in iter_cards():
        if not isinstance(card, CodeCard):
            continue
        fields = card_fields(card, subdeck.name)
        assert fields["test_cases"] == card.tests
        assert fields["starter_code"] == card.starter
        assert card.starter.rstrip() in fields["Front"]  # the code to fix is on the card
        assert fields["Back"].rstrip().endswith(card.solution.rstrip())
        assert bool(fields.get("type_check")) == card.type_check
        assert card_kind(card) in ("write", "fix", "types")


# ── code cards run ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_code_cards_reference_passes_and_mistakes_fail(monkeypatch):
    monkeypatch.setattr(runner, "MAX_CONCURRENT_RUNS", 8)
    runner._run_slots.clear()

    jobs: list[tuple[str, str, CodeCard]] = []
    for card in CODE:
        if card.type_check and not HAS_TSC:
            continue
        jobs.append(("solution", card.solution, card))
        jobs.append(("starter", card.starter, card))
        jobs.extend((f"wrong #{i + 1}", code, card) for i, code in enumerate(card.wrong))

    async def run(code: str, card: CodeCard) -> dict:
        return await runner.run_code(
            code,
            card.tests,
            language=card.language,
            type_check=card.type_check,
            type_tests=card.type_tests,
        )

    results = await _gather_limited([run(code, card) for _, code, card in jobs])
    runner._run_slots.clear()

    problems = []
    for (what, _, card), res in zip(jobs, results, strict=True):
        accepted = res["status"] == "Accepted"
        if what == "solution" and not accepted:
            failing = [r for r in res.get("results", []) if not r.get("passed")][:2]
            problems.append(
                f"{card.key}: reference answer got {res['status']}: {res.get('error')} {failing}"
            )
        elif what != "solution" and accepted:
            problems.append(f"{card.key}: {what} was accepted")
    assert not problems, "\n".join(problems)


# ── predict cards print what they say ─────────────────────────────────────


async def _run_snippet(card: PredictCard, flags: list[str]) -> str:
    with tempfile.TemporaryDirectory(prefix="course-predict-") as tmp:
        root = Path(tmp)
        (root / "package.json").write_text('{"type": "module"}', encoding="utf-8")
        for name, body in (card.files or {}).items():
            (root / name).write_text(body, encoding="utf-8")
        main = root / ("main.ts" if card.language == "typescript" else "main.js")
        main.write_text(card.snippet, encoding="utf-8")
        proc = await asyncio.create_subprocess_exec(
            "node",
            *flags,
            str(main),
            cwd=tmp,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=30)
    lines = [line.rstrip("\r") for line in out.decode().rstrip("\r\n").split("\n")] if out.strip() else []
    if proc.returncode != 0:
        thrown = re.search(r"^(\w*Error\b.*)$", err.decode(), re.M)
        lines.append(
            thrown.group(1).rstrip("\r") if thrown else f"<exit {proc.returncode}> {err.decode()[:300]}"
        )
    return "\n".join(lines)


@pytest.mark.asyncio
async def test_predict_cards_print_what_they_say():
    flags = _node_flags()
    outputs = await _gather_limited([_run_snippet(card, flags) for card in PREDICT])
    problems = [
        f"{card.key}: expected {card.output!r}, Node printed {out!r}"
        for card, out in zip(PREDICT, outputs, strict=True)
        if out != card.output
    ]
    assert not problems, "\n".join(problems)


# ── compile cards match the compiler ──────────────────────────────────────

CHECKER = r"""
const { createRequire } = require('node:module');
const req = createRequire(process.argv[2] + '/');
const ts = req('typescript');
const GLOBALS = 'declare var console: { log(...data: any[]): void };';
const jobs = JSON.parse(require('node:fs').readFileSync(0, 'utf-8'));
const out = jobs.map(({ code, options }) => {
  const files = { 'snippet.ts': code, 'globals.d.ts': GLOBALS };
  const opts = {
    strict: true, noEmit: true, target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
    moduleDetection: ts.ModuleDetectionKind.Force, lib: ['lib.es2024.d.ts'], types: [],
    skipLibCheck: true, ...options,
  };
  const host = ts.createCompilerHost(opts, true);
  const get = host.getSourceFile.bind(host), exists = host.fileExists.bind(host), read = host.readFile.bind(host);
  host.getSourceFile = (n, v, ...r) => n in files ? ts.createSourceFile(n, files[n], v, true) : get(n, v, ...r);
  host.fileExists = (n) => n in files || exists(n);
  host.readFile = (n) => n in files ? files[n] : read(n);
  const program = ts.createProgram(Object.keys(files), opts, host);
  return ts.getPreEmitDiagnostics(program)
    .filter((d) => d.category === ts.DiagnosticCategory.Error)
    .map((d) => ({
      line: d.file && d.start !== undefined ? d.file.getLineAndCharacterOfPosition(d.start).line + 1 : 0,
      file: d.file ? d.file.fileName : '',
      message: ts.flattenDiagnosticMessageText(d.messageText, ' '),
    }));
});
process.stdout.write(JSON.stringify(out));
"""


@pytest.mark.skipif(not HAS_TSC, reason="TypeScript not installed (npm ci in frontend/)")
def test_compile_cards_match_the_compiler():
    if not COMPILE:
        pytest.skip("no compile cards")
    with tempfile.TemporaryDirectory(prefix="course-tsc-") as tmp:
        script = Path(tmp) / "check.cjs"
        script.write_text(CHECKER, encoding="utf-8")
        jobs = [{"code": c.snippet, "options": c.options} for c in COMPILE]
        proc = subprocess.run(
            ["node", str(script), str(FRONTEND)],
            input=json.dumps(jobs),
            capture_output=True,
            text=True,
            timeout=120,
        )
    assert proc.returncode == 0, proc.stderr
    problems = []
    for card, errors in zip(COMPILE, json.loads(proc.stdout), strict=True):
        stray = [e for e in errors if e["file"] != "snippet.ts"]
        lines = sorted({e["line"] for e in errors if e["file"] == "snippet.ts"})
        if stray or lines != sorted(card.error_lines):
            problems.append(f"{card.key}: expected errors on {card.error_lines}, tsc said {errors}")
    assert not problems, "\n".join(problems)

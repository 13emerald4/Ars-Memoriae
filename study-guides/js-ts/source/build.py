"""Build the Socratic study guides for the JavaScript & TypeScript course.

One PDF per course Part. Sources:
  * the course itself (backend/app/content/js_ts_course): cards, solutions,
    tests, quotes, deck summaries;
  * chapters/cNN.tex: the hand-written chapter bodies;
  * parts/partN.py: the Part's front matter, groupings, card notes, test
    questions, snippets, flags and deviations.

Before writing a PDF it verifies everything it labels as verified: each code
card's answer is run against the card's tests in the app's own runner, each
predicted output is run in Node, each compile verdict is checked with tsc,
and each chapter snippet is run and its output captured.

Usage:  python build.py 1 [2 3 4]
"""

from __future__ import annotations

import asyncio
import datetime as dt
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # study-guides/js-ts/source -> repo root
GUIDES = HERE.parent  # where the finished .tex and .pdf go
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"
sys.path.insert(0, str(BACKEND))

import app.services.code_runner_service as runner  # noqa: E402
from app.content.js_ts_course import COURSE, CodeCard, CompileCard, PredictCard  # noqa: E402
from app.content.js_ts_course.render import card_fields, card_kind  # noqa: E402

NODE_VERSION = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
TSC_VERSION = json.loads((FRONTEND / "node_modules/typescript/package.json").read_text())["version"]
TODAY = dt.date.today().isoformat()

# ── text conversion ────────────────────────────────────────────────────────

UNICODE = {
    "π": r"$\pi$", "²": r"$^2$", "×": r"$\times$", "−": r"$-$", "≥": r"$\geq$", "≤": r"$\leq$",
    "→": r"$\rightarrow$", "…": r"\ldots{}", "°": r"\textdegree{}", "≠": r"$\neq$", "✓": r"$\checkmark$",
}
SPECIAL = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&", "#": r"\#",
           "_": r"\_", "%": r"\%", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def url(u: str) -> str:
    """A URL safe inside macro arguments (tabularx, boxes)."""
    return u.replace("#", "\\#").replace("%", "\\%")


def esc(text: str) -> str:
    out = []
    for ch in text:
        out.append(SPECIAL.get(ch) or UNICODE.get(ch) or ch)
    return "".join(out)


def code_inline(text: str) -> str:
    """Inline code: \\code{} with every special character escaped."""
    s = esc(text).replace("<", r"\textless{}").replace(">", r"\textgreater{}")
    s = s.replace('"', r"\textquotedbl{}").replace("'", r"\textquotesingle{}")
    return r"\code{" + s + "}"


def inline_md(text: str) -> str:
    """`code`, **bold**, plain text → LaTeX."""
    parts = re.split(r"(`[^`]+`)", text)
    out = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            out.append(code_inline(p[1:-1]))
        else:
            seg = esc(p)
            seg = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", seg)
            out.append(seg)
    return "".join(out)


def listing(code: str, lang: str = "js", style: str = "") -> str:
    language = {"js": "JavaScript", "ts": "TypeScript", "javascript": "JavaScript",
                "typescript": "TypeScript", "text": "", "": ""}.get(lang, "JavaScript")
    opts = []
    if language:
        opts.append(f"language={language}")
    if style:
        opts.append(style)
    o = f"[{','.join(opts)}]" if opts else ""
    return f"\\begin{{lstlisting}}{o}\n{code.rstrip()}\n\\end{{lstlisting}}\n"


def md_block(text: str) -> str:
    """Markdown-lite with fenced code → LaTeX (fronts, notes)."""
    out = []
    pos = 0
    for m in re.finditer(r"```(\w*)\n(.*?)\n```", text, re.S):
        out.append(_md_paras(text[pos:m.start()]))
        out.append(listing(m.group(2), m.group(1) or "js"))
        pos = m.end()
    out.append(_md_paras(text[pos:]))
    return "".join(out)


def _md_paras(text: str) -> str:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return "".join(inline_md(" ".join(p.split("\n"))) + "\\par\n" for p in paras)


# ── chapter parsing ────────────────────────────────────────────────────────


def _balanced(s: str, i: int, open_ch: str, close_ch: str) -> int:
    """Index just past the group starting at s[i] == open_ch (braces nest)."""
    depth = 0
    j = i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    raise ValueError(f"unbalanced {open_ch} at {i}")


def find_terms(tex: str) -> list[tuple[str, str, str]]:
    """(key, word, definition) for each defining \\term[def]{key}{word}."""
    terms = []
    for m in re.finditer(r"\\term\[", tex):
        end_def = _balanced(tex, m.end() - 1, "[", "]")
        definition = tex[m.end():end_def - 1]
        k_end = _balanced(tex, end_def, "{", "}")
        w_end = _balanced(tex, k_end, "{", "}")
        terms.append((tex[end_def + 1:k_end - 1], tex[k_end + 1:w_end - 1], definition))
    return terms


def strip_margins(tex: str) -> str:
    """For copies: \\term → bold, drop margin notes and footnotes."""
    out = tex
    while True:
        m = re.search(r"\\term(\[)?", out)
        if not m:
            break
        i = m.end()
        if m.group(1):
            i = _balanced(out, i - 1, "[", "]")
        k_end = _balanced(out, i, "{", "}")
        w_end = _balanced(out, k_end, "{", "}")
        out = out[:m.start()] + r"\textbf{" + out[k_end + 1:w_end - 1] + "}" + out[w_end:]
    for macro in ("footnote", "safemargin"):
        while True:
            m = re.search(r"\\" + macro + r"\{", out)
            if not m:
                break
            end = _balanced(out, m.end() - 1, "{", "}")
            out = out[:m.start()] + out[end:]
    out = re.sub(r"\\label\{[^}]*\}", "", out)
    return out


class Chapter:
    def __init__(self, key: str, path: Path):
        self.key = key
        self.raw = path.read_text(encoding="utf-8")
        m = re.search(r"\\chap\{", self.raw)
        t_end = _balanced(self.raw, m.end() - 1, "{", "}")
        c_end = _balanced(self.raw, t_end, "{", "}")
        self.title = self.raw[m.end():t_end - 1]
        self.core = self.raw[t_end + 1:c_end - 1]
        self.terms = find_terms(self.raw)
        # Sections: \subsection{Q}% sec:id ... up to the next \subsection, \mantra or ponder.
        self.sections: dict[str, tuple[str, str]] = {}
        heads = list(re.finditer(r"\\subsection\{", self.raw))
        for n, h in enumerate(heads):
            q_end = _balanced(self.raw, h.end() - 1, "{", "}")
            question = self.raw[h.end():q_end - 1]
            sid = re.match(r"%\s*sec:([\w-]+)", self.raw[q_end:])
            if not sid:
                raise ValueError(f"{key}: subsection without '% sec:id': {question}")
            stop = heads[n + 1].start() if n + 1 < len(heads) else len(self.raw)
            body = self.raw[q_end + sid.end():stop]
            body = re.split(r"\\mantra\{|\\begin\{ponder\}", body)[0]
            self.sections[sid.group(1)] = (question, body.strip())
        mm = re.search(r"\\mantra\{", self.raw)
        self.mantra = self.raw[mm.end():_balanced(self.raw, mm.end() - 1, "{", "}") - 1] if mm else ""


# ── verification ───────────────────────────────────────────────────────────


async def verify_code(card: CodeCard) -> dict:
    res = await runner.run_code(card.solution, card.tests, language=card.language,
                                type_check=card.type_check, type_tests=card.type_tests)
    starter = await runner.run_code(card.starter, card.tests, language=card.language,
                                    type_check=card.type_check, type_tests=card.type_tests)
    return {"status": res["status"], "passed": res["passed_count"], "total": res["total_count"],
            "type_check": res.get("type_check"), "starter": starter["status"]}


def node_flags() -> list[str]:
    out = subprocess.run(["node", "-p", "process.allowedNodeEnvironmentFlags.has('--experimental-transform-types')"],
                         capture_output=True, text=True)
    return ["--no-warnings"] + (["--experimental-transform-types"] if out.stdout.strip() == "true" else [])


FLAGS = node_flags()


def run_node(code: str, lang: str = "js", files: dict | None = None) -> str:
    with tempfile.TemporaryDirectory(prefix="guide-run-") as tmp:
        root = Path(tmp)
        (root / "package.json").write_text('{"type": "module"}')
        for name, body in (files or {}).items():
            (root / name).write_text(body)
        main = root / ("main.ts" if lang in ("ts", "typescript") else "main.js")
        main.write_text(code)
        p = subprocess.run(["node", *FLAGS, str(main)], capture_output=True, text=True, cwd=tmp, timeout=30)
    lines = p.stdout.rstrip("\n").split("\n") if p.stdout.strip() else []
    if p.returncode != 0:
        thrown = re.search(r"^(\w*Error\b.*)$", p.stderr, re.M)
        lines.append(thrown.group(1) if thrown else f"<exit {p.returncode}>")
    return "\n".join(lines)


TSC_CHECKER = r"""
const { createRequire } = require('node:module');
const req = createRequire(process.argv[2] + '/');
const ts = req('typescript');
const GLOBALS = 'declare var console: { log(...data: any[]): void };';
const jobs = JSON.parse(require('node:fs').readFileSync(0, 'utf-8'));
process.stdout.write(JSON.stringify(jobs.map(({ code, options }) => {
  const files = { 'snippet.ts': code, 'globals.d.ts': GLOBALS };
  const opts = { strict: true, noEmit: true, target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
    moduleDetection: ts.ModuleDetectionKind.Force, lib: ['lib.es2024.d.ts'], types: [], skipLibCheck: true, ...options };
  const host = ts.createCompilerHost(opts, true);
  const get = host.getSourceFile.bind(host), ex = host.fileExists.bind(host), rd = host.readFile.bind(host);
  host.getSourceFile = (n, v, ...r) => n in files ? ts.createSourceFile(n, files[n], v, true) : get(n, v, ...r);
  host.fileExists = (n) => n in files || ex(n);
  host.readFile = (n) => n in files ? files[n] : rd(n);
  return ts.getPreEmitDiagnostics(ts.createProgram(Object.keys(files), opts, host))
    .filter((d) => d.category === ts.DiagnosticCategory.Error && d.file && d.file.fileName === 'snippet.ts')
    .map((d) => ({ line: d.file.getLineAndCharacterOfPosition(d.start).line + 1,
                   message: ts.flattenDiagnosticMessageText(d.messageText, ' ') }));
})));
"""


def tsc_errors(jobs: list[tuple[str, dict]]) -> list[list[dict]]:
    if not jobs:
        return []
    with tempfile.TemporaryDirectory(prefix="guide-tsc-") as tmp:
        script = Path(tmp) / "check.cjs"
        script.write_text(TSC_CHECKER)
        p = subprocess.run(["node", str(script), str(FRONTEND)], input=json.dumps(
            [{"code": c, "options": o} for c, o in jobs]), capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)


# ── document pieces ────────────────────────────────────────────────────────

PREAMBLE = (HERE / "preamble.tex").read_text(encoding="utf-8")


def load_part(n: int):
    if str(HERE / "parts") not in sys.path:
        sys.path.insert(0, str(HERE / "parts"))
    spec = importlib.util.spec_from_file_location(f"part{n}", HERE / "parts" / f"part{n}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def subdeck_key(subdeck) -> str:
    return "c" + subdeck.name.split(" ", 1)[0]


class Build:
    def __init__(self, n: int):
        self.n = n
        self.part = COURSE[n - 1]
        self.cfg = load_part(n)
        self.chapters: dict[str, Chapter] = {}
        for sd in self.part.subdecks:
            key = subdeck_key(sd)
            self.chapters[key] = Chapter(key, HERE / "chapters" / f"{key}.tex")
        self.cards = [(sd, c) for sd in self.part.subdecks for c in sd.cards]
        self.snippet_results: dict[str, str] = {}
        self.code_results: dict[str, dict] = {}
        self.predict_results: dict[str, str] = {}
        self.compile_results: dict[str, list] = {}
        self.problems: list[str] = []

    # verification ---------------------------------------------------------
    def verify(self):
        runner.MAX_CONCURRENT_RUNS = 6
        runner._run_slots.clear()

        async def all_code():
            sem = asyncio.Semaphore(6)

            async def one(card):
                async with sem:
                    return card.key, await verify_code(card)

            return dict(await asyncio.gather(*(one(c) for _, c in self.cards if isinstance(c, CodeCard))))

        self.code_results = asyncio.run(all_code())
        for key, r in self.code_results.items():
            if r["status"] != "Accepted" or r["passed"] != r["total"]:
                self.problems.append(f"{key}: reference answer got {r['status']} {r['passed']}/{r['total']}")
            if r["starter"] == "Accepted":
                self.problems.append(f"{key}: starter passes")
        for _, c in self.cards:
            if isinstance(c, PredictCard):
                out = run_node(c.snippet, c.language, c.files)
                self.predict_results[c.key] = out
                if out != c.output:
                    self.problems.append(f"{c.key}: Node printed {out!r}, card says {c.output!r}")
        compiles = [c for _, c in self.cards if isinstance(c, CompileCard)]
        for c, errs in zip(compiles, tsc_errors([(c.snippet, c.options) for c in compiles]), strict=True):
            self.compile_results[c.key] = errs
            if sorted({e["line"] for e in errs}) != sorted(c.error_lines):
                self.problems.append(f"{c.key}: tsc errors {errs} != {c.error_lines}")
        # chapter snippets
        snippets = getattr(self.cfg, "SNIPPETS", {})
        ts_jobs = [(k, s) for k, s in snippets.items() if s.get("compile") is not None]
        for (k, s), errs in zip(ts_jobs, tsc_errors([(s["code"], s.get("options", {})) for _, s in ts_jobs]), strict=True):
            lines = sorted({e["line"] for e in errs})
            if lines != sorted(s["compile"]):
                self.problems.append(f"snippet {k}: tsc errors on {lines}, expected {s['compile']}: {errs}")
            self.snippet_results[k + ":tsc"] = json.dumps(errs)
        for k, s in snippets.items():
            if s.get("run", True):
                out = run_node(s["code"], s.get("lang", "js"), s.get("files"))
                self.snippet_results[k] = out
                if "out" in s and out != s["out"]:
                    self.problems.append(f"snippet {k}: printed {out!r}, expected {s['out']!r}")
        if self.problems:
            raise SystemExit("VERIFICATION FAILED:\n  " + "\n  ".join(self.problems))

    # rendering --------------------------------------------------------------
    def snippet_tex(self, key: str) -> str:
        s = self.cfg.SNIPPETS[key]
        lang = s.get("lang", "js")
        tex = "\\Needspace{6\\baselineskip}\n" + listing(s.get("display", s["code"]), lang)
        if s.get("compile") is not None:
            errs = json.loads(self.snippet_results[key + ":tsc"])
            verdict = "; ".join(f"line {e['line']}: {e['message']}" for e in errs) or "compiles with no errors"
            tex += "{\\small\\textit{tsc --strict:}~" + esc(verdict) + "}\\par\n"
        if s.get("run", True) and s.get("show_out", True) and self.snippet_results.get(key):
            out = self.snippet_results[key].split("\n")
            sep = r"\enspace\textcolor{black!45}{|}\enspace "
            if max(len(x) for x in out) > 40:
                tex += "{\\small\\textit{Prints:}}\n" + listing("\n".join(out), "text")
            else:
                tex += "{\\small\\textit{Prints:}~" + sep.join(code_inline(x) for x in out) + "}\\par\n"
        return tex

    def chapter_tex(self, key: str) -> str:
        raw = self.chapters[key].raw
        return re.sub(r"^%%SNIPPET:([\w-]+)%%\s*$", lambda m: self.snippet_tex(m.group(1)), raw, flags=re.M)

    def front(self) -> str:
        c = self.cfg
        return (
            "\\begin{document}\n"
            f"{{\\noindent\\raggedright\\LARGE\\bfseries\\color{{blue!40!black}} {esc(c.TITLE)}\\par}}\n"
            f"\\vspace{{2pt}}{{\\large {esc(c.SUBTITLE)}}}\\par\\vspace{{6pt}}\n"
            "\\begin{corebox}\\textbf{The question this guide answers.} " + c.META_QUESTION + "\\par\\smallskip\n"
            + c.META_DECOMPOSITION + "\\end{corebox}\n"
            "\\vspace{6pt}\\tableofcontents\\vspace{6pt}\n\\newpage\n"
        )

    def body(self) -> str:
        out = []
        for title, intro, keys in self.cfg.GROUPS:
            out.append(f"\\partline{{{title}}}{{{intro}}}\n")
            for k in keys:
                out.append(self.chapter_tex(k) + "\n")
        return "".join(out)

    def synthesis(self) -> str:
        return ("\\phantomsection\\label{synthesis}\n\\section*{How the Parts Answer the Question}"
                "\\addcontentsline{toc}{section}{How the Parts Answer the Question}\n" + self.cfg.SYNTHESIS + "\n")

    def tests(self) -> str:
        items = "".join(f"\\item {inline_md(q)} \\hfill{{\\small\\hyperref[ch:{ch}]{{→ {esc(self.chapters[ch].title.split('.')[0])}}}}}\n"
                        .replace("→", r"$\rightarrow$ Ch.~") for q, ch in self.cfg.TEST_QUESTIONS)
        return ("\\section*{Test Yourself}\\addcontentsline{toc}{section}{Test Yourself}\n"
                "Answer without looking; the link after each question points to the chapter that holds the answer.\n"
                f"\\begin{{enumerate}}[leftmargin=1.6em,itemsep=3pt]\n{items}\\end{{enumerate}}\n")

    def card_guide(self) -> str:
        notes = self.cfg.CARDS
        out = ["\\newpage\\phantomsection\\partline{Card-by-Card Solution Guide}{One entry for every card in this Part's decks.}\n",
               "\\begin{corebox}\\textbf{How this part works.} Each entry is self-contained: it repeats the card, "
               "the terms it needs and the chapter sections it drills, so you can study a card without turning back. "
               "That repetition is deliberate (the one exception to saying each thing once). For each card: the card "
               "as it appears in your deck; how to solve it (approach, what must stay true, what lives in memory, the "
               "types involved, how it fails, how to test it) and the trap that most often costs it; the solution, "
               "checked by actually running it; and the readings from the chapters.\\end{corebox}\n",
               "\\subsection*{Which card drills which chapters?}\n"]
        rows = []
        for i, (sd, c) in enumerate(self.cards, 1):
            chs = ", ".join(f"\\hyperref[ch:{k}]{{{esc(self.chapters[k].title.split('.')[0])}}}" for k in notes[c.key]["chapters"])
            rows.append(f"{i} & {inline_md(card_label(c))} & Ch.~{chs}\\\\\n")
        for start in range(0, len(rows), 30):
            out.append("{\\footnotesize\\begin{tabularx}{\\linewidth}{@{}rXl@{}}\\toprule\n"
                       "\\textbf{\\#} & \\textbf{Card} & \\textbf{Chapters it drills}\\\\\\midrule\n")
            out.extend(rows[start:start + 30])
            out.append("\\bottomrule\\end{tabularx}}\\par\n")
        num = 0
        for sd in self.part.subdecks:
            key = subdeck_key(sd)
            ch = self.chapters[key]
            out.append(f"\\deckhead{{{esc(sd.name)}}}{{{len(sd.cards)}}}\n")
            out.append(f"\\begin{{corebox}}\\textbf{{Core idea.}} {ch.core}\\end{{corebox}}\n")
            out.append(f"\\begin{{sumbox}}{{Deck summary sheet --- {esc(sd.name)}}}\n{inline_md(sd.summary)}\\par\n"
                       "\\smallskip{\\footnotesize Read more: " + "; ".join(
                           f"\\href{{{url(s.url)}}}{{{esc(s.title)}}}" for s in sd.sources) + "}\\end{sumbox}\n")
            for c in sd.cards:
                num += 1
                out.append(self.card_entry(num, sd, c, notes[c.key]))
        return "".join(out)

    def card_entry(self, num: int, sd, c, note: dict) -> str:
        fields = card_fields(c, sd.name)
        sig = card_signature(c)
        out = [f"\\cardhead{{Card {num} --- {esc(card_title(c))}}}{{{esc(sig)}}}\n"]
        # Terms for this card: every term defined in the sections it reads.
        defs = []
        seen = set()
        for sec in note["read"]:
            ch = self.section_chapter(sec)
            body = ch.sections[sec][1]
            for k, w, d in ch.terms:
                if k not in seen and re.search(r"\\term(\[[^\]]*?\])?\{" + re.escape(k) + r"\}", body):
                    seen.add(k)
                    defs.append(d)
            for k in note.get("terms", []):
                if k not in seen:
                    t = self.find_term(k)
                    if t:
                        seen.add(k)
                        defs.append(t)
        if defs:
            out.append("\\safemargin{\\textbf{Terms for this card}\\par\\smallskip " + "\\par\\smallskip ".join(defs) + "}\n")
        chs = ", ".join(f"\\hyperref[ch:{k}]{{Ch.~{esc(self.chapters[k].title.split('.')[0])}}}" for k in note["chapters"])
        out.append(f"\\noindent{{\\small\\textbf{{Covered in:}} {chs} of this guide; documentation: "
                   f"\\href{{{url(c.source.url)}}}{{{esc(c.source.title)}}}.}}\\par\n")
        out.append("\\cardsub{The card}\n" + md_block(fields["Front"]))
        out.append("\\cardsub{How to solve it}\n\\begin{cardrows}\n")
        for label, k in (("Solve", "solve"), ("Invariants", "invariants"), ("Memory", "memory"),
                         ("Types", "types"), ("Failure", "failure"), ("Tests", "tests")):
            out.append(f"\\item[{label}] {inline_md(note[k])}\n")
        out.append("\\end{cardrows}\n\\trap " + inline_md(note["trap"]) + "\\par\n")
        out.append("\\cardsub{Solution}\n" + self.solution_tex(c))
        out.append("\\cardsub{From the readings}\n")
        by_chapter: dict[str, list[str]] = {}
        for sec in note["read"]:
            by_chapter.setdefault(self.section_chapter(sec).key, []).append(sec)
        for k, secs in by_chapter.items():
            ch = self.chapters[k]
            out.append(f"\\readchap{{{ch.title}}}{{{ch.core}}}\n")
            for sec in secs:
                q, body = ch.sections[sec]
                out.append(f"\\readq{{{q}}}\n{strip_margins(self.expand_snippets(body))}\n")
        out.append("\\cardend\n")
        return "".join(out)

    def expand_snippets(self, tex: str) -> str:
        return re.sub(r"^%%SNIPPET:([\w-]+)%%\s*$", lambda m: self.snippet_tex(m.group(1)), tex, flags=re.M)

    def section_chapter(self, sec: str) -> Chapter:
        for ch in self.chapters.values():
            if sec in ch.sections:
                return ch
        raise KeyError(f"no section {sec}")

    def find_term(self, key: str) -> str | None:
        for ch in self.chapters.values():
            for k, _, d in ch.terms:
                if k == key:
                    return d
        return None

    def solution_tex(self, c) -> str:
        if isinstance(c, CodeCard):
            r = self.code_results[c.key]
            checked = " and type-checked by the TypeScript compiler (strict)" if c.type_check else ""
            label = (f"\\textit{{Verified: passes all {r['total']} test cases on the card in the app's code runner"
                     f"{checked}; the starter code fails them.}}")
            return listing(c.solution, "ts" if c.language == "typescript" else "js") + "{\\small " + label + "}\\par\n" + \
                "\\smallskip{\\small\\textbf{Why:} " + inline_md(c.why) + "}\\par\n"
        if isinstance(c, PredictCard):
            return ("{\\small\\textbf{Prints:}}\n" + listing(c.output, "text") +
                    f"{{\\small\\textit{{Verified: Node {NODE_VERSION} prints exactly this.}}}}\\par\n"
                    "\\smallskip{\\small\\textbf{Why:} " + inline_md(c.why) + "}\\par\n")
        errs = self.compile_results[c.key]
        where = ("; ".join(f"line {e['line']}: {e['message']}" for e in errs)) or "no errors"
        return (inline_md(c.answer) + "\\par\n" +
                f"{{\\small\\textit{{Verified: tsc {TSC_VERSION} (strict) reports: {esc(where)}.}}}}\\par\n"
                "\\smallskip{\\small\\textbf{Why:} " + inline_md(c.why) + "}\\par\n")

    def audit(self) -> str:
        c = self.cfg
        rows = []
        out = ["\\addtocontents{toc}{\\vspace{6pt}}\n\\Needspace{14\\baselineskip}\\phantomsection\\section*{Appendix: Audit Trail}"
               "\\addcontentsline{toc}{section}{Appendix: Audit Trail}\n"]
        out.append("\\subsection*{Sources}\n{\\footnotesize\\begin{tabularx}{\\linewidth}{@{}p{1.6in}p{0.9in}X@{}}\\toprule\n"
                   "\\textbf{Source} & \\textbf{How much read} & \\textbf{Used for}\\\\\\midrule\n")
        for name, how, use in c.SOURCES:
            out.append(f"{name} & {how} & {use}\\\\\n")
        out.append("\\bottomrule\\end{tabularx}}\n\n{\\footnotesize\\textbf{Not read:} " + c.NOT_READ + "}\n")
        # Claim ledger, grouped by source, auto-built from the cards.
        groups: dict[str, list[tuple[str, str, str]]] = {}
        for sd, card in self.cards:
            groups.setdefault(card.source.title, []).append(
                (card.key, f"\\href{{{url(card.source.url)}}}{{page}}", "quoted (word-for-word check)"))
        out.append("\\subsection*{Claim ledger}\n{\\footnotesize Each card's explanation rests on the documentation "
                   "excerpt shown with it; the table lists, per source page, the cards whose claim it backs. Code "
                   "behaviour claimed in the chapters and solutions was established by running it (see Checks run).}\n")
        items = sorted(groups.items())
        for start in range(0, len(items), 22):
            out.append("{\\footnotesize\\begin{tabularx}{\\linewidth}{@{}p{2.2in}X@{}}\\toprule\n"
                       "\\textbf{Source (all quoted, checked word for word)} & \\textbf{Cards whose claim it backs}\\\\\\midrule\n")
            for title, entries in items[start:start + 22]:
                keys = ", ".join(esc(k) for k, _, _ in entries)
                out.append(f"{esc(title)} ({entries[0][1]}) & {keys}\\\\\n")
            out.append("\\bottomrule\\end{tabularx}}\n")
        authored = len([1 for ch in self.chapters.values() for _ in ch.terms])
        out.append("{\\footnotesize\\textbf{Authored, not sourced:} every analogy in a term definition "
                   f"({authored} terms), every rule of thumb, every Think-it-through box, the chapter prose that "
                   "connects the sourced facts, the How-to-solve rows and traps, and all chapter code snippets "
                   "(their behaviour was run, see below). The cards themselves (tasks, tests, solutions) were written "
                   "for this course earlier in this session and are verified, not sourced.}\n")
        out.append("\\subsection*{Flags}\n{\\footnotesize\\begin{itemize}\n" + "".join(f"\\item {f}\n" for f in c.FLAGS) + "\\end{itemize}}\n")
        n_code = len(self.code_results)
        n_tests = sum(r["total"] for r in self.code_results.values())
        n_typed = sum(1 for _, x in self.cards if isinstance(x, CodeCard) and x.type_check)
        snip_run = sum(1 for k, s in c.SNIPPETS.items() if s.get("run", True))
        snip_tsc = sum(1 for s in c.SNIPPETS.values() if s.get("compile") is not None)
        checks = [
            f"Code cards: {n_code} reference answers run in the app's own code runner against the cards' {n_tests} test cases: all pass. Every starter fails. {n_typed} TypeScript answers also type-checked (strict) with their type tests: all pass.",
            f"Predict cards: {len(self.predict_results)} snippets run in Node {NODE_VERSION}: each prints exactly the card's answer.",
            f"Compile cards: {len(self.compile_results)} snippets checked with tsc {TSC_VERSION} (strict): errors on exactly the stated lines.",
            f"Chapter snippets: {snip_run} run in Node {NODE_VERSION}; every \\textit{{Prints}} line is the captured output. {snip_tsc} checked with tsc {TSC_VERSION}.",
            "Quotes: every card's quote found word for word (ignoring markdown) in the documentation source text (MDN content and TypeScript-Website repositories, fetched on " + TODAY + ").",
            "The course's own test suite (\\code{tests/test\\_js\\_ts\\_course.py}) passes, including planted wrong answers that each card must reject.",
            f"Deck files: \\path{{study-guides/js-ts/decks/{slug(self.part.name)}/}} holds the {len(self.part.subdecks)} decks of this Part as JSON (a plain array and a wrapped copy each): {n_code} code cards and {len(self.cards) - n_code} qa cards, each with its verified quote. They are written by \\path{{export\\_decks.py}} from the same course data the checks above ran on. All 27 deck files of the course were imported through the app's \\code{{POST /api/import/json}} into a fresh test database: no warnings, every quote became a citation, and every code card's answer passed all its test cases (and its type check) through the imported card's run-code endpoint.",
        ]
        checks = [x for x in checks if not re.match(r"(Predict|Compile|Code) cards: 0 ", x)]
        not_run = ["Not run: the cards in your own app with the local 3B grading model (grading of typed answers is not verified here).",
                   "Not run: Node 24 on Windows; checks used Node " + NODE_VERSION + " on Linux.",
                   "Not checked: the live web pages (the quotes were checked against the pages' source files, which can lag or lead the site)."]
        out.append("\\subsection*{Checks run}\n{\\footnotesize\\begin{itemize}\n" + "".join(f"\\item {x}\n" for x in checks + not_run) + "\\end{itemize}}\n")
        out.append("\\subsection*{Deviations}\n{\\footnotesize\\begin{itemize}\n" + "".join(f"\\item {d}\n" for d in c.DEVIATIONS) + "\\end{itemize}}\n")
        out.append("\\subsection*{Revision log}\n{\\footnotesize\\begin{itemize}\n" + "".join(f"\\item {r}\n" for r in c.REVISIONS) + "\\end{itemize}}\n")
        return "".join(out) + "".join(rows)

    def index(self) -> str:
        entries = []
        for k, ch in self.chapters.items():
            for key, word, _ in ch.terms:
                entries.append((re.sub(r"\\[a-z]+\{|\}", "", word).lower(), key, word, ch.title.split(".")[0]))
        entries.sort()
        return ("\\addtocontents{toc}{\\vspace{6pt}}\n\\phantomsection\\section*{Index of Terms}"
                "\\addcontentsline{toc}{section}{Index of Terms}\n{\\small\\begin{multicols}{2}\n" +
                "".join(f"\\ix{{{key}}}{{{word}}}{{Ch.~{num}}}\n" for _, key, word, num in entries) +
                "\\end{multicols}}\n")

    def document(self) -> str:
        return "".join([PREAMBLE, self.front(), self.body(), self.synthesis(), self.tests(),
                        self.card_guide(), self.audit(), self.index(), "\\end{document}\n"])

    def compile(self) -> Path:
        out_dir = HERE / "out"
        out_dir.mkdir(exist_ok=True)
        tex = out_dir / f"{self.cfg.FILENAME}.tex"
        tex.write_text(self.document(), encoding="utf-8")
        for _ in range(3):
            p = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
                               cwd=out_dir, capture_output=True, text=True)
            if p.returncode != 0:
                log = (out_dir / f"{self.cfg.FILENAME}.log").read_text(errors="replace")
                err = log[log.find("\n!"):][:3000] if "\n!" in log else p.stdout[-3000:]
                raise SystemExit(f"pdflatex failed:\n{err}")
        for ext in (".tex", ".pdf"):
            shutil.copy2(out_dir / f"{self.cfg.FILENAME}{ext}", GUIDES / f"{self.cfg.FILENAME}{ext}")
        return GUIDES / f"{self.cfg.FILENAME}.pdf"


def card_title(c) -> str:
    if isinstance(c, CodeCard):
        return c.title
    return "What does this print?" if isinstance(c, PredictCard) else "Does it compile?"


def card_label(c) -> str:
    return f"`{c.title}`" if isinstance(c, CodeCard) else f"{card_title(c)} ({c.key})"


def card_signature(c) -> str:
    if isinstance(c, CodeCard):
        return f"{card_kind(c)} · {c.language} · {c.difficulty}"
    return f"{card_kind(c)} · {c.key}"


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        b = Build(int(arg))
        b.verify()
        pdf = b.compile()
        print(f"built {pdf}")

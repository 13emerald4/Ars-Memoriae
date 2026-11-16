"""Card shapes for the coding-first JavaScript & TypeScript course.

Every card makes the learner read or write code:

* ``CodeCard``    write a function (or fix one, or add its types). Graded by
                  running the answer against ``tests``; TypeScript cards are
                  also type-checked, with ``type_tests`` pinning the types.
* ``PredictCard`` read a snippet and say exactly what it prints.
* ``CompileCard`` read a TypeScript snippet and say whether ``tsc --strict``
                  accepts it, and if not, which statement fails and why.

``tests/test_js_ts_course.py`` proves each card: the reference answer passes,
the starter and every listed wrong answer fail, every printed output is what
Node really prints, and every compile verdict is what the compiler says.
"""

from __future__ import annotations

from dataclasses import dataclass, field

TS_HANDBOOK = "https://www.typescriptlang.org/docs/handbook/2/"
TS_DOCS = "https://www.typescriptlang.org/docs/handbook/"
MDN_JS = "https://developer.mozilla.org/en-US/docs/Web/JavaScript/"


@dataclass(frozen=True)
class Source:
    """A documentation page, optionally with a verbatim excerpt from it."""

    title: str
    url: str
    quote: str = ""


@dataclass
class CodeCard:
    key: str
    title: str
    task: str
    starter: str
    solution: str
    tests: list[dict]
    why: str
    language: str = "javascript"
    type_tests: str | None = None
    wrong: list[str] = field(default_factory=list)
    source: Source | None = None
    difficulty: str = "Easy"
    kind: str = "write"  # "write" | "fix" | "types"

    @property
    def type_check(self) -> bool:
        return self.language == "typescript"


@dataclass
class PredictCard:
    key: str
    snippet: str
    output: str
    why: str
    language: str = "javascript"
    # Other modules the snippet imports, by file name (module cards).
    files: dict[str, str] | None = None
    source: Source | None = None
    difficulty: str = "Easy"
    # Replaces "What does this print?" when the question needs context.
    prompt: str | None = None


@dataclass
class CompileCard:
    key: str
    snippet: str
    answer: str
    # 1-based lines the compiler must report errors on; empty means it compiles.
    error_lines: list[int]
    why: str
    # Extra compiler options on top of `strict` (e.g. noUncheckedIndexedAccess).
    options: dict = field(default_factory=dict)
    source: Source | None = None
    difficulty: str = "Medium"


Card = CodeCard | PredictCard | CompileCard


@dataclass
class Subdeck:
    name: str
    summary: str
    sources: list[Source]
    cards: list[Card]


@dataclass
class Part:
    name: str
    summary: str
    subdecks: list[Subdeck]

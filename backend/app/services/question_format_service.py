"""Canonical formatter for embedding code components of questions in fenced IDE blocks."""

from __future__ import annotations

import re

_FENCE_ALIASES: dict[str, str] = {
    "ts": "ts",
    "tsx": "ts",
    "typescript": "ts",
    "js": "js",
    "jsx": "js",
    "javascript": "js",
    "py": "python",
    "python": "python",
    "java": "java",
    "cpp": "cpp",
    "c++": "cpp",
    "c": "c",
    "go": "go",
    "rust": "rust",
    "rs": "rust",
    "sql": "sql",
}

_SANDBOX_MARKERS = (
    "// ---- Sandbox harness",
    "// --- provided (framework + service)",
)

_SKIP_SANDBOX_FN_RE = re.compile(
    r"^(?:export\s+)?(?:async\s+)?function\s+"
    r"(?:run[A-Z]\w*|countAllTies|respond|failWith|findStation|unknownStation)\b"
)
_SKIP_SANDBOX_TYPE_RE = re.compile(r"^(?:export\s+)?type\s+\w+Op\b")
_DECL_START_RE = re.compile(
    r"^(?:export\s+)?(?:(?:async\s+)?function|class|interface|type|enum)\s+([A-Za-z_$][\w$]*)"
)
_JSDOC_OR_COMMENT_RE = re.compile(r"^\s*(?://|/\*|\*)")

_STRONG_CODE_LINE_RE = re.compile(
    r"^\s*(?:"
    r"(?:export\s+)?(?:async\s+)?(?:function|class|interface|type|enum)\s+[A-Za-z_$]|"
    r"(?:public|private|protected|readonly|static)\s+|"
    r"def\s+[A-Za-z_]\w*\s*\(|"
    r"class\s+[A-Za-z_]\w*(?:\([^)]*\))?\s*:|"
    r"return\b.*?;?|"
    r"(?:const|let|var)\s+[A-Za-z_$]\w*\s*(?::|=)|"
    r"[{}]\s*;?$"
    r")"
)


def infer_fence_lang(language: str | None = None, code: str = "", front: str = "") -> str:
    """Return a concise markdown fence language tag for code blocks."""
    raw = (language or "").strip().lower()
    if raw in _FENCE_ALIASES:
        return _FENCE_ALIASES[raw]
    if raw:
        return raw

    sample = f"{code}\n{front}"
    if re.search(r"\bdef\s+\w+\s*\([^)]*\)\s*(?:->|:)", sample) or "elif " in sample:
        return "python"
    if re.search(
        r":\s*(?:number|string|boolean|void|unknown|never|Result<|Promise<)|\btype\s+\w+\s*=|\binterface\s+\w+|=>",
        sample,
    ):
        return "ts"
    return ""


def _has_fenced_code(text: str) -> bool:
    return bool(re.search(r"```[a-zA-Z0-9_+#.-]*\s*\r?\n[\s\S]*?```", text or ""))


def _extract_target_names(front: str) -> list[str]:
    names: list[str] = []
    for match in re.finditer(r"`([A-Za-z_$][\w$]*)\s*\(", front or ""):
        name = match.group(1)
        if name not in names:
            names.append(name)
    for match in re.finditer(r"\b(?:class|interface)\s+`?([A-Z][\w$]*)`?", front or ""):
        name = match.group(1)
        if name not in names:
            names.append(name)
    return names


def _collect_top_level_blocks(lines: list[str]) -> list[tuple[str, str, str]]:
    """Parse top-level TS/JS declarations as (kind_name, block_text, comment_before)."""
    blocks: list[tuple[str, str, str]] = []
    i = 0
    n = len(lines)
    pending_comments: list[str] = []

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            pending_comments.clear()
            i += 1
            continue

        if stripped.startswith("//"):
            if "----" in stripped:
                pending_comments.clear()
            else:
                pending_comments.append(line)
            i += 1
            continue

        if stripped.startswith("/*"):
            comment_lines = [line]
            while i + 1 < n and "*/" not in lines[i]:
                i += 1
                comment_lines.append(lines[i])
            pending_comments = comment_lines
            i += 1
            continue

        decl_m = _DECL_START_RE.match(stripped)
        if not decl_m:
            pending_comments.clear()
            i += 1
            continue

        name = decl_m.group(1)
        block_lines = list(pending_comments) + [line]
        pending_comments.clear()

        depth = line.count("{") - line.count("}")
        ends_with_semi = stripped.endswith(";") and depth <= 0

        if depth > 0 or (not ends_with_semi and "{" not in line and not stripped.endswith(";")):
            j = i + 1
            while j < n:
                nxt = lines[j]
                block_lines.append(nxt)
                depth += nxt.count("{") - nxt.count("}")
                nxt_stripped = nxt.strip()
                if depth <= 0 and ("}" in nxt or nxt_stripped.endswith(";")):
                    i = j
                    break
                j += 1
            else:
                i = n - 1

        blocks.append((name, "\n".join(block_lines).strip(), ""))
        i += 1

    return blocks


def _clean_function_stub(block_text: str) -> str:
    """Replace internal mock boilerplate in a function stub with a concise // TODO body."""
    lines = block_text.splitlines()
    if len(lines) <= 5 and "const readFile" not in block_text and "Info {" not in block_text:
        return block_text

    # Keep leading comments + function header up to opening `{`, emit clean `// TODO`.
    header_lines: list[str] = []
    for line in lines:
        header_lines.append(line)
        if "{" in line and not line.strip().startswith("//") and not line.strip().startswith("*"):
            break
    indent = "  "
    if len(lines) >= 2 and lines[-2].startswith("    "):
        indent = "    "
    return "\n".join(header_lines) + f"\n{indent}// TODO\n}}"


def _extract_orderedset_task33(starter_code: str) -> str:
    marker = "// ---- src/organization/orderedset.ts"
    idx = starter_code.find(marker)
    if idx == -1:
        return ""
    sub = starter_code[idx:]
    end_marker = "// ---- src/organization/albumarchive.ts"
    end_idx = sub.find(end_marker)
    if end_idx != -1:
        sub = sub[:end_idx]
    return sub.strip()


def _extract_class_spec_from_front(front: str, targets: list[str]) -> list[str]:
    """Synthesize clean TypeScript class skeletons from bullet specifications when starter is a stub."""
    class_blocks: list[str] = []
    for cls_name in targets:
        if not cls_name or not cls_name[0].isupper():
            continue
        # Only build a class skeleton if the prompt mentions implementing that class + fields/methods.
        if not re.search(rf"\b(?:encapsulated\s+)?class\s+`?{re.escape(cls_name)}`?", front):
            continue

        members: list[str] = []
        # Extract fields declared in `Field:` / `Fields:` / `Private fields:` lines
        field_line_re = re.compile(
            r"(?:Private\s+)?Fields?\s*:\s*(.+)", re.IGNORECASE
        )
        for fl_match in field_line_re.finditer(front):
            line_text = fl_match.group(1)
            for code_span in re.findall(r"`([^`\n]+)`", line_text):
                for part in code_span.split(";"):
                    p = part.strip().rstrip(";")
                    if ":" in p:
                        if p.startswith(("public ", "private ", "protected ")):
                            members.append(f"  {p};")
                        else:
                            members.append(f"  public {p};")

        # Extract method/constructor signatures on bullet lines (`constructor(...)`, `method(...): Ret`)
        for raw_line in front.splitlines():
            m = re.match(
                r"^\s*[-*•]\s+`((?:constructor|[A-Za-z_$][\w$]*)\([^`\n]*\)(?:\s*:\s*[^`\n]+)?)`",
                raw_line,
            )
            if m:
                sig = m.group(1).strip()
                if sig.startswith("constructor"):
                    members.append(f"  public {sig} {{ /* TODO */ }}")
                elif ":" in sig:
                    members.append(f"  public {sig} {{ /* TODO */ }}")
                else:
                    members.append(f"  public {sig} {{ /* TODO */ }}")

        if members:
            class_blocks.append(f"class {cls_name} {{\n" + "\n".join(members) + "\n}")

    return class_blocks


def _extract_provided_methods_for_task30(front: str) -> str:
    if "AlbumArchive" in front and "add(item: Album)" in front and "remove(item: Album)" in front:
        return (
            "// src/organization/albumarchive.ts (existing operations)\n"
            "class AlbumArchive {\n"
            "  public add(item: Album): boolean { /* ... */ }\n"
            "  public remove(item: Album): boolean { /* ... */ }\n"
            "}"
        )
    return ""


def _extract_python_or_other_from_starter(front: str, starter_code: str, lang: str) -> str:
    """Clean extraction for non-TS starters (e.g. Python forged problems)."""
    lines = starter_code.strip().splitlines()
    if len(lines) <= 45:
        return starter_code.strip()
    return "\n".join(lines[:35]).strip()


def extract_question_code_from_starter(
    front: str, starter_code: str | None, language: str | None = None
) -> tuple[str, str]:
    """Return (fence_lang, code_snippet) extracted cleanly from starter_code & front without leaking tests/harnesses."""
    sc = (starter_code or "").replace("\r\n", "\n").strip()
    lang = infer_fence_lang(language, sc, front)

    if not sc:
        task30_code = _extract_provided_methods_for_task30(front)
        if task30_code:
            return ("ts", task30_code)
        return (lang or "ts", "")

    if lang == "python" or (lang and lang not in ("ts", "js")):
        return (lang, _extract_python_or_other_from_starter(front, sc, lang))

    # Special case: Task 3.3 carries full OrderedSet design snippet cleanly midway through starter_code.
    if "// ---- src/organization/orderedset.ts" in sc and "TODO Task 3.3" in sc:
        t33 = _extract_orderedset_task33(sc)
        if t33:
            return ("ts", t33)

    # Strip sandbox / framework tails
    for marker in _SANDBOX_MARKERS:
        m_idx = sc.find(marker)
        if m_idx != -1:
            sc = sc[:m_idx].strip()

    lines = sc.splitlines()
    blocks = _collect_top_level_blocks(lines)
    targets = _extract_target_names(front)

    # Filter out test runner helpers / internal Op types
    type_blocks: list[str] = []
    fn_or_class_blocks: list[tuple[str, str]] = []
    for name, block_text, _ in blocks:
        first_code_line = next(
            (ln.strip() for ln in block_text.splitlines() if not _JSDOC_OR_COMMENT_RE.match(ln)),
            "",
        )
        if _SKIP_SANDBOX_TYPE_RE.match(first_code_line) or _SKIP_SANDBOX_FN_RE.match(first_code_line):
            continue
        if re.match(r"^(?:export\s+)?(?:type|interface|enum)\b", first_code_line):
            # Include type only if referenced in prompt/target functions or small domain definition set
            type_blocks.append(block_text)
        else:
            fn_or_class_blocks.append((name, block_text))

    selected_fns: list[str] = []
    target_set = set(targets)
    class_from_front = _extract_class_spec_from_front(front, targets)

    for name, block_text in fn_or_class_blocks:
        if class_from_front and re.match(rf"^(?:export\s+)?class\s+{re.escape(name)}\b", block_text.splitlines()[-1 if False else 0].strip()) and "TODO" in block_text:
            continue
        is_explicit_target = name in target_set
        is_todo = "// TODO" in block_text or "/* TODO" in block_text
        if is_explicit_target or is_todo:
            cleaned = (
                _clean_function_stub(block_text)
                if re.search(r"^(?:export\s+)?(?:async\s+)?function\b", block_text.strip(), re.M)
                else block_text
            )
            selected_fns.append(cleaned)
        elif not targets and len(fn_or_class_blocks) <= 2:
            selected_fns.append(_clean_function_stub(block_text))

    if class_from_front:
        selected_fns = class_from_front + [b for b in selected_fns if not re.match(r"^(?:export\s+)?class\b", b.strip())]

    # Filter types to those transitively referenced by selected functions/front (keep all if <= 6 types)
    base_ref_text = "\n".join(selected_fns) + "\n" + front
    if len(type_blocks) <= 6:
        kept_types = list(type_blocks)
    else:
        parsed_types: list[tuple[str, str]] = []
        for tb in type_blocks:
            m = re.search(r"\b(?:type|interface|enum)\s+([A-Za-z_$][\w$]*)", tb)
            parsed_types.append((m.group(1) if m else "", tb))
        kept_indices: set[int] = set()
        ref_pool = base_ref_text
        changed = True
        while changed:
            changed = False
            for idx, (t_name, tb) in enumerate(parsed_types):
                if idx in kept_indices:
                    continue
                if not t_name or re.search(rf"\b{re.escape(t_name)}\b", ref_pool):
                    kept_indices.add(idx)
                    ref_pool += "\n" + tb
                    changed = True
        kept_types = [tb for idx, (_, tb) in enumerate(parsed_types) if idx in kept_indices]

    parts = [p for p in ["\n".join(kept_types).strip(), "\n\n".join(selected_fns).strip()] if p]
    return ("ts", "\n\n".join(parts).strip())


def _fence_unfenced_code_in_prose(front: str, lang: str) -> str:
    """Wrap consecutive multi-line unfenced code runs or standalone signature lines in code fences."""
    lines = front.replace("\r\n", "\n").splitlines()
    out: list[str] = []
    buf: list[str] = []

    def flush_buf() -> None:
        nonlocal buf
        if len(buf) >= 2:
            fence_tag = lang or "ts"
            out.append(f"```{fence_tag}")
            out.extend(buf)
            out.append("```")
        else:
            out.extend(buf)
        buf = []

    for line in lines:
        if _STRONG_CODE_LINE_RE.match(line):
            buf.append(line)
        else:
            if buf:
                flush_buf()
            out.append(line)
    if buf:
        flush_buf()

    result = "\n".join(out)
    if _has_fenced_code(result):
        return result

    # Detect single standalone backticked typed signature line e.g. `foo(a: T): R` on its own line
    # or `Implement \`fn(complexArgs): complexReturn\`:` where signature length >= 38
    sig_match = re.search(
        r"`([A-Za-z_$][\w$.]*\([^`\n]{12,}\)\s*:\s*[^`\n]+)`",
        front,
    )
    if sig_match:
        sig = sig_match.group(1).strip()
        fence_tag = lang or infer_fence_lang(None, sig, front) or "ts"
        body = f"function {sig} {{\n  // TODO\n}}" if not sig.startswith(("function ", "async ", "def ")) else sig
        return _insert_fence_after_first_paragraph(front, fence_tag, body)

    return front


def _insert_fence_after_first_paragraph(front: str, lang: str, code_block: str) -> str:
    """Insert a fenced code block cleanly after the opening prompt paragraph (or before subheadings)."""
    fence = f"```{lang}\n{code_block}\n```" if lang else f"```\n{code_block}\n```"
    paragraphs = re.split(r"\n\s*\n", front.strip())
    if len(paragraphs) <= 1:
        return f"{front.strip()}\n\n{fence}"

    # If a subheading (### ...) appears after intro paragraphs (e.g. Task 3.0), place the fence right before it.
    for idx, p in enumerate(paragraphs):
        if idx >= 1 and re.match(r"^\s*###\s+", p):
            before = "\n\n".join(paragraphs[:idx]).rstrip()
            after = "\n\n".join(paragraphs[idx:]).lstrip()
            return f"{before}\n\n{fence}\n\n{after}"

    return f"{paragraphs[0].rstrip()}\n\n{fence}\n\n" + "\n\n".join(paragraphs[1:]).lstrip()


def _normalize_fence_pairs(text: str, inferred_lang: str) -> str:
    """Ensure opening code fences carry a language tag when known and closing fences stay bare ```."""
    lines = text.splitlines()
    out: list[str] = []
    in_fence = False
    for line in lines:
        m = re.match(r"^```([A-Za-z0-9_+#.-]*)[ \t]*$", line)
        if m:
            if not in_fence:
                in_fence = True
                lang_tag = m.group(1) or inferred_lang
                out.append(f"```{lang_tag}" if lang_tag else "```")
            else:
                in_fence = False
                out.append("```")
        else:
            out.append(line)
    return "\n".join(out)


def format_question_with_code_blocks(
    front: str,
    starter_code: str | None = None,
    language: str | None = None,
) -> str:
    """Format a card question so its code components sit in clean fenced markdown blocks for IDE rendering.

    Idempotent and safe on non-code prose cards.
    """
    raw_front = (front or "").replace("\r\n", "\n").strip()
    if not raw_front:
        return front or ""

    inferred_lang = infer_fence_lang(language, starter_code or "", raw_front)
    if _has_fenced_code(raw_front):
        return _normalize_fence_pairs(raw_front, inferred_lang)

    # 1. If card carries starter_code (or is a known code-design card like Task 3.0), extract clean question IDE block
    if (starter_code and starter_code.strip()) or (
        "AlbumArchive" in raw_front and "add(item: Album)" in raw_front
    ):
        fence_lang, code_snippet = extract_question_code_from_starter(
            raw_front, starter_code, language
        )
        if code_snippet:
            return _insert_fence_after_first_paragraph(raw_front, fence_lang, code_snippet)

    # 2. Otherwise promote any unambiguous multi-line code or typed function signature in standalone questions
    return _fence_unfenced_code_in_prose(raw_front, inferred_lang)

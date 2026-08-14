"""Turning an uploaded document into located, citable segments.

The point of this module is the *locator*. Chunking a textbook into passages
is easy; the reason to do it here rather than reuse the plain IR chunker is
that each chunk has to remember where it came from — "p. 42", "§ 3.1" — so a
card generated from it can send the user back to the reading.

So extraction is page- or heading-aware first and length-aware second: a PDF
is split on page boundaries (pypdf gives us those), Markdown on headings, and
only then is an over-long unit packed down to a readable size by the existing
IR chunker, with every piece inheriting its parent's locator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.ir_service import chunk_text, extract_readable

MAX_DOCUMENT_BYTES = 25 * 1024 * 1024
# Long enough for a textbook chapter, bounded so one upload can't wedge the
# generation step behind thousands of LLM calls.
MAX_SEGMENTS = 2000

SUPPORTED_SUFFIXES = (".pdf", ".txt", ".md", ".markdown", ".html", ".htm", ".rst")

HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", re.M)


class DocumentError(ValueError):
    """The upload could not be turned into text worth studying."""


@dataclass
class Segment:
    """One citable piece of a document."""

    locator: str
    text: str


def supported(filename: str) -> bool:
    return (filename or "").lower().endswith(SUPPORTED_SUFFIXES)


def extract_document(filename: str, data: bytes) -> tuple[str, list[Segment]]:
    """(title, segments) for an uploaded file.

    Raises DocumentError with something the user can act on — an unreadable
    upload should say *why*, since "0 cards generated" three steps later is a
    miserable way to discover a scanned PDF has no text layer.
    """
    name = (filename or "document").strip()
    lower = name.lower()
    if not data:
        raise DocumentError("the uploaded file is empty")

    if lower.endswith(".pdf"):
        title, segments = _extract_pdf(name, data)
    elif lower.endswith((".html", ".htm")):
        html = _decode(data)
        title, text = extract_readable(html, fallback_title=_stem(name))
        segments = _segment_text(text)
    elif lower.endswith(SUPPORTED_SUFFIXES):
        text = _decode(data)
        title = _markdown_title(text) or _stem(name)
        segments = _segment_text(text)
    else:
        raise DocumentError(
            f"unsupported file type; upload one of: {', '.join(SUPPORTED_SUFFIXES)}"
        )

    segments = [s for s in segments if s.text.strip()][:MAX_SEGMENTS]
    if not segments:
        raise DocumentError(
            "no readable text was found in this document — a scanned PDF needs OCR first"
        )
    return title or _stem(name), segments


def _decode(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def _stem(filename: str) -> str:
    return re.sub(r"\.[A-Za-z0-9]{1,8}$", "", filename.rsplit("/", 1)[-1]) or "Document"


def _markdown_title(text: str) -> str:
    match = HEADING_RE.search(text)
    return match.group(2).strip() if match else ""


def _extract_pdf(filename: str, data: bytes) -> tuple[str, list[Segment]]:
    import io

    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise DocumentError("PDF support requires pypdf") from exc

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise DocumentError(f"could not read the PDF: {exc}") from exc

    if getattr(reader, "is_encrypted", False):
        # An empty user password is common on "protected" PDFs and costs
        # nothing to try before refusing the upload.
        try:
            reader.decrypt("")
        except Exception as exc:
            raise DocumentError("this PDF is password-protected") from exc

    title = ""
    try:
        meta = reader.metadata
        title = (getattr(meta, "title", "") or "").strip()
    except Exception:
        title = ""

    segments: list[Segment] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            continue
        text = _tidy(text)
        if not text:
            continue
        # A page is the citable unit; a long one is packed down but every
        # piece keeps the page number.
        for piece in chunk_text(text) or [text]:
            segments.append(Segment(locator=f"p. {i}", text=piece))

    return title or _stem(filename), segments


def _segment_text(text: str) -> list[Segment]:
    """Split on Markdown headings when present, else on length alone."""
    text = _tidy(text)
    if not text:
        return []

    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [
            Segment(locator=f"part {i}", text=piece)
            for i, piece in enumerate(chunk_text(text), start=1)
        ]

    segments: list[Segment] = []
    # Anything before the first heading is still content worth keeping.
    preamble = text[: matches[0].start()].strip()
    if preamble:
        for piece in chunk_text(preamble):
            segments.append(Segment(locator="introduction", text=piece))

    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        heading = match.group(2).strip()
        body = text[match.end() : end].strip()
        if not body:
            continue
        for piece in chunk_text(body):
            segments.append(Segment(locator=heading[:120], text=piece))
    return segments


def _tidy(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # PDF extraction routinely leaves hyphenated line breaks mid-word.
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def normalize_for_match(text: str) -> str:
    """Whitespace- and case-insensitive form used to verify a quote.

    Models reflow whitespace and normalise dashes/quotes when copying a span,
    so a strict substring test would reject genuine citations.
    """
    text = (text or "").lower()
    # Escapes rather than the literal glyphs: these are near-indistinguishable
    # from ASCII in a source file, which is exactly the confusion this
    # function exists to undo.
    text = text.replace("\u2019", "'").replace("\u2018", "'")  # curly single quotes
    text = text.replace("\u201c", '"').replace("\u201d", '"')  # curly double quotes
    text = re.sub("[\u2010-\u2015]", "-", text)  # hyphen .. horizontal bar
    return re.sub(r"\s+", " ", text).strip()


def quote_is_grounded(quote: str, passage: str) -> bool:
    """Did the model actually copy this span out of the passage?

    A citation the reader cannot find in the source is worse than no citation,
    so anything that fails this check is not shown as a quote.
    """
    q, p = normalize_for_match(quote), normalize_for_match(passage)
    if len(q) < 12 or not p:
        return False
    return q in p

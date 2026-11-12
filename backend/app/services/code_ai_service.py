"""AI Code Generator, Socratic Code Tutor & Multilingual Code Evaluator.

Runs on the local Ollama model, through the same client as grading.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.services.grading_service import GradingService, GradingUnavailable

log = logging.getLogger(__name__)

FORGE_PROBLEM_PROMPT = """You are a senior algorithmic problem designer for software engineering, university software construction courses (e.g. CPSC 210), and technical interviews.
Generate a structured, complete coding challenge based on the requested topic.

Topic/Concept: {topic}
Difficulty: {difficulty}
Target Primary Language: {target_language}

Requirements:
1. Clear problem statement with formatted markdown, mathematical notation ($O(N)$), and constraints. Place any code snippets, function/class signatures, or type definitions inside the problem statement in fenced markdown code blocks (e.g. ```typescript ... ``` or ```python ... ```) so they render in an IDE.
2. 2-3 comprehensive examples with Input, Output, and Explanation.
3. Realistic constraints (e.g. array length, integer bounds, valid types).
4. Idiomatic starter code with function/class definition and docstring:
   - For TypeScript: if modeling Result or fallible operations, use the standard CPSC 210 Result type with 'error':
     type Result<T, E = string> = {{ ok: true; value: T }} | {{ ok: false; error: E }};
   - For async operations, use modern async/await and Promise signatures.
5. Unit Testing Suite (`starter_tests`) using CPSC 210 conventions:
   - Use `test('description', checkExpect(() => actual, expected))` where checkExpect takes the actual call thunk first, expected second.
   - For error testing on functions that throw: `test('description', checkError(() => actualFunctionCall(), 'expected error message'))`.
   - For unwrapping / checking Result types: use `assertOk(r)` (returns value) and `assertErr(r)` (returns error).
   - For async tests: use `checkExpect(async () => await asyncFn(...), expected)`.
   - Include normal cases, boundary threshold limits, and error/Result edge cases.
6. Optimal reference solution with comments.
7. In-depth editorial explaining pattern intuition, step-by-step walkthrough, and time/space complexity proof.
8. 4-6 diverse test cases (including edge cases like empty, single element, threshold bounds, duplicates).
9. 3 progressive hints (Conceptual -> Directional -> Edge Case).

Respond with ONLY a JSON object conforming to this schema:
{{
  "title": "Problem Title",
  "slug": "problem-slug",
  "difficulty": "{difficulty}",
  "category": "Algorithmic Category (e.g. Control Flow, Recursion, Result Types, Async, Testing)",
  "tags": ["Array", "Result", "Testing"],
  "description": "Full problem description in markdown",
  "examples": [
    {{"input": "...", "output": "...", "explanation": "..."}}
  ],
  "constraints": ["1 <= nums.length <= 10^5", "-10^9 <= nums[i] <= 10^9"],
  "starter_codes": {{
    "python": "class Solution:\\n    def solve(self, nums: list[int]) -> int:\\n        pass\\n",
    "typescript": "function solve(nums: number[]): number {{\\n    return 0;\\n}}\\n"
  }},
  "starter_tests": "// Unit Testing Suite\\ntest('sample case', checkExpect(() => solve([1, 2, 3]), 3));\\n\\ntest('boundary threshold', checkExpect(() => solve([]), 0));\\n",
  "solutions": {{
    "python": "class Solution:\\n    def solve(self, nums: list[int]) -> int:\\n        return len(nums)\\n",
    "typescript": "function solve(nums: number[]): number {{\\n    return nums.length;\\n}}\\n"
  }},
  "editorial": "### Intuition\\n...\\n### Complexity\\n- Time: $O(N)$\\n- Space: $O(1)$",
  "test_cases": [
    {{"input": {{"nums": [1, 2, 3]}}, "expected": 3}}
  ],
  "hints": ["Hint 1...", "Hint 2...", "Hint 3..."]
}}
"""

SOCRATIC_CODE_PROMPT = """You are a Socratic Code Tutor and Algorithm Coach.
A learner is working on a coding problem and has requested guidance.

Problem Title: {title}
Problem Description:
{description}

Learner's Current Code ({language}):
```{language}
{code}
```

Learner's Inquiry / Request Type: {hint_type}
- If 'conceptual': Guide them toward the right algorithmic pattern or invariant without revealing code or spoiling the exact answer.
- If 'edge_case': Point out unhandled boundary conditions (empty lists, duplicates, negative numbers, overflow) by asking leading questions.
- If 'complexity': Explain how their current approach scales (e.g., $O(N^2)$ vs $O(N)$) and suggest an alternate data structure to optimize it.
- If 'debug': Explain the conceptual mistake or logical bug on the offending line without writing the fixed code for them.

Respond with concise, encouraging, Socratic feedback formatted in clean markdown (2-3 short paragraphs max).
"""

OCCAMS_SOCRATIC_EXPLAIN_PROMPT = """You are an expert software engineer and computer science pedagogue applying Occam's Razor and the Socratic method.
A programmer has highlighted a specific section of code and requested an Occam's razor / Socratic concise explanation.

Programming Language: {language}
{context_info}
Selected Code Snippet:
```{language}
{selected_code}
```
{full_code_section}

Mode Requested: {mode}

Instructions:
1. Conciseness is paramount. Maximum 3-4 sentences total. No conversational filler ("Certainly! Here is...", "This code...", "In this snippet...").
2. Occam's Razor: Eliminate all unnecessary assumptions, fluff, and boilerplate. Explain what this code fundamentally achieves and the single reason it exists in the simplest possible terms.
3. Socratic Insight: State the core invariant or ask a sharp diagnostic question that prompts deep realization of *why* it is designed this way or what edge case it protects against.
4. Format directly as:
{format_instruction}
5. Bold key terms and invariants so it can be skimmed in under 5 seconds.
"""

DECK_DOCS_GROUNDING_PROMPT = """You are a precise technical tutor explaining code grounded strictly in the attached course documentation.
A student highlighted a line or block of code from a card and wants to understand its concise meaning and application according to the course documentation.

Instructions:
1. Grounding: Identify the cited document title and page/locator where this specification comes from (e.g., [Title · Locator]).
2. Verbatim Specification: Quote the exact sentence, rule, formula, threshold, or example from the document that specifies this card or function.
3. Meaning & Application: In 2-3 concise sentences, explain the exact meaning and application of this highlighted code for this card based on the document:
   - What does this line test, calculate, or enforce?
   - How do the document's rules, formulas, or thresholds apply to these specific inputs or logic? (e.g. show the math or condition: 18 / 20 = 90% >= 80% threshold -> 'A').
4. Respect any Reference Solution Disclosure Rule if present below, and use any Card Question / Student Work context to make your explanation directly relevant.
5. Keep it direct, clean, and concise. Zero conversational filler.
6. Use clean markdown formatting without extraneous whitespace around code tokens or punctuation.

Format your response strictly using these section headers:
**→ Cited Document.** [Source Title · Locator]
**→ Verbatim Specification.**
> <Exact quote, formula, or example from the document>
**→ Meaning & Application.** <Concise explanation of what this highlighted code means and how the document rules apply to it>
{card_context_section}{student_work_section}
Highlighted Code:
```{language}
{query}
```

Attached Course Documentation:
{doc_excerpts}
"""

DECK_DOCS_QA_PROMPT = """You are a precise, insightful technical tutor helping a student understand their code, attached course documentation, and programming concepts.
A student is working on a coding flashcard/problem and has a question about the card, their work, the code, or documentation.

Instructions:
1. Provide a direct, technically accurate, clear, and educational answer to the student's question.
2. Synthesize BOTH the attached course documentation and your general pre-trained programming knowledge and language capabilities ({language}):
   - If the attached documentation specifies rules, formulas, constraints, or course conventions, incorporate and adhere to them.
   - Use your pre-trained software engineering knowledge to explain underlying mechanics, language semantics, standard library behavior, algorithmic complexity, common pitfalls, and edge cases.
   - If no attached documentation is found or if the documentation is silent on this detail, provide a complete and authoritative answer drawn from your pre-trained programming knowledge.
3. Use the Card Question, Canonical Reference Solution, and Student's Current Work below whenever available to diagnose bugs, check edge cases, and tailor your answer (strictly honoring any Reference Solution Disclosure Rule).
4. Be concise and structured (typically 2-4 focused sentences or clean bullet points). Zero conversational filler (do NOT say "Sure!", "Great question!", "Certainly!", "As an AI...").
5. Use markdown backticks (`code`) for code tokens and bold for key terms.
{card_context_section}{student_work_section}
Highlighted / Focused Code:
```{language}
{selected_code}
```

Attached Course Documentation:
{doc_excerpts}
{history_section}

Student Question:
{question}
"""


def _build_card_and_work_sections(
    *,
    language: str,
    context: str | None = None,
    card_front: str | None = None,
    card_back: str | None = None,
    card_tests: str | None = None,
    card_weaknesses: list[str] | None = None,
    user_code: str | None = None,
    user_test_code: str | None = None,
    execution_summary: str | None = None,
    full_code: str | None = None,
    focus_code: str | None = None,
    revealed: bool | None = None,
) -> tuple[str, str]:
    """Builds the immutable card prefix followed by the mutable student-work snapshot.

    Keeping instructions + card question/solution at the front of the prompt keeps
    leading tokens identical across turns so local Ollama and upstream providers can
    reuse prefix KV cache entries while edits/doc excerpts/questions append at the tail.
    """
    prefix_parts: list[str] = []
    if card_front and card_front.strip():
        prefix_parts.append(f"Card Question / Specification:\n{card_front.strip()[:4500]}")
    elif context and context.strip():
        prefix_parts.append(f"Card / Problem Context:\n{context.strip()[:4500]}")

    has_ref = bool(card_back and card_back.strip())
    if has_ref:
        prefix_parts.append(
            f"Canonical Reference Solution:\n```{language}\n{card_back.strip()[:4500]}\n```"
        )
    if card_tests and card_tests.strip():
        prefix_parts.append(
            f"Card Reference / Starter Tests:\n```{language}\n{card_tests.strip()[:2500]}\n```"
        )
    if card_weaknesses:
        weak_list = "\n".join(f"- {w}" for w in card_weaknesses[:5] if str(w).strip())
        if weak_list:
            prefix_parts.append(f"Recorded Prior Weaknesses on This Card:\n{weak_list}")

    card_context_section = ("\n" + "\n\n".join(prefix_parts) + "\n") if prefix_parts else ""

    work_parts: list[str] = []
    if has_ref:
        if revealed is False:
            work_parts.append(
                "Reference Solution Disclosure Rule: The student has NOT revealed the reference solution yet. "
                "Use the Canonical Reference Solution silently to verify correctness and spot bugs, and coach/answer "
                "WITHOUT printing or quoting the complete reference implementation verbatim."
            )
        elif revealed is True:
            work_parts.append(
                "Reference Solution Disclosure Rule: The reference solution is currently revealed to the student; you may discuss it openly."
            )

    focus_clean = (focus_code or "").strip()
    if user_code is not None and user_code.strip():
        work_parts.append(
            f"Student's Current Solution Draft:\n```{language}\n{user_code.strip()[:4500]}\n```"
        )
    if (
        full_code
        and full_code.strip()
        and full_code.strip() != focus_clean
        and full_code.strip() != (user_code or "").strip()
        and full_code.strip() != (card_back or "").strip()
    ):
        work_parts.append(
            f"Full Surrounding Editor Buffer:\n```{language}\n{full_code.strip()[:4500]}\n```"
        )
    if user_test_code and user_test_code.strip():
        work_parts.append(
            f"Student's Current Unit Tests:\n```{language}\n{user_test_code.strip()[:3000]}\n```"
        )
    if execution_summary and execution_summary.strip():
        work_parts.append(f"Latest Test Run / Execution Output:\n{execution_summary.strip()[:2500]}")

    student_work_section = ("\n" + "\n\n".join(work_parts) + "\n") if work_parts else ""
    return card_context_section, student_work_section




def rank_extracts_for_query(
    query: str,
    extracts_with_sources: list[Any],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Rank extracts based on token overlap, identifier matches, and substring containment."""
    if not extracts_with_sources:
        return []

    cleaned_query = (query or "").strip().lower()
    raw_tokens = re.findall(r"[a-z0-9_]{2,}", cleaned_query)

    common_tokens = {
        "the", "and", "for", "with", "that", "this", "from", "are", "not",
        "let", "var", "const", "def", "func", "function", "return", "class",
        "import", "export", "type", "interface", "public", "private", "true", "false", "null",
        "number", "string", "boolean", "void", "any", "list", "dict", "int", "float",
    }

    keywords = [t for t in raw_tokens if t not in common_tokens]
    if not keywords:
        keywords = raw_tokens

    scored_items: list[tuple[float, Any, Any]] = []

    for item in extracts_with_sources:
        if hasattr(item, "_mapping") or isinstance(item, (tuple, list)):
            extract = item[0]
            source = item[1] if len(item) > 1 else None
        else:
            extract = getattr(item, "Extract", getattr(item, "extract", item))
            source = getattr(item, "Source", getattr(item, "source", None))

        text = (getattr(extract, "content", "") or "").lower()
        title = (getattr(source, "title", "") or "").lower()
        score = 0.0

        if len(cleaned_query) > 5 and cleaned_query in text:
            score += 50.0

        for kw in keywords:
            if kw in title:
                score += 5.0
            # Exact word boundary match gets heavy boost
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                score += 30.0
            count = text.count(kw)
            if count > 0:
                score += min(count, 5) * (4.0 if len(kw) >= 5 else 2.0)

        if score > 0.0:
            scored_items.append((score, extract, source))

    scored_items.sort(key=lambda x: x[0], reverse=True)

    results: list[dict[str, Any]] = []
    for score, extract, source in scored_items[:top_k]:
        results.append(
            {
                "extract_id": str(getattr(extract, "id", "")),
                "source_id": str(getattr(source, "id", "")) if source else "",
                "source_title": getattr(source, "title", "Deck Document") if source else "Deck Document",
                "locator": getattr(extract, "locator", "General") or "General",
                "content": getattr(extract, "content", ""),
                "score": round(score, 2),
            }
        )

    return results


class CodeAiService:
    def __init__(self, model: str | None = None, *, allow_antigravity: bool = False) -> None:
        self.grading_service = GradingService(model=model, allow_antigravity=allow_antigravity)

    @classmethod
    def for_user(cls, user: Any | None, requested_model: str | None = None) -> CodeAiService:
        grading_svc = GradingService.for_user(user, requested_model)
        svc = cls.__new__(cls)
        svc.grading_service = grading_svc
        return svc

    async def _list_available_models(self, target_model: str) -> list[str]:
        from app.services.grading_service import is_allowed_qwen_coder_model, is_antigravity_model

        allow_agy = getattr(self.grading_service, "allow_antigravity", False)
        try:
            if type(self.grading_service).verify_engine is GradingService.verify_engine:
                engines = await self.grading_service.verify_all_engines()
                combined = list(
                    dict.fromkeys([
                        *engines["ollama"]["models"],
                        *(engines["antigravity"]["models"] if allow_agy else []),
                    ])
                )
                return combined or [target_model]

            installed = await self.grading_service.verify_engine()
            filtered = [
                m
                for m in installed
                if is_allowed_qwen_coder_model(m) or (allow_agy and is_antigravity_model(m))
            ]
            return filtered or installed or [target_model]
        except Exception:
            return [target_model]

    async def forge_problem(
        self,
        topic: str,
        difficulty: str = "Medium",
        target_language: str = "python",
    ) -> dict[str, Any]:
        """Generates a new coding problem challenge using Qwen 2.5 Coder."""
        prompt = FORGE_PROBLEM_PROMPT.format(
            topic=topic,
            difficulty=difficulty,
            target_language=target_language,
        )

        try:
            raw_response = await self.grading_service._generate(
                prompt=prompt,
                model=self.grading_service.model,
            )
        except Exception as e:
            log.warning("Qwen generation failed for forge_problem: %s", e)
            raise GradingUnavailable(f"AI problem generation failed: {e}") from e

        # Parse JSON
        clean_json = raw_response.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]

        try:
            data = json.loads(clean_json.strip())
            return data
        except json.JSONDecodeError as exc:
            # Fallback regex extraction
            match = re.search(r"\{.*\}", clean_json, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise GradingUnavailable("Failed to parse structured problem JSON from AI.") from exc

    async def socratic_hint(
        self,
        title: str,
        description: str,
        language: str,
        code: str,
        hint_type: str = "conceptual",
    ) -> str:
        """Generates Socratic tutoring feedback for user's code."""
        prompt = SOCRATIC_CODE_PROMPT.format(
            title=title,
            description=description,
            language=language,
            code=code or "# (no code written yet)",
            hint_type=hint_type,
        )

        try:
            response = await self.grading_service._generate(
                prompt=prompt,
                model=self.grading_service.model,
            )
            return response.strip()
        except Exception as e:
            log.warning("Socratic code hint failed on '%s': %s", self.grading_service.model, e)
            raise GradingUnavailable(
                f"Socratic code hint failed on '{self.grading_service.model}': {e}"
            ) from e

    async def explain_code_selection(
        self,
        selected_code: str,
        full_code: str | None = None,
        language: str = "typescript",
        context: str | None = None,
        mode: str = "both",
        model: str | None = None,
    ) -> dict[str, Any]:
        """Generates an Occam's razor / Socratic concise explanation of the selected code."""
        context_info = f"Context / Task: {context}\n" if context else ""
        full_code_section = (
            f"\nFull Surrounding Code:\n```{language}\n{full_code.strip()}\n```\n"
            if full_code and full_code.strip() and full_code.strip() != selected_code.strip()
            else ""
        )

        if mode == "occams_razor":
            format_instruction = (
                "**→ Occam's Razor.** <Simplest 1-2 sentence explanation of the mechanism and fundamental purpose>"
            )
        elif mode == "socratic":
            format_instruction = (
                "**→ Socratic Insight.** <Core invariant or sharp diagnostic question on why it is designed this way>"
            )
        else:
            format_instruction = (
                "**→ Occam's Razor.** <Simplest 1-2 sentence explanation of the mechanism and fundamental purpose>\n\n"
                "**→ Socratic Insight.** <Core invariant or sharp diagnostic question on why it is designed this way>"
            )

        prompt = OCCAMS_SOCRATIC_EXPLAIN_PROMPT.format(
            language=language,
            context_info=context_info,
            selected_code=selected_code.strip(),
            full_code_section=full_code_section,
            mode=mode,
            format_instruction=format_instruction,
        )

        target_model = model or self.grading_service.model
        available_models = await self._list_available_models(target_model)

        try:
            raw_response = await self.grading_service._generate(
                prompt=prompt,
                model=target_model,
                allow_smaller_model=False,
            )
            explanation = raw_response.strip()
        except Exception as e:
            log.warning("Occam's razor explanation generation failed: %s", e)
            raise GradingUnavailable(f"LLM explanation failed on '{target_model}': {e}") from e

        occams_razor: str | None = None
        socratic_insight: str | None = None

        # Extract Occam's Razor portion if formatted
        if "**→ Occam's Razor.**" in explanation:
            after_occams = explanation.split("**→ Occam's Razor.**", 1)[1]
            if "**→ Socratic Insight.**" in after_occams:
                occams_razor = after_occams.split("**→ Socratic Insight.**", 1)[0].strip()
            else:
                occams_razor = after_occams.strip()

        # Extract Socratic Insight portion if formatted
        if "**→ Socratic Insight.**" in explanation:
            socratic_insight = explanation.split("**→ Socratic Insight.**", 1)[1].strip()

        model_used = self.grading_service.last_used_model or target_model

        return {
            "explanation": explanation,
            "occams_razor": occams_razor,
            "socratic_insight": socratic_insight,
            "model_used": model_used,
            "available_models": available_models,
        }

    async def query_deck_docs(
        self,
        query: str,
        doc_excerpts: list[dict[str, Any]],
        full_code: str | None = None,
        language: str = "typescript",
        model: str | None = None,
        context: str | None = None,
        card_front: str | None = None,
        card_back: str | None = None,
        card_tests: str | None = None,
        card_weaknesses: list[str] | None = None,
        user_code: str | None = None,
        user_test_code: str | None = None,
        execution_summary: str | None = None,
        revealed: bool | None = None,
    ) -> dict[str, Any]:
        """Grounds a code snippet or user inquiry against attached deck documentation."""
        target_model = model or self.grading_service.model
        available_models = await self._list_available_models(target_model)

        if not doc_excerpts:
            return {
                "found_info": "No documentation excerpts available to ground this code snippet.",
                "doc_citation": None,
                "verbatim_passage": None,
                "explanation": "Upload documentation (.pdf, .md, .txt, code files) to this deck to cross-reference specifications.",
                "key_takeaway": "No grounding documentation attached to this deck.",
                "citations": [],
                "model_used": target_model,
                "available_models": available_models,
            }

        formatted_excerpts = []
        for idx, exc in enumerate(doc_excerpts, 1):
            formatted_excerpts.append(
                f"[Document: {exc['source_title']} · {exc.get('locator') or 'General'}]\n{exc['content']}\n"
            )
        doc_excerpts_str = "\n".join(formatted_excerpts)

        card_context_section, student_work_section = _build_card_and_work_sections(
            language=language,
            context=context,
            card_front=card_front,
            card_back=card_back,
            card_tests=card_tests,
            card_weaknesses=card_weaknesses,
            user_code=user_code,
            user_test_code=user_test_code,
            execution_summary=execution_summary,
            full_code=full_code,
            focus_code=query,
            revealed=revealed,
        )

        prompt = DECK_DOCS_GROUNDING_PROMPT.format(
            language=language,
            card_context_section=card_context_section,
            student_work_section=student_work_section,
            query=query.strip(),
            doc_excerpts=doc_excerpts_str,
        )

        try:
            raw_response = await self.grading_service._generate(
                prompt=prompt,
                model=target_model,
                allow_smaller_model=False,
            )
            raw = raw_response.strip()
        except Exception as e:
            log.warning("Deck docs query generation failed: %s", e)
            raise GradingUnavailable(f"LLM documentation search failed on '{target_model}': {e}") from e

        found_info = ""
        doc_citation: str | None = None
        verbatim_passage: str | None = None
        explanation: str | None = None
        key_takeaway: str | None = None

        # Regex search tolerant of ->, →, ###, asterisks, colons, case
        sec_cit = re.search(
            r"(?:\*{0,2}(?:→|->|#+)?\s*Cited Document[:\.]?\*{0,2})\s*([^\n\r]+)",
            raw,
            re.IGNORECASE,
        )
        if sec_cit:
            doc_citation = sec_cit.group(1).strip()
            m = re.search(r"\[(.*?)\]", doc_citation)
            if m:
                doc_citation = f"[{m.group(1)}]"
            elif doc_citation and not doc_citation.startswith("["):
                doc_citation = f"[{doc_citation}]"

        sec_verb = re.search(
            r"(?:\*{0,2}(?:→|->|#+)?\s*Verbatim Specification[:\.]?\*{0,2})\s*(.*?)(?=(?:\*{0,2}(?:→|->|#+)?\s*(?:Meaning|Relevant Rules|Documentation Details|Explanation|Key Takeaway))|\Z)",
            raw,
            re.DOTALL | re.IGNORECASE,
        )
        if sec_verb:
            verbatim_passage = sec_verb.group(1).strip().strip(">").strip()

        sec_meaning = re.search(
            r"(?:\*{0,2}(?:→|->|#+)?\s*(?:Meaning\s*(?:&|and)\s*Application|Relevant Rules|Documentation Details|Explanation)[:\.]?\*{0,2})\s*(.*?)(?=(?:\*{0,2}(?:→|->|#+)?\s*Key Takeaway)|\Z)",
            raw,
            re.DOTALL | re.IGNORECASE,
        )
        if sec_meaning:
            explanation = sec_meaning.group(1).strip()

        sec_key = re.search(
            r"(?:\*{0,2}(?:→|->|#+)?\s*Key Takeaway[:\.]?\*{0,2})\s*(.*)",
            raw,
            re.DOTALL | re.IGNORECASE,
        )
        if sec_key:
            key_takeaway = sec_key.group(1).strip()

        found_info = explanation or verbatim_passage or raw

        if not doc_citation:
            cit_match = re.search(r"\[(.*?)\]", raw)
            if cit_match:
                doc_citation = cit_match.group(0)

        if not doc_citation and doc_excerpts:
            top = doc_excerpts[0]
            doc_citation = f"[{top['source_title']} · {top.get('locator') or 'General'}]"

        # Fallback to top excerpt text if verbatim_passage is not extracted or too short
        if (not verbatim_passage or len(verbatim_passage) < 10) and doc_excerpts:
            top = doc_excerpts[0]
            top_content = top.get("content", "").strip()
            if top_content:
                verbatim_passage = top_content

        model_used = self.grading_service.last_used_model or target_model

        return {
            "found_info": found_info,
            "doc_citation": doc_citation,
            "verbatim_passage": verbatim_passage,
            "explanation": explanation,
            "key_takeaway": key_takeaway,
            "citations": doc_excerpts,
            "model_used": model_used,
            "available_models": available_models,
        }

    async def ask_deck_question(
        self,
        question: str,
        doc_excerpts: list[dict[str, Any]],
        selected_code: str | None = None,
        full_code: str | None = None,
        language: str = "typescript",
        history: list[Any] | None = None,
        model: str | None = None,
        context: str | None = None,
        card_front: str | None = None,
        card_back: str | None = None,
        card_tests: str | None = None,
        card_weaknesses: list[str] | None = None,
        user_code: str | None = None,
        user_test_code: str | None = None,
        execution_summary: str | None = None,
        revealed: bool | None = None,
    ) -> dict[str, Any]:
        """Answers a student's follow-up question grounded in card context, student work, code, and attached deck documentation."""
        target_model = model or self.grading_service.model
        available_models = await self._list_available_models(target_model)

        formatted_excerpts = []
        for exc in doc_excerpts:
            formatted_excerpts.append(
                f"[Document: {exc['source_title']} · {exc.get('locator') or 'General'}]\n{exc['content']}\n"
            )
        doc_excerpts_str = (
            "\n".join(formatted_excerpts)
            if formatted_excerpts
            else "(No attached course documentation extracts found; answer using pre-trained programming knowledge)"
        )

        card_context_section, student_work_section = _build_card_and_work_sections(
            language=language,
            context=context,
            card_front=card_front,
            card_back=card_back,
            card_tests=card_tests,
            card_weaknesses=card_weaknesses,
            user_code=user_code,
            user_test_code=user_test_code,
            execution_summary=execution_summary,
            full_code=full_code,
            focus_code=selected_code,
            revealed=revealed,
        )

        formatted_history = []
        if history:
            for turn in history[-12:]:
                role = getattr(turn, "role", None) or (turn.get("role") if isinstance(turn, dict) else "user")
                content = getattr(turn, "content", None) or (turn.get("content") if isinstance(turn, dict) else str(turn))
                role_label = "Student" if role == "user" else "Tutor"
                formatted_history.append(f"{role_label}: {content}")
        history_section = "\nPrior Discussion:\n" + "\n".join(formatted_history) if formatted_history else ""

        prompt = DECK_DOCS_QA_PROMPT.format(
            language=language,
            card_context_section=card_context_section,
            student_work_section=student_work_section,
            selected_code=(selected_code or "").strip() or "(No specific code highlighted)",
            history_section=history_section,
            doc_excerpts=doc_excerpts_str,
            question=question.strip(),
        )

        try:
            raw_response = await self.grading_service._generate(
                prompt=prompt,
                model=target_model,
                allow_smaller_model=False,
            )
            raw = raw_response.strip()
        except Exception as e:
            log.warning("Deck docs question generation failed: %s", e)
            raise GradingUnavailable(f"LLM documentation question failed on '{target_model}': {e}") from e

        doc_citation: str | None = None
        if doc_excerpts:
            top = doc_excerpts[0]
            doc_citation = f"[{top['source_title']} · {top.get('locator') or 'General'}]"

        model_used = self.grading_service.last_used_model or target_model
        extracted_glosses = extract_term_definitions_from_qa(
            question=question,
            answer=raw,
            selected_code=selected_code,
            doc_citation=doc_citation,
            language=language,
        )

        return {
            "answer": raw,
            "doc_citation": doc_citation,
            "citations": doc_excerpts,
            "model_used": model_used,
            "available_models": available_models,
            "extracted_glosses": extracted_glosses,
        }


_META_DEFINITION_HEADINGS = {
    "answer",
    "note",
    "notes",
    "summary",
    "why",
    "here's why",
    "heres why",
    "example",
    "examples",
    "result",
    "output",
    "warning",
    "tip",
    "explanation",
    "key takeaway",
    "takeaway",
    "meaning",
    "context",
    "context in codebase",
    "solution",
    "reference",
    "rule",
    "invariant",
}

_STOP_SUBJECT_WORDS = {
    "it",
    "that",
    "code",
    "line",
    "lines",
    "method",
    "function",
    "following",
    "terms",
    "the",
    "a",
    "an",
    "these",
    "those",
    "here",
    "snippet",
    "expression",
}


def canonical_term_key(term: str) -> str:
    """Normalize a term string for deduplication without colliding distinct identifiers."""
    t = (term or "").strip().lower()
    if t.startswith("."):
        t = t[1:]
    t = re.sub(r"\([^)]*\)$", "", t)
    return t.strip()


def extract_term_definitions_from_qa(
    question: str,
    answer: str,
    selected_code: str | None = None,
    doc_citation: str | None = None,
    language: str = "typescript",
) -> list[dict[str, Any]]:
    """Extracts structured term definitions from an Ask Local LLM Q&A exchange."""
    if not answer or not answer.strip():
        return []

    from datetime import UTC, datetime

    now_iso = datetime.now(UTC).isoformat()
    results: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    patterns = [
        re.compile(
            r"^\s*(?:[-*•+]|\d+[.)])\s+(?:\*{1,2})?`([^`\n]{1,64})`(?:\*{1,2})?\s*(?::|—|–|-\s+)\s*(.+)$"
        ),
        re.compile(
            r"^\s*(?:[-*•+]|\d+[.)])\s+\*\*([^*\n:]{1,64})\*\*\s*(?::|—|–|-\s+)\s*(.+)$"
        ),
        re.compile(
            r"^\s*(?:[-*•+]|\d+[.)])\s+([A-Za-z_$.][A-Za-z0-9_$.()<>\[\]]{0,48})\s*:\s+(.{8,})$"
        ),
        re.compile(
            r"^\s*(?:\*{1,2})?`([^`\n]{1,48})`(?:\*{1,2})?\s*:\s+(.{10,})$"
        ),
    ]

    for line in answer.splitlines():
        for pat in patterns:
            m = pat.match(line)
            if m:
                raw_term = m.group(1).strip().rstrip(":").strip()
                raw_def = m.group(2).strip()
                if not raw_term or not raw_def:
                    break
                if raw_term.lower() in _META_DEFINITION_HEADINGS:
                    break
                key = canonical_term_key(raw_term)
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    results.append(
                        {
                            "term": raw_term,
                            "definition": raw_def,
                            "domain": language or "Code",
                            "context_explanation": f"Cited: {doc_citation}" if doc_citation else None,
                            "source": "Ask Local LLM",
                            "pinned_at": now_iso,
                        }
                    )
                break

    if results:
        return results

    q_clean = (question or "").strip()
    is_definitional_q = bool(
        re.search(
            r"\b(?:explain|define|what\s+(?:is|are|does|do)|meaning\s+of|purpose\s+of|role\s+of|how\s+does|why\s+(?:do\s+we\s+)?use|what\s+happens\s+if)\b",
            q_clean,
            re.IGNORECASE,
        )
    )
    if not is_definitional_q:
        return []

    candidate_term: str | None = None
    backticked = re.findall(r"`([^`\n]{1,48})`", q_clean)
    if backticked:
        candidate_term = backticked[0].strip()
    else:
        trig = re.search(
            r"(?:what\s+(?:is|are|does)|define|explain|meaning\s+of|purpose\s+of|role\s+of|(?:don'?t|do\s+not|not)?\s*use)\s+([.`'\"]?[A-Za-z_$.][A-Za-z0-9_$.()]{0,40}[`'\"]?)",
            q_clean,
            re.IGNORECASE,
        )
        if trig:
            word = trig.group(1).lstrip("`'\"").rstrip("`'\"?.!,")
            if word.lower() not in _STOP_SUBJECT_WORDS:
                candidate_term = word

    if not candidate_term and selected_code:
        sel = selected_code.strip()
        if re.fullmatch(r"\.?[A-Za-z_$][A-Za-z0-9_$.()]{0,40}", sel):
            candidate_term = sel

    if candidate_term:
        clean_ans = re.sub(r"\s+", " ", answer.strip())
        if len(clean_ans) > 420:
            clean_ans = clean_ans[:417].rsplit(" ", 1)[0] + "..."
        results.append(
            {
                "term": candidate_term,
                "definition": clean_ans,
                "domain": language or "Code",
                "context_explanation": f"Cited: {doc_citation}" if doc_citation else None,
                "source": "Ask Local LLM",
                "pinned_at": now_iso,
            }
        )

    return results


def merge_lexicon_glosses(
    existing: list[dict[str, Any]] | None,
    new_entries: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Merge newly extracted glosses into existing card glosses, deduplicating by canonical term."""
    merged: list[dict[str, Any]] = [dict(g) for g in (existing or []) if isinstance(g, dict) and g.get("term")]
    index_by_key: dict[str, int] = {}
    for idx, g in enumerate(merged):
        k = canonical_term_key(str(g.get("term", "")))
        if k and k not in index_by_key:
            index_by_key[k] = idx

    for entry in (new_entries or []):
        if not isinstance(entry, dict) or not entry.get("term"):
            continue
        k = canonical_term_key(str(entry["term"]))
        if not k:
            continue
        if k in index_by_key:
            idx = index_by_key[k]
            if not merged[idx].get("context_explanation") and entry.get("context_explanation"):
                merged[idx]["context_explanation"] = entry["context_explanation"]
        else:
            index_by_key[k] = len(merged)
            merged.append(dict(entry))

    return merged

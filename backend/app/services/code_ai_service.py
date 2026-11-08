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
1. Clear problem statement with formatted markdown, mathematical notation ($O(N)$), and constraints.
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

Highlighted Code:
```{language}
{query}
```
{full_code_section}

Attached Course Documentation:
{doc_excerpts}

Instructions:
1. Grounding: Identify the cited document title and page/locator where this specification comes from (e.g., [Title · Locator]).
2. Verbatim Specification: Quote the exact sentence, rule, formula, threshold, or example from the document that specifies this card or function.
3. Meaning & Application: In 2-3 concise sentences, explain the exact meaning and application of this highlighted code for this card based on the document:
   - What does this line test, calculate, or enforce?
   - How do the document's rules, formulas, or thresholds apply to these specific inputs or logic? (e.g. show the math or condition: 18 / 20 = 90% >= 80% threshold -> 'A').
4. Keep it direct, clean, and concise. Zero conversational filler.
5. Use clean markdown formatting without extraneous whitespace around code tokens or punctuation.

Format your response strictly using these section headers:
**→ Cited Document.** [Source Title · Locator]
**→ Verbatim Specification.**
> <Exact quote, formula, or example from the document>
**→ Meaning & Application.** <Concise explanation of what this highlighted code means and how the document rules apply to it>
"""

DECK_DOCS_QA_PROMPT = """You are a precise, insightful technical tutor helping a student understand their code, attached course documentation, and programming concepts.
A student is working on a coding flashcard/problem and has a question about the code or documentation.

Attached Course Documentation:
{doc_excerpts}

Highlighted / Focused Code:
```{language}
{selected_code}
```
{full_code_section}
{history_section}

Student Question:
{question}

Instructions:
1. Provide a direct, technically accurate, clear, and educational answer to the student's question.
2. Synthesize BOTH the attached course documentation and your general pre-trained programming knowledge and language capabilities ({language}):
   - If the attached documentation specifies rules, formulas, constraints, or course conventions, incorporate and adhere to them.
   - Use your pre-trained software engineering knowledge to explain underlying mechanics, language semantics, standard library behavior, algorithmic complexity, common pitfalls, and edge cases.
   - If no attached documentation is found or if the documentation is silent on this detail, provide a complete and authoritative answer drawn from your pre-trained programming knowledge.
3. Be concise and structured (typically 2-4 focused sentences or clean bullet points). Zero conversational filler (do NOT say "Sure!", "Great question!", "Certainly!", "As an AI...").
4. Use markdown backticks (`code`) for code tokens and bold for key terms.
"""



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
    def __init__(self, model: str | None = None) -> None:
        self.grading_service = GradingService(model=model)

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
            log.warning("Socratic code hint failed: %s", e)
            return "Focus on the core pattern: consider what data structure allows you to look up or store previous states in $O(1)$ time."

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
        from app.services.grading_service import is_allowed_qwen_coder_model

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
        available_models: list[str] = []
        try:
            installed = await self.grading_service.verify_engine()
            available_models = [m for m in installed if is_allowed_qwen_coder_model(m)]
            if not available_models and installed:
                available_models = installed
        except Exception:
            available_models = [target_model]

        try:
            raw_response = await self.grading_service._generate(
                prompt=prompt,
                model=target_model,
                allow_smaller_model=True,
            )
            explanation = raw_response.strip()
        except Exception as e:
            log.warning("Occam's razor explanation generation failed: %s", e)
            raise GradingUnavailable(f"Local LLM explanation failed: {e}") from e

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
    ) -> dict[str, Any]:
        """Grounds a code snippet or user inquiry against attached deck documentation."""
        from app.services.grading_service import is_allowed_qwen_coder_model

        target_model = model or self.grading_service.model
        available_models: list[str] = []
        try:
            installed = await self.grading_service.verify_engine()
            available_models = [m for m in installed if is_allowed_qwen_coder_model(m)]
            if not available_models and installed:
                available_models = installed
        except Exception:
            available_models = [target_model]

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

        full_code_section = (
            f"\nFull Surrounding Code:\n```{language}\n{full_code.strip()}\n```\n"
            if full_code and full_code.strip() and full_code.strip() != query.strip()
            else ""
        )

        prompt = DECK_DOCS_GROUNDING_PROMPT.format(
            language=language,
            query=query.strip(),
            full_code_section=full_code_section,
            doc_excerpts=doc_excerpts_str,
        )

        try:
            raw_response = await self.grading_service._generate(
                prompt=prompt,
                model=target_model,
                allow_smaller_model=True,
            )
            raw = raw_response.strip()
        except Exception as e:
            log.warning("Deck docs query generation failed: %s", e)
            raise GradingUnavailable(f"Local LLM documentation search failed: {e}") from e

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
    ) -> dict[str, Any]:
        """Answers a student's follow-up question grounded in code and attached deck documentation."""
        from app.services.grading_service import is_allowed_qwen_coder_model

        target_model = model or self.grading_service.model
        available_models: list[str] = []
        try:
            installed = await self.grading_service.verify_engine()
            available_models = [m for m in installed if is_allowed_qwen_coder_model(m)]
            if not available_models and installed:
                available_models = installed
        except Exception:
            available_models = [target_model]

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

        full_code_section = (
            f"\nFull Surrounding Code:\n```{language}\n{full_code.strip()}\n```\n"
            if full_code and full_code.strip() and full_code.strip() != (selected_code or "").strip()
            else ""
        )

        formatted_history = []
        if history:
            for turn in history:
                role = getattr(turn, "role", None) or (turn.get("role") if isinstance(turn, dict) else "user")
                content = getattr(turn, "content", None) or (turn.get("content") if isinstance(turn, dict) else str(turn))
                role_label = "Student" if role == "user" else "Tutor"
                formatted_history.append(f"{role_label}: {content}")
        history_section = "\nPrior Discussion:\n" + "\n".join(formatted_history) if formatted_history else ""

        prompt = DECK_DOCS_QA_PROMPT.format(
            language=language,
            selected_code=(selected_code or "").strip() or "(No specific code highlighted)",
            full_code_section=full_code_section,
            history_section=history_section,
            doc_excerpts=doc_excerpts_str,
            question=question.strip(),
        )

        try:
            raw_response = await self.grading_service._generate(
                prompt=prompt,
                model=target_model,
                allow_smaller_model=True,
            )
            raw = raw_response.strip()
        except Exception as e:
            log.warning("Deck docs question generation failed: %s", e)
            raise GradingUnavailable(f"Local LLM documentation question failed: {e}") from e

        doc_citation: str | None = None
        if doc_excerpts:
            top = doc_excerpts[0]
            doc_citation = f"[{top['source_title']} · {top.get('locator') or 'General'}]"

        model_used = self.grading_service.last_used_model or target_model

        return {
            "answer": raw,
            "doc_citation": doc_citation,
            "citations": doc_excerpts,
            "model_used": model_used,
            "available_models": available_models,
        }



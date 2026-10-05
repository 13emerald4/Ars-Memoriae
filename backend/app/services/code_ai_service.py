"""AI Code Generator, Socratic Code Tutor & Multilingual Code Evaluator.

Powered by Google Gemini BYOK.
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
  "starter_tests": "// 🧪 CPSC 210 Unit Testing Suite\\ntest('sample case', checkExpect(() => solve([1, 2, 3]), 3));\\n\\ntest('boundary threshold', checkExpect(() => solve([]), 0));\\n",
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


class CodeAiService:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.grading_service = GradingService(api_key=api_key, model=model)

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
            return "💡 Focus on the core pattern: consider what data structure allows you to look up or store previous states in $O(1)$ time."

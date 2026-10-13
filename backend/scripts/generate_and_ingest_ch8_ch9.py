"""Generate comprehensive flashcard sets for Chapter 8 and Chapter 9 and ingest them into dev.db."""

from __future__ import annotations

import asyncio
import json
import logging
import os

from sqlalchemy import select

from app.db import SessionLocal
from app.models import CardReference, Deck, Note, User
from app.services.note_service import default_note_type, sync_cards

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

USER_EMAIL = "michael.r.polley@outlook.com"
CARDS_DOCS_DIR = r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\Cards Documents"
MASTER_PDF_PATH = os.path.join(CARDS_DOCS_DIR, "CPSC210_2026W1_Master.pdf")

CH8_CARDS = [
    {
        "card_type": "concept",
        "title": "Result<T, E> vs Exceptions: Architectural Rule",
        "category": "Error Handling Strategy",
        "difficulty": "Medium",
        "front": "In CPSC 210 software design, what is the core architectural rule for choosing between returning a `Result<T, E>` versus throwing an exception (`throw new Error(...)`)?",
        "back": "- **Choose `Result<T, E>`** when the failure is an *expected domain outcome* that the **immediate caller** is responsible for handling (e.g. invalid form input, missing lookup key, bad query). The compiler forces the caller to check `.ok`.\n- **Choose `throw`** when the failure is an *unrecoverable bug* (e.g. broken invariant, precondition violation `assert`), or an operational failure where the work should **abort and unwind the stack** to be handled far above (e.g. disk failure, network timeout).\n\n*Rule of thumb*: Return values for local caller decisions; throw to abort stack execution.",
        "quote": "Choose a Result when the immediate caller should deal with the failure; throw when the work should abort and be handled far above. Catch only where the code knows what to do.",
        "locator": "Textbook Ch. 8 — Designing for Failure (p. 175); Chapter Summary",
        "tags": ["cpsc210", "ch08", "result-vs-throw", "design-philosophy"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Defining and Constructing Result<T, E>",
        "category": "Result Type",
        "difficulty": "Easy",
        "front": "Define the canonical CPSC 210 discriminated union `Result<T, E>` along with the helper factory functions `ok` and `err`.",
        "starter_code": "export type Result<T, E> = \n  | { ok: true; value: T }\n  | { ok: false; error: E };\n\nexport function ok<T>(value: T): Result<T, never> {\n  // TODO\n}\n\nexport function err<E>(error: E): Result<never, E> {\n  // TODO\n}",
        "back": "export type Result<T, E> = \n  | { ok: true; value: T }\n  | { ok: false; error: E };\n\nexport function ok<T>(value: T): Result<T, never> {\n  return { ok: true, value };\n}\n\nexport function err<E>(error: E): Result<never, E> {\n  return { ok: false, error };\n}",
        "test_cases": [
            {"input": {"val": 42}, "expected": {"ok": True, "value": 42}},
            {"input": {"err": "not found"}, "expected": {"ok": False, "error": "not found"}}
        ],
        "time_complexity": "O(1)",
        "space_complexity": "O(1)",
        "quote": "Result: the failure is in the type, so the compiler forces callers to handle it.",
        "locator": "Textbook Ch. 8 — Returning Results (p. 172)",
        "tags": ["cpsc210", "ch08", "result-type", "code"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Unwrapping Result with Discriminated Union Narrowing",
        "category": "Result Handling",
        "difficulty": "Easy",
        "front": "Write `unwrapOr<T, E>(result: Result<T, E>, fallback: T): T` that extracts the value if the result is `ok`, or returns `fallback` if the result is an `err`.",
        "starter_code": "import { Result } from './result';\n\nexport function unwrapOr<T, E>(result: Result<T, E>, fallback: T): T {\n  // TODO\n  return fallback;\n}",
        "back": "export function unwrapOr<T, E>(result: Result<T, E>, fallback: T): T {\n  if (result.ok) {\n    return result.value;\n  }\n  return fallback;\n}",
        "test_cases": [
            {"input": {"result": {"ok": True, "value": "loaded"}, "fallback": "default"}, "expected": "loaded"},
            {"input": {"result": {"ok": False, "error": "missing"}, "fallback": "default"}, "expected": "default"}
        ],
        "time_complexity": "O(1)",
        "space_complexity": "O(1)",
        "quote": "TypeScript's type checker narrows the type inside the if block because 'ok' is a discriminant property.",
        "locator": "Textbook Ch. 8 — Handling Results (p. 174)",
        "tags": ["cpsc210", "ch08", "discriminated-unions", "code"]
    },
    {
        "card_type": "concept",
        "title": "TypeScript Exception Model: Unchecked Exceptions",
        "category": "Exceptions",
        "difficulty": "Medium",
        "front": "Are exceptions checked or unchecked in TypeScript? What are the consequences for callers, and how should thrown exceptions be documented?",
        "back": "1. **TypeScript exceptions are unchecked**: The TypeScript type system does **not** track thrown exceptions in function return signatures. A function that throws `Error` simply has return type `T` (or `Promise<T>`).\n2. **Consequence**: The compiler will **not** warn a caller if they forget to wrap a throwing call in `try/catch`.\n3. **Documentation**: Because the compiler cannot enforce exception handling, all throwing behaviors must be explicitly documented in JSDoc using the `@throws {ErrorType} condition` tag.",
        "quote": "TypeScript exceptions are unchecked, and assert is just a throw nobody catches. Document it with @throws.",
        "locator": "Textbook Ch. 8 — Throwing Exceptions (p. 176); Chapter Summary",
        "tags": ["cpsc210", "ch08", "exceptions", "jsdoc"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Type-Safe Error Catching with unknown",
        "category": "Exception Handling",
        "difficulty": "Medium",
        "front": "In TypeScript with strict mode, what type does the variable `e` have in `catch (e)`? Write the standard boilerplate to safely extract its error message.",
        "starter_code": "try {\n  riskyOperation();\n} catch (e) {\n  // What type is e, and how do you safely get its message?\n}",
        "back": "try {\n  riskyOperation();\n} catch (e: unknown) {\n  // In TypeScript, e has type 'unknown' because anything can be thrown in JS.\n  if (e instanceof Error) {\n    console.error(e.message);\n  } else {\n    console.error(String(e));\n  }\n}",
        "quote": "In catch (e), e has type unknown, so check e instanceof Error before using it.",
        "locator": "Textbook Ch. 8 — Catching Exceptions (p. 178)",
        "tags": ["cpsc210", "ch08", "catch-unknown", "type-narrowing"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "NodeJS System Error Checking (ENOENT)",
        "category": "Filesystem Errors",
        "difficulty": "Medium",
        "front": "Write a `catch` block that specifically inspects whether a caught error is a Node filesystem `ENOENT` (file not found) error, re-throwing any other error.",
        "starter_code": "try {\n  await fs.readFile(path, 'utf-8');\n} catch (e) {\n  // Check if ENOENT; if not, re-throw\n}",
        "back": "try {\n  await fs.readFile(path, 'utf-8');\n} catch (e) {\n  if (e instanceof Error && (e as NodeJS.ErrnoException).code === 'ENOENT') {\n    // Recover from missing file locally\n    return null;\n  }\n  throw e; // Re-throw all unexpected errors\n}",
        "quote": "if (!(e instanceof Error) || (e as NodeJS.ErrnoException).code !== 'ENOENT') throw e;",
        "locator": "Textbook Ch. 8 — File System Errors (p. 182); LA08 Task 3",
        "tags": ["cpsc210", "ch08", "enoent", "nodejs-fs"]
    },
    {
        "card_type": "concept",
        "title": "Anti-Pattern: Error Swallowing",
        "category": "Design Anti-Patterns",
        "difficulty": "Medium",
        "front": "Why is `try { return await load(path); } catch { return []; }` considered a severe software design anti-pattern? What is the correct fix?",
        "back": "- **Why it is an anti-pattern**: It **swallows** failures silently. The caller has no way of distinguishing between \"the file exists and has 0 events\" versus \"the file path was misspelled, permissions failed, or the disk was corrupt\". It hides failures from logs and callers.\n- **The Fix**: Remove the `try/catch` entirely and let the error propagate: `return await load(path);`. Propagating errors requires no code at all.",
        "quote": "loadEventsLenient is currently following a software design anti-pattern. It 'swallows' errors by catching them and simply returning a feasible return value. Propagating needs no code at all.",
        "locator": "LA08.1 Task 2.5 — An Error Propagation Anti-Pattern; Textbook Ch. 8",
        "tags": ["cpsc210", "ch08", "anti-patterns", "error-swallowing"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Parsing Event Log Line with Strict Validation (LA08 Task 1)",
        "category": "Input Validation",
        "difficulty": "Medium",
        "front": "Implement `parseEventLine(line: string): EventRecord` that parses `<timestamp>|<level>|<message>`. Check that level is one of `INFO`, `WARN`, `ERROR`. Throw `Error(\"malformed event line: \" + line)` on invalid format or level.",
        "starter_code": "export type EventLevel = 'INFO' | 'WARN' | 'ERROR';\nexport type EventRecord = { timestamp: string; level: EventLevel; message: string };\n\nexport function parseEventLine(line: string): EventRecord {\n  // TODO\n}",
        "back": "export function parseEventLine(line: string): EventRecord {\n  const parts = line.split('|');\n  if (parts.length !== 3) {\n    throw new Error(`malformed event line: ${line}`);\n  }\n  const [timestamp, rawLevel, message] = parts;\n  if (rawLevel !== 'INFO' && rawLevel !== 'WARN' && rawLevel !== 'ERROR') {\n    throw new Error(`malformed event line: ${line}`);\n  }\n  return { timestamp, level: rawLevel, message };\n}",
        "test_cases": [
            {"input": {"line": "2026-10-12T10:00:00Z|INFO|System booted"}, "expected": {"timestamp": "2026-10-12T10:00:00Z", "level": "INFO", "message": "System booted"}}
        ],
        "time_complexity": "O(N) where N is line length",
        "space_complexity": "O(N)",
        "quote": "Throws Error 'malformed event line: <line>' when fields are missing or level is not INFO/WARN/ERROR.",
        "locator": "LA08.1 — TASK 1: Basics of Throwing and Catching While Parsing",
        "tags": ["cpsc210", "ch08", "la08", "validation", "code"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Parsing Log File with Line Number Attribution (LA08 Task 1)",
        "category": "Parsing & Error Context",
        "difficulty": "Medium",
        "front": "Implement `parseLog(content: string): EventRecord[]`. Split by newline, ignore empty lines, parse non-empty lines using `parseEventLine`. If any line fails, catch and re-throw with message `\"line <n>: malformed\"` (1-indexed).",
        "starter_code": "export function parseLog(content: string): EventRecord[] {\n  // TODO\n}",
        "back": "export function parseLog(content: string): EventRecord[] {\n  const lines = content.split(/\\r?\\n/);\n  const records: EventRecord[] = [];\n  for (let i = 0; i < lines.length; i++) {\n    const line = lines[i].trim();\n    if (line.length === 0) continue;\n    try {\n      records.push(parseEventLine(line));\n    } catch {\n      throw new Error(`line ${i + 1}: malformed`);\n    }\n  }\n  return records;\n}",
        "quote": "Throws when any non-empty line is malformed, with message 'line <n>: malformed'.",
        "locator": "LA08.1 — TASK 1: parseLog; Textbook Ch. 8",
        "tags": ["cpsc210", "ch08", "la08", "error-context", "code"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Graceful Local Recovery with Retry (LA08 Task 3)",
        "category": "Recovery Patterns",
        "difficulty": "Hard",
        "front": "Implement `writeSummaryFile(reportPath: string, summary: object): Promise<void>`. Attempt to write JSON to `reportPath`. If writing fails because the parent directory does not exist (ENOENT), create the directory recursively and retry once. Re-throw all other errors.",
        "starter_code": "import { writeFile, mkdir } from 'node:fs/promises';\nimport { dirname } from 'node:path';\n\nexport async function writeSummaryFile(reportPath: string, summary: object): Promise<void> {\n  // TODO\n}",
        "back": "export async function writeSummaryFile(reportPath: string, summary: object): Promise<void> {\n  const payload = JSON.stringify(summary, null, 2);\n  try {\n    await writeFile(reportPath, payload, 'utf-8');\n  } catch (e) {\n    if (e instanceof Error && (e as NodeJS.ErrnoException).code === 'ENOENT') {\n      await mkdir(dirname(reportPath), { recursive: true });\n      await writeFile(reportPath, payload, 'utf-8');\n      return;\n    }\n    throw e;\n  }\n}",
        "quote": "If writing fails because a parent directory is missing (ENOENT), creates the directory and retries once. Re-throws all other errors.",
        "locator": "LA08.1 — TASK 3: Graceful Local Recovery; Textbook Ch. 8 (p. 184)",
        "tags": ["cpsc210", "ch08", "la08", "recovery", "retry-pattern", "code"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Testing Expected Throws in Vitest",
        "category": "Testing Exceptions",
        "difficulty": "Easy",
        "front": "How do you test that a synchronous function throws an expected error message using Vitest? Why does `expect(fn())` fail while `expect(() => fn())` succeeds?",
        "starter_code": "import { test, expect } from 'vitest';\n\ntest('throws on invalid level', () => {\n  // Write assertion that parseEventLine('t|BAD|m') throws 'malformed event line'\n});",
        "back": "test('throws on invalid level', () => {\n  expect(() => parseEventLine('t|BAD|m')).toThrow('malformed event line');\n});\n// Explanation: If you write expect(parseEventLine(...)), the function executes immediately\n// before Vitest can intercept it, crashing the test. Passing a zero-argument arrow function\n// (() => ...) allows Vitest to wrap the call in its internal try/catch.",
        "quote": "expect(() => requireSection(c, 'NOPE')).to.throw('no section with id NOPE'); // needs () =>",
        "locator": "Textbook Ch. 9 — Testing Exceptions (p. 198); Chapter Summary",
        "tags": ["cpsc210", "ch08", "vitest", "to-throw"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Testing Asynchronous Rejections in Vitest",
        "category": "Testing Async Exceptions",
        "difficulty": "Medium",
        "front": "How do you assert that an asynchronous Promise-returning function rejects with an expected error message in Vitest?",
        "starter_code": "import { test, expect } from 'vitest';\n\ntest('rejects on missing file', async () => {\n  // Assert loadEventsFromFile('missing.txt') rejects with ENOENT\n});",
        "back": "test('rejects on missing file', async () => {\n  await expect(loadEventsFromFile('missing.txt')).rejects.toThrow();\n});\n// Must await the expect(...).rejects promise chain so Vitest waits for resolution.",
        "quote": "Async throwing returns a rejected promise: await expect(p).rejects.toThrow().",
        "locator": "Textbook Ch. 8 — Testing Asynchronous Errors (p. 187)",
        "tags": ["cpsc210", "ch08", "vitest", "async-testing"]
    },
    {
        "card_type": "concept",
        "title": "The finally Block Guarantee",
        "category": "Resource Cleanup",
        "difficulty": "Easy",
        "front": "What is the execution guarantee provided by a `finally` block in TypeScript? When should it be used?",
        "back": "- **Execution Guarantee**: A `finally` block runs on **every exit path**: whether the `try` block succeeds, throws an unhandled exception, handles an exception in `catch`, or exits early via a `return` statement.\n- **Use Case**: Mandatory resource cleanup that must happen no matter what: closing open file descriptors, releasing database connections, clearing interval timers, or unlocking mutexes.",
        "quote": "finally runs on every exit, so it is the place for cleanup.",
        "locator": "Textbook Ch. 8 — Cleaning Up with finally (p. 180)",
        "tags": ["cpsc210", "ch08", "finally", "cleanup"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Custom Error Classes in TypeScript",
        "category": "Custom Exceptions",
        "difficulty": "Medium",
        "front": "Create a custom error class `MalformedEventError` in TypeScript that captures the line number and offending text, setting its `name` property properly.",
        "starter_code": "export class MalformedEventError extends Error {\n  // TODO: capture lineNo, rawText\n}",
        "back": "export class MalformedEventError extends Error {\n  public readonly lineNo: number;\n  public readonly rawText: string;\n\n  constructor(lineNo: number, rawText: string) {\n    super(`Line ${lineNo} is malformed: \"${rawText}\"`);\n    this.name = 'MalformedEventError';\n    this.lineNo = lineNo;\n    this.rawText = rawText;\n    Object.setPrototypeOf(this, MalformedEventError.prototype);\n  }\n}",
        "quote": "Custom error classes allow callers to use instanceof to distinguish domain errors from unexpected system bugs.",
        "locator": "Textbook Ch. 8 — Custom Error Classes (p. 181)",
        "tags": ["cpsc210", "ch08", "custom-errors", "subclassing"]
    },
    {
        "card_type": "concept",
        "title": "Clean Happy Path Pipeline Pattern (LA08 Task 4)",
        "category": "Architecture",
        "difficulty": "Medium",
        "front": "How do exceptions allow pipeline functions like `importLogs(filePaths, reportPath)` to keep their 'happy path' clean compared to using return status codes?",
        "back": "When using exceptions, the happy path reads linearly as a clear sequence of steps:\n1. Load files\n2. Count and aggregate records\n3. Write output summary report\n\nIf any step fails, execution halts automatically and unwinds to the caller. With status codes or nested `Result` checks, every intermediate line requires defensive branching (`if (!res.ok) return res;`), cluttering the domain algorithm.",
        "quote": "Done when: success path reads as sequence: load -> count -> write. Exceptions keep the happy path clean.",
        "locator": "LA08.1 — TASK 4: Keeping the Happy Path Clean",
        "tags": ["cpsc210", "ch08", "happy-path", "design-patterns"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Boundary Error Reporting Callback Pattern (LA08 Task 5)",
        "category": "Caller Boundaries",
        "difficulty": "Hard",
        "front": "Implement `runImportJob(files: string[], report: (err: Error | null, summary?: object) => void): Promise<void>`. Call `report(null, summary)` on success, or `report(err)` on failure, without throwing.",
        "starter_code": "export async function runImportJob(\n  files: string[],\n  report: (err: Error | null, summary?: object) => void\n): Promise<void> {\n  // TODO\n}",
        "back": "export async function runImportJob(\n  files: string[],\n  report: (err: Error | null, summary?: object) => void\n): Promise<void> {\n  try {\n    const summary = await importLogs(files, 'output.json');\n    report(null, summary);\n  } catch (e) {\n    const err = e instanceof Error ? e : new Error(String(e));\n    report(err);\n  }\n}",
        "quote": "This function shows an alternate design where the function takes in a report callback serving as the boundary between the pipeline and its caller.",
        "locator": "LA08.1 — TASK 5: Boundary Handling; Textbook Ch. 8",
        "tags": ["cpsc210", "ch08", "boundary-handling", "callbacks"]
    },
    {
        "card_type": "concept",
        "title": "Where to Catch Exceptions",
        "category": "Exception Principles",
        "difficulty": "Easy",
        "front": "What is the golden rule for where in a system architecture an exception should be caught?",
        "back": "**Catch only where the code knows what to do about it.**\n- If an intermediary function cannot fix, retry, or meaningfully translate an error, it should **not catch it at all**; let it propagate.\n- Catch only at architectural boundaries where:\n  1. Local recovery/retry is possible (e.g. creating a missing folder).\n  2. A domain translation is necessary.\n  3. Top-level presentation to the user/client is handled (e.g. HTTP 400/500 router).",
        "quote": "Catch only where the code knows what to do. Propagating needs no code at all.",
        "locator": "Textbook Ch. 8 — Deciding Where to Catch (p. 185)",
        "tags": ["cpsc210", "ch08", "principles", "exception-handling"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Mapping Result Values (resultMap)",
        "category": "Result Combinators",
        "difficulty": "Medium",
        "front": "Implement `resultMap<T, U, E>(res: Result<T, E>, fn: (val: T) => U): Result<U, E>` which applies `fn` to the inner value if `ok`, or passes the `error` along unchanged.",
        "starter_code": "import { Result, ok, err } from './result';\n\nexport function resultMap<T, U, E>(res: Result<T, E>, fn: (val: T) => U): Result<U, E> {\n  // TODO\n}",
        "back": "export function resultMap<T, U, E>(res: Result<T, E>, fn: (val: T) => U): Result<U, E> {\n  if (res.ok) {\n    return ok(fn(res.value));\n  }\n  return err(res.error);\n}",
        "test_cases": [
            {"input": {"res": {"ok": True, "value": 5}}, "expected": {"ok": True, "value": 10}},
            {"input": {"res": {"ok": False, "error": "failed"}}, "expected": {"ok": False, "error": "failed"}}
        ],
        "time_complexity": "O(1)",
        "space_complexity": "O(1)",
        "quote": "Combinators allow transforming values inside Result wrappers without manual unpacking boilerplate.",
        "locator": "Textbook Ch. 8 — Result Combinators (p. 188)",
        "tags": ["cpsc210", "ch08", "functional-patterns", "result"]
    },
    {
        "card_type": "concept",
        "title": "Never Use Exceptions for Normal Control Flow",
        "category": "Design Anti-Patterns",
        "difficulty": "Easy",
        "front": "Why should exceptions never be used for normal control flow (such as terminating a loop or checking for empty input)?",
        "back": "1. **Violates Software Contracts**: Exceptions indicate *exceptional*, abnormal conditions. Using them for ordinary branching breaks the contract and confuses maintainers.\n2. **Severe Performance Penalty**: Throwing an exception requires the JavaScript runtime to capture the call stack trace and unwind the frame stack.\n3. **Cluttered Call Sites**: Forces callers to write noisy `try/catch` blocks for ordinary scenarios.",
        "quote": "Never use exceptions for normal control flow; validate data where it enters the program.",
        "locator": "Textbook Ch. 8 — Best Practices for Failure (p. 190); Chapter Summary",
        "tags": ["cpsc210", "ch08", "control-flow", "anti-patterns"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Converting Thrown Exception to Result (tryCatch)",
        "category": "Interoperability",
        "difficulty": "Medium",
        "front": "Write `tryCatch<T>(fn: () => T): Result<T, string>` that executes `fn()`. If it returns normally, wraps it in `ok()`. If it throws, catches the error and wraps the message in `err()`.",
        "starter_code": "import { Result, ok, err } from './result';\n\nexport function tryCatch<T>(fn: () => T): Result<T, string> {\n  // TODO\n}",
        "back": "export function tryCatch<T>(fn: () => T): Result<T, string> {\n  try {\n    return ok(fn());\n  } catch (e) {\n    const msg = e instanceof Error ? e.message : String(e);\n    return err(msg);\n  }\n}",
        "test_cases": [
            {"input": {}, "expected": {"ok": True, "value": 100}}
        ],
        "quote": "Bridging between third-party throwing APIs and modern Result-based domain code.",
        "locator": "Textbook Ch. 8 — Bridging Exceptions and Results (p. 191)",
        "tags": ["cpsc210", "ch08", "try-catch", "interop"]
    },
    {
        "card_type": "concept",
        "title": "Data Validation at System Boundaries",
        "category": "Defensive Design",
        "difficulty": "Easy",
        "front": "Where in a software architecture should data validation take place, and why?",
        "back": "**Validate data where it enters the program** (at system boundaries):\n- When parsing external files, HTTP request bodies, or command line arguments.\n- Once data passes the boundary validation and enters core domain code, internal functions should be able to trust that invariants hold without redundant defensive re-checks.",
        "quote": "Validate data where it enters the program. Once inside, internal functions rely on enforced contracts.",
        "locator": "Textbook Ch. 8 — Validating at Boundaries (p. 191); Chapter Summary",
        "tags": ["cpsc210", "ch08", "boundary-validation", "invariants"]
    },
    {
        "card_type": "concept",
        "title": "Assert vs Result: The Distinction",
        "category": "Contracts",
        "difficulty": "Medium",
        "front": "In CPSC 210, what is the exact difference between `assert(condition)` and returning `Result<T, E>`?",
        "back": "- `assert(condition)`: Guards **preconditions** against **programming bugs**. A failed assertion means developer error; the program should immediately crash because internal invariants are violated. Nobody catches an assertion.\n- `Result<T, E>`: Represents an **expected domain scenario** (e.g. incorrect user input, network offline). The program is functioning correctly, and the caller is expected to handle the alternative outcome gracefully.",
        "quote": "assert is just a throw nobody catches. Choose Result when the caller should deal with the failure.",
        "locator": "Textbook Ch. 8 — Designing for Failure (p. 176); Chapter Summary",
        "tags": ["cpsc210", "ch08", "assert-vs-result", "invariants"]
    }
]

CH9_CARDS = [
    {
        "card_type": "concept",
        "title": "Black-Box vs White-Box Testing",
        "category": "Testing Strategies",
        "difficulty": "Easy",
        "front": "What is the difference between black-box testing and white-box testing? Which one should be written first?",
        "back": "- **Black-Box Testing**: Tests written directly from the **specification / contract**, with zero knowledge of the implementation internals. Tests equivalence classes and boundary values.\n- **White-Box Testing**: Tests written by inspecting the **implementation source code**, designed to achieve high statement, branch, or condition coverage.\n- **Order**: Write black-box tests **first** from the spec so you don't encode implementation assumptions or miss requirements.",
        "quote": "Black-box tests come from the spec, white-box tests from the code. 100% branch coverage can't reveal a missing branch.",
        "locator": "Textbook Ch. 9 — Validating Behaviour (p. 200); Chapter Summary",
        "tags": ["cpsc210", "ch09", "black-box", "white-box", "testing-theory"]
    },
    {
        "card_type": "concept",
        "title": "Why 100% Branch Coverage Is Not Enough",
        "category": "Code Coverage",
        "difficulty": "Medium",
        "front": "Why is 100% branch coverage insufficient to guarantee that a program is free of bugs?",
        "back": "1. **Missing Branches**: 100% branch coverage only measures branches that *exist* in the written code. It cannot reveal a branch that the developer forgot to implement entirely (a missing requirement).\n2. **Boundary Value Precision**: Reaching a branch with `x = 5` covers the branch, but does not verify whether the operator should be `>` or `>=`.\n3. **Combination Explosions**: Individual branches may execute, but complex interactions between multiple state variables may still cause faults.",
        "quote": "100% branch coverage can't reveal a missing branch. A test suite must test according to the specification.",
        "locator": "Textbook Ch. 9 — Coverage Limits (p. 202); Reid Holmes Piazza @313",
        "tags": ["cpsc210", "ch09", "branch-coverage", "testing-limits"]
    },
    {
        "card_type": "concept",
        "title": "The Purpose of Regression Testing",
        "category": "Regression Testing",
        "difficulty": "Easy",
        "front": "What is regression testing, and when should the test suite be executed during software development?",
        "back": "- **Regression Testing**: Re-running the entire existing test suite after modifying code to verify that bug fixes, optimizations, or new features have **not broken existing functionality** (caused a regression).\n- **When to run**: Rerun the **entire test suite** after every implementation change or refactoring step.",
        "quote": "Rerun the whole suite after every change (regression).",
        "locator": "Textbook Ch. 9 — Regression Testing (p. 204); Chapter Summary",
        "tags": ["cpsc210", "ch09", "regression-testing", "workflow"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Specific Assertions vs Generic Boolean Assertions",
        "category": "Assertion Design",
        "difficulty": "Easy",
        "front": "Why should you prefer `expect(users).toHaveLength(3)` over `expect(users.length === 3).toBe(true)` in Vitest?",
        "back": "- **Specific Assertion (`toHaveLength(3)`)**: On failure, the test runner outputs: `Expected length 3, but received 2: ['Alice', 'Bob']`. The error message immediately reveals *why* it failed.\n- **Generic Boolean Assertion (`toBe(true)`)**: On failure, the runner only outputs: `Expected true, received false`. The failure gives zero diagnostic insight into what the actual length or array contents were.",
        "quote": "Prefer specific assertions (include, toHaveLength) over equal(true). The failure message names the cause.",
        "locator": "Textbook Ch. 9 — Assertion Quality (p. 195); Chapter Summary",
        "tags": ["cpsc210", "ch09", "vitest", "assertion-quality"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Identity (toBe) vs Value Equality (toEqual)",
        "category": "Vitest Assertions",
        "difficulty": "Medium",
        "front": "Explain the difference between `expect(a).toBe(b)` and `expect(a).toEqual(b)` in Vitest / Chai. Give an example where `toBe` fails but `toEqual` passes.",
        "starter_code": "const obj1 = { id: 'x', count: 1 };\nconst obj2 = { id: 'x', count: 1 };\n\n// Which assertion passes and which fails?",
        "back": "- `toBe(b)` (identity equality): Uses `Object.is` (strict `===`). For objects/arrays, it checks whether both point to the **same memory reference**.\n- `toEqual(b)` (deep / structural equality): Traverses all properties and checks that every field value matches.\n\n```typescript\nexpect(obj1).toBe(obj2);    // FAILS (different references)\nexpect(obj1).toEqual(obj2); // PASSES (deep equal)\n```",
        "quote": "Trap: equal on objects compares identity. Use toEqual / to.deep.equal for structural object comparison.",
        "locator": "Textbook Ch. 9 — Comparing Objects (p. 196); Chapter Summary",
        "tags": ["cpsc210", "ch09", "to-be-vs-to-equal", "vitest"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Testing Floating-Point Numbers with toBeCloseTo",
        "category": "Numeric Assertions",
        "difficulty": "Easy",
        "front": "Why does `expect(0.1 + 0.2).toBe(0.3)` fail in JavaScript / TypeScript? How should floating point values be tested in Vitest?",
        "starter_code": "import { test, expect } from 'vitest';\n\ntest('floating point addition', () => {\n  const result = 0.1 + 0.2;\n  // Write proper floating point assertion\n});",
        "back": "test('floating point addition', () => {\n  const result = 0.1 + 0.2; // In IEEE-754: 0.30000000000000004\n  expect(result).toBeCloseTo(0.3, 5); // Checks within precision\n});\n// In LA09: Temperatures come from power * 0.12, so use toBeCloseTo / to.be.closeTo, not toBe.",
        "quote": "Temperatures come from power * 0.12, so use to.be.closeTo(x, delta), not to.equal, for temperature assertions.",
        "locator": "LA09.1 Task 4; Textbook Ch. 9 — Floating Point Testing",
        "tags": ["cpsc210", "ch09", "floating-point", "to-be-close-to", "la09"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Layered Assertions on Structured Reports (LA09 Task 3)",
        "category": "Assertion Structure",
        "difficulty": "Medium",
        "front": "What does it mean to write 'informative, layered assertions' on a structured assessment object, and why is it preferred over a single `toEqual` on the entire object?",
        "starter_code": "const report = reactor.evaluateSafety();\n// How should you assert report rather than expect(report).toEqual({...})?",
        "back": "```typescript\n// Layer from general to specific:\nexpect(report.status).toBe('emergency');\nexpect(report.shouldScram).toBe(true);\nexpect(report.minutesToCritical).toBe(5);\nexpect(report.activePumps).toBe(2);\n```\n**Why**: If the whole object is compared with `toEqual({...})`, any mismatch in an unrelated field obscures the primary fault. Layered assertions check primary state first, so test failures identify the exact faulty property immediately.",
        "quote": "For the structured safety report, assert one field at a time rather than one big equality on the whole object, so the first failure names the fault.",
        "locator": "LA09.1 — TASK 3: Informative, layered assertions",
        "tags": ["cpsc210", "ch09", "layered-assertions", "la09"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Testing Boundary Conditions: Telling >= from > (LA09 Task 1)",
        "category": "Boundary Testing",
        "difficulty": "Hard",
        "front": "In LA09's reactor, an emergency occurs when `temperature >= criticalTempC - 20`. How do you design a test that can distinguish between `temperature >= threshold` versus `temperature > threshold`?",
        "starter_code": "// Initial temp: 300, Critical: 650. Emergency threshold = 630.\n// Online pumps: 1 (cooling 18/min). Power: 400MW (heat in = 48/min). Net heat = 30/min.\n// Write the exact tick test.",
        "back": "```typescript\ntest('emergency at exactly criticalTempC - 20 boundary', () => {\n  const reactor = makeReactorCoolingSystem(2, 300, 650); // threshold = 630\n  reactor.setPumpOnline(1, false); // 1 pump online (18 cooling)\n  reactor.setPowerMw(400);         // 400 * 0.12 = 48 heat. Net = +30/min\n  reactor.tick(11);                // 300 + (30 * 11) = 630 (EXACTLY threshold)\n\n  const report = reactor.evaluateSafety();\n  expect(report.status).toBe('emergency');\n});\n```\n*Explanation*: Driving temperature to *exactly* 630 tests the boundary. If the code used `>` instead of `>=`, this test fails.",
        "quote": "Drive the temperature to exactly critical - 20 with tick, since a boundary test is the only kind that tells >= from >.",
        "locator": "LA09.1 — TASK 1: Partition inputs by status",
        "tags": ["cpsc210", "ch09", "boundary-value-analysis", "la09", "code"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Output Partitioning: Null vs Rounded Up (LA09 Task 2)",
        "category": "Output Partitioning",
        "difficulty": "Medium",
        "front": "How do you partition output tests for `minutesToCritical` where the contract specifies:\n- `null` when net heat is not positive\n- rounded up integer when net heat is positive?",
        "starter_code": "// Write tests covering both output partitions",
        "back": "```typescript\ntest('minutesToCritical is null when cooling or stable', () => {\n  const reactor = makeReactorCoolingSystem(3, 300, 650);\n  reactor.setPowerMw(100); // 12 heat in < 54 cooling (net negative)\n  expect(reactor.evaluateSafety().minutesToCritical).toBeNull();\n});\n\ntest('minutesToCritical rounds up on uneven division', () => {\n  // Gap: 650 - 300 = 350. Net heat: 300*0.12 - 18 = 36 - 18 = 18.\n  // 350 / 18 = 19.44 -> Math.ceil gives 20.\n  const reactor = makeReactorCoolingSystem(1, 300, 650);\n  reactor.setPowerMw(300);\n  expect(reactor.evaluateSafety().minutesToCritical).toBe(20);\n});\n```",
        "quote": "minutesToCritical is null when not heating and a number when heating; pick an uneven division so the assertion checks rounding.",
        "locator": "LA09.1 — TASK 2: Partition the outputs",
        "tags": ["cpsc210", "ch09", "output-partitioning", "la09", "code"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Testing Floor Clamping Invariants (LA09 Task 4)",
        "category": "Invariant Testing",
        "difficulty": "Medium",
        "front": "Write a test verifying that `tick(minutes)` enforces the minimum temperature floor invariant of 250°C, even when intense cooling runs for many minutes.",
        "starter_code": "test('temperature never falls below 250C floor', () => {\n  // TODO: start at 300C, power 0, 5 pumps cooling, tick(100)\n});",
        "back": "test('temperature never falls below 250C floor', () => {\n  const reactor = makeReactorCoolingSystem(5, 300, 700);\n  reactor.setPowerMw(0); // 0 heat in, 5*18 = 90 cooling/min\n  reactor.tick(100);      // 300 - 9000 would be negative\n  const snap = reactor.snapshot();\n  expect(snap.coolantTempC).toBe(250);\n});",
        "quote": "temperature moves by net heat times minutes, and never falls below 250.",
        "locator": "LA09.1 — Domain Rules & TASK 4; Textbook Ch. 9",
        "tags": ["cpsc210", "ch09", "invariants", "floor-testing", "code"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Stateful Sequence Integration Test (LA09 Task 5)",
        "category": "Sequence Testing",
        "difficulty": "Hard",
        "front": "Write a stateful sequence test in Vitest that tests:\n1. Power set to 500, pumps taken offline\n2. Temperature ticks up\n3. `startEmergencyCooldown()` triggers\n4. Verifies power is reset to 0, all pumps brought online, and status recovers.",
        "starter_code": "test('emergency cooldown resets power and restores pumps', () => {\n  // TODO\n});",
        "back": "test('emergency cooldown resets power and restores pumps', () => {\n  const reactor = makeReactorCoolingSystem(3, 300, 700);\n  reactor.setPowerMw(500);\n  reactor.setPumpOnline(0, false);\n  reactor.setPumpOnline(1, false);\n  reactor.tick(2);\n\n  // Trigger emergency cooldown\n  reactor.startEmergencyCooldown();\n\n  const snap = reactor.snapshot();\n  expect(snap.powerMw).toBe(0);\n  expect(snap.pumpOnline).toEqual([true, true, true]);\n\n  const report = reactor.evaluateSafety();\n  expect(report.status).toBe('stable');\n  expect(report.shouldScram).toBe(false);\n});",
        "quote": "Add one test that performs a sequence: set power, disable pumps, tick, trigger emergency cooldown... catches cooldown that forgets to restore pumps.",
        "locator": "LA09.1 — TASK 5: A stateful sequence",
        "tags": ["cpsc210", "ch09", "sequence-testing", "stateful", "code"]
    },
    {
        "card_type": "concept",
        "title": "Mutation Testing: Killing Mutants",
        "category": "Test Suite Strength",
        "difficulty": "Medium",
        "front": "What is mutation testing, and what does it mean to 'kill a mutant'? How is it used to evaluate test suite strength in CPSC 210 autograders?",
        "back": "- **Mutation Testing**: An automated tool (or autograder) injects small synthetic faults (\"mutants\") into the reference codebase (e.g. changing `>=` to `>`, changing a constant `18` to `17`, deleting a floor check).\n- **Killing a Mutant**: If your test suite **fails** when run against the faulty mutant code, your test has detected the bug—the mutant is \"killed\".\n- **Mutation Score**: The percentage of mutants killed measures the true **fault detection strength** of your suite, far surpassing raw line coverage.",
        "quote": "The grader scores your suite by running it against faulty copies of reactor.ts, each with one small change, and counting how many your tests catch.",
        "locator": "LA09.1 — STRETCH: Be the Mutant; Textbook Ch. 9",
        "tags": ["cpsc210", "ch09", "mutation-testing", "test-strength"]
    },
    {
        "card_type": "concept",
        "title": "Test Independence: Fresh State Rule",
        "category": "Testing Best Practices",
        "difficulty": "Easy",
        "front": "Why should each test build a fresh object/system instance inside its test body instead of sharing a global instance across tests?",
        "back": "Sharing a mutable instance across tests causes **test pollution / coupling**:\n- Test B might pass only because Test A previously mutated the state into an expected configuration.\n- If Test A fails, Test B fails as a cascading artifact.\n- Tests cannot be reordered or run in parallel.\n*Rule*: Build a fresh, isolated system instance inside every test (or in `beforeEach`).",
        "quote": "Build a fresh reactor inside each test so tests stay independent, and name tests by behaviour, not implementation details.",
        "locator": "LA09.1 — Workflow; Textbook Ch. 9",
        "tags": ["cpsc210", "ch09", "test-isolation", "fixtures"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Testing Constructor Invariant Rejection",
        "category": "Precondition Testing",
        "difficulty": "Medium",
        "front": "Write Vitest assertions testing that `makeReactorCoolingSystem(pumpCount, initialTempC, criticalTempC)` rejects impossible parameters:\n- pumpCount <= 0\n- initialTempC < 250\n- criticalTempC <= initialTempC",
        "starter_code": "import { test, expect } from 'vitest';\n\ntest('rejects impossible reactors', () => {\n  // Write the three throw assertions\n});",
        "back": "test('rejects impossible reactors', () => {\n  // pumpCount <= 0\n  expect(() => makeReactorCoolingSystem(0, 300, 600)).toThrow();\n\n  // initialTempC < 250\n  expect(() => makeReactorCoolingSystem(2, 249, 600)).toThrow();\n\n  // criticalTempC <= initialTempC\n  expect(() => makeReactorCoolingSystem(2, 300, 300)).toThrow();\n  expect(() => makeReactorCoolingSystem(2, 300, 250)).toThrow();\n});",
        "quote": "makeReactorCoolingSystem refuses to build a reactor that could not exist. Test each boundary from both sides.",
        "locator": "LA09.1 — STRETCH: Reject an impossible reactor",
        "tags": ["cpsc210", "ch09", "constructor-invariants", "boundary-testing", "code"]
    },
    {
        "card_type": "concept",
        "title": "Equivalence Class Partitioning for Inputs",
        "category": "Test Design",
        "difficulty": "Medium",
        "front": "In Chapter 9 test design, what is an input equivalence class, and how do you select test inputs from it?",
        "back": "- An **equivalence class** is a subset of input values where the program is specified to behave in the same manner. If one test input in the class succeeds (or fails), all other inputs in that class are assumed to do the same.\n- **Selection rule**: Pick at least **one typical value** from each valid equivalence class, **one value** from each invalid/error class, and **test each boundary** (on, just below, just above) between classes.",
        "quote": "The checklist for what cases to cover is equivalence class partitioning + boundary value analysis.",
        "locator": "Textbook Ch. 9 — Input Partitioning; Reid Holmes Piazza @313",
        "tags": ["cpsc210", "ch09", "equivalence-classes", "test-design"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Testing Out-of-Bounds Pump Indices (Boundary Throw)",
        "category": "Boundary Testing",
        "difficulty": "Easy",
        "front": "For a reactor with `pumpCount = 3`, write tests verifying that `setPumpOnline(i, online)` accepts valid indices and throws on out-of-bounds indices, specifically testing the exact boundary `i === pumpCount`.",
        "starter_code": "test('pump index boundaries', () => {\n  const reactor = makeReactorCoolingSystem(3, 300, 600);\n  // Test valid: 0 and 2. Test invalid: -1 and 3.\n});",
        "back": "test('pump index boundaries', () => {\n  const reactor = makeReactorCoolingSystem(3, 300, 600);\n  // Valid boundaries:\n  expect(() => reactor.setPumpOnline(0, false)).not.toThrow();\n  expect(() => reactor.setPumpOnline(2, false)).not.toThrow();\n\n  // Invalid boundaries:\n  expect(() => reactor.setPumpOnline(-1, false)).toThrow();\n  expect(() => reactor.setPumpOnline(3, false)).toThrow(); // index === pumpCount\n});",
        "quote": "An out-of-range pump index throws, including the index equal to pumpCount.",
        "locator": "LA09.1 — TASK 4: Boundaries and rejected inputs",
        "tags": ["cpsc210", "ch09", "boundary-values", "la09", "code"]
    },
    {
        "card_type": "concept",
        "title": "Testing Closures: Observable Behavior Only",
        "category": "Abstraction",
        "difficulty": "Medium",
        "front": "When validating a component created via factory function with closure-protected state (like `makeReactorCoolingSystem`), why and how do tests interact with internal state?",
        "back": "- **Why**: Internal variables inside the closure are completely invisible and unexported. Tests **must not** attempt to break encapsulation.\n- **How**: Tests interact exclusively through the **public interface** (calling mutators like `tick()` and observers like `snapshot()` or `evaluateSafety()`). This ensures tests validate **observable behavior** and won't break if internal implementation details change.",
        "quote": "The implementation is given: state is hidden in a closure. You do not need to read its code to write tests.",
        "locator": "LA09.1 — Domain Rules; Textbook Ch. 9",
        "tags": ["cpsc210", "ch09", "closures", "observable-behavior"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Vitest describe Block Organization",
        "category": "Test Architecture",
        "difficulty": "Easy",
        "front": "Show how to structure a Vitest test suite using nested `describe` blocks to organize behavior by functional area.",
        "starter_code": "import { describe, test, expect } from 'vitest';\n\n// Organize: Reactor Coolant System -> Power Limits vs Safety Evaluation",
        "back": "describe('ReactorCoolingSystem', () => {\n  describe('Power Control', () => {\n    test('accepts power between 0 and 1000', () => { /* ... */ });\n    test('throws on negative power', () => { /* ... */ });\n    test('throws on power above 1000', () => { /* ... */ });\n  });\n\n  describe('Safety Evaluation', () => {\n    test('reports emergency when all pumps offline under power', () => { /* ... */ });\n    test('reports warning when net heat is positive', () => { /* ... */ });\n  });\n});",
        "quote": "A test body is a block: local setup, several steps, several assertions.",
        "locator": "Textbook Ch. 9 — Test Structure (p. 194)",
        "tags": ["cpsc210", "ch09", "vitest", "describe-blocks"]
    },
    {
        "card_type": "concept",
        "title": "Testing Both Emergency Branches (LA09 Task 1)",
        "category": "Branch Coverage",
        "difficulty": "Medium",
        "front": "In LA09's cooling system, there are two distinct ways for the status to become 'emergency'. What are they, and why must both have independent tests?",
        "back": "1. **Temperature Emergency**: Temperature $\\ge$ `criticalTempC - 20`.\n2. **Total Pump Failure Under Power**: Every pump is offline AND power $> 0$.\n\n*Why both need tests*: They are two independent compound boolean clauses in the contract. A test covering high temperature will not catch a mutant that breaks the zero-pumps-under-power logic, and vice versa.",
        "quote": "evaluateSafety has four branches: emergency (temp >= critical - 20), emergency (all pumps offline under power), warning, and stable.",
        "locator": "LA09.1 — TASK 1: Partition inputs by status",
        "tags": ["cpsc210", "ch09", "branch-coverage", "la09"]
    },
    {
        "card_type": "code",
        "language": "typescript",
        "title": "Testing shouldScram Contract (LA09 Task 2)",
        "category": "Specification Testing",
        "difficulty": "Easy",
        "front": "Write a test asserting that `shouldScram` is `true` if and only if the status is `emergency`.",
        "starter_code": "test('shouldScram matches emergency status', () => {\n  // Assert shouldScram is true in emergency, false in warning\n});",
        "back": "test('shouldScram matches emergency status', () => {\n  const reactor = makeReactorCoolingSystem(1, 300, 600);\n  reactor.setPowerMw(100); // 12 heat < 18 cooling -> warning / stable\n  expect(reactor.evaluateSafety().shouldScram).toBe(false);\n\n  reactor.setPumpOnline(0, false); // 0 pumps online with power > 0 -> emergency\n  const report = reactor.evaluateSafety();\n  expect(report.status).toBe('emergency');\n  expect(report.shouldScram).toBe(true);\n});",
        "quote": "shouldScram is true only in an emergency.",
        "locator": "LA09.1 — Domain Rules & TASK 2; Textbook Ch. 9",
        "tags": ["cpsc210", "ch09", "scram", "la09", "code"]
    },
    {
        "card_type": "concept",
        "title": "Mocking Filesystem Dependencies with memfs",
        "category": "Mocking & Test Isolation",
        "difficulty": "Hard",
        "front": "Why is in-memory filesystem mocking (e.g. `memfs`) preferred over using real temporary files on disk when running large test suites?",
        "back": "1. **Speed**: In-memory mocking avoids physical disk I/O, allowing hundreds of file tests to run in milliseconds.\n2. **Deterministic Isolation**: Tests cannot conflict over shared filenames or leave orphan files behind after crashes.\n3. **OS Portability**: Avoids differences in Windows vs Linux file paths, line endings (`\\r\\n` vs `\\n`), or file permissions.",
        "quote": "If you found it tedious to write tests interacting with the file system, you may want to acquaint yourself with memfs.",
        "locator": "LA08.1 — Advanced Tips on Testing with the Filesystem; Textbook Ch. 9",
        "tags": ["cpsc210", "ch09", "mocking", "memfs", "test-speed"]
    },
    {
        "card_type": "concept",
        "title": "Test Naming by Observable Behaviour",
        "category": "Test Naming",
        "difficulty": "Easy",
        "front": "Why should tests be named by observable behaviour (e.g. `it('throws when power exceeds 1000MW')`) rather than implementation details (e.g. `it('tests line 45')`)?",
        "back": "1. **Living Specification**: Test titles serve as the executable documentation for the system. A new developer reads test names to understand what the system guarantees.\n2. **Resilience to Refactoring**: If the internal implementation is refactored, the test name remains completely valid because the observable behavior hasn't changed.\n3. **Clear Failure Diagnostics**: When CI reports a failure, the test title immediately explains which business contract was violated.",
        "quote": "Name tests by behaviour, not implementation details.",
        "locator": "LA09.1 — Workflow; Textbook Ch. 9 (p. 195)",
        "tags": ["cpsc210", "ch09", "test-naming", "best-practices"]
    }
]


async def generate_and_ingest():
    # 1. Save JSON files to disk
    ch8_json_path = os.path.join(CARDS_DOCS_DIR, "cpsc210_ch8_designing_for_failure.json")
    ch9_json_path = os.path.join(CARDS_DOCS_DIR, "cpsc210_ch9_validating_behaviour.json")

    with open(ch8_json_path, "w", encoding="utf-8") as f:
        json.dump(CH8_CARDS, f, indent=2)
    logger.info(f"Saved {len(CH8_CARDS)} cards to {ch8_json_path}")

    with open(ch9_json_path, "w", encoding="utf-8") as f:
        json.dump(CH9_CARDS, f, indent=2)
    logger.info(f"Saved {len(CH9_CARDS)} cards to {ch9_json_path}")

    # Also mirror into Cards/Cards/3 - Textbook Ch1-7 for consistency
    mirror_dir = r"C:\Users\micha\OneDrive\Documents\UBC BCS ICS\CPSC 210\Cards\Cards\3 - Textbook Ch1-7"
    if os.path.exists(mirror_dir):
        with open(os.path.join(mirror_dir, "cpsc210_ch8_designing_for_failure.json"), "w", encoding="utf-8") as f:
            json.dump(CH8_CARDS, f, indent=2)
        with open(os.path.join(mirror_dir, "cpsc210_ch9_validating_behaviour.json"), "w", encoding="utf-8") as f:
            json.dump(CH9_CARDS, f, indent=2)
        logger.info(f"Mirrored JSON files to {mirror_dir}")

    # 2. Ingest into dev.db
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == USER_EMAIL))
        if not user:
            logger.error("User not found!")
            return

        # Find Chapter 8 and 9 decks
        decks = (await db.scalars(select(Deck).where(Deck.user_id == user.id))).all()
        ch8_deck = None
        ch9_deck = None

        for d in decks:
            if "Ch 08" in d.name:
                ch8_deck = d
            elif "Ch 09" in d.name:
                ch9_deck = d

        if not ch8_deck or not ch9_deck:
            logger.error("Could not find Ch 08 or Ch 09 decks!")
            return

        # Rename to remove '!' prefix since documents and cards are now complete
        if ch8_deck.name.startswith("! "):
            ch8_deck.name = ch8_deck.name[2:]
            logger.info(f"Cleared '!' prefix: '{ch8_deck.name}'")
        if ch9_deck.name.startswith("! "):
            ch9_deck.name = ch9_deck.name[2:]
            logger.info(f"Cleared '!' prefix: '{ch9_deck.name}'")

        async def ingest_cards(card_list: list[dict], target_deck: Deck, chapter_num: int):
            count = 0
            for item in card_list:
                card_type = item.get("card_type", "concept")
                is_code = card_type == "code" or bool(item.get("starter_code"))

                front = item["front"].strip()
                back = item["back"].strip()
                starter_code = item.get("starter_code")
                test_cases = item.get("test_cases")
                quote = (item.get("quote") or "").strip()
                locator = (item.get("locator") or "").strip()

                field_values: dict = {"Front": front, "Back": back}
                if is_code:
                    if starter_code:
                        field_values["starter_code"] = starter_code
                    if test_cases:
                        field_values["test_cases"] = test_cases
                    for k in ["title", "category", "difficulty", "time_complexity", "space_complexity", "edge_cases"]:
                        if item.get(k):
                            field_values[k] = item[k]

                profile = "math_code" if is_code else "short_answer"
                nt = await default_note_type(db, user, "basic", grading_profile=profile)
                note_row = Note(user_id=user.id, note_type_id=nt.id, field_values=field_values)
                db.add(note_row)
                await db.flush()

                tags = list(item.get("tags") or [])
                if is_code and "code" not in tags:
                    tags.append("code")
                if "cpsc210" not in tags:
                    tags.append("cpsc210")
                tags.append(f"ch0{chapter_num}")

                doc_parts = []
                if locator:
                    doc_parts.append(f"**Locator**: {locator}")
                if quote:
                    doc_parts.append(f"**Key Quote**: \"{quote}\"")
                if item.get("time_complexity") or item.get("space_complexity"):
                    tc = item.get("time_complexity", "N/A")
                    sc = item.get("space_complexity", "N/A")
                    doc_parts.append(f"**Complexity**: Time `{tc}`, Space `{sc}`")
                card_doc = "\n\n".join(doc_parts) if doc_parts else target_deck.documentation

                card_sources = [
                    {
                        "name": "CPSC210_2026W1_Master.pdf",
                        "locator": locator,
                        "quote": quote,
                        "source_file": f"cpsc210_ch{chapter_num}.json",
                    }
                ]

                cards = await sync_cards(
                    db,
                    note_row,
                    nt,
                    target_deck.id,
                    tags=tags,
                    priority=item.get("priority", 50),
                    origin="manual",
                    documentation=card_doc,
                    thematic_nature=item.get("category") or target_deck.thematic_nature,
                    source_documents=card_sources,
                )
                count += len(cards)

                if quote or locator:
                    for c in cards:
                        db.add(
                            CardReference(
                                card_id=c.id,
                                quote=quote or (f"Excerpt from {locator}" if locator else ""),
                                quote_verified=True,
                                locator=locator,
                                source_title=f"CPSC 210 — {target_deck.name}",
                            )
                        )

            return count

        c8 = await ingest_cards(CH8_CARDS, ch8_deck, 8)
        c9 = await ingest_cards(CH9_CARDS, ch9_deck, 9)

        await db.commit()
        logger.info(f"Ingested {c8} cards into '{ch8_deck.name}'")
        logger.info(f"Ingested {c9} cards into '{ch9_deck.name}'")
        logger.info("Successfully generated and ingested all Ch 8 and Ch 9 cards!")


if __name__ == "__main__":
    asyncio.run(generate_and_ingest())

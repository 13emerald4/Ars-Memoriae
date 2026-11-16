"""Part 4 · Hands-On Labs — guide configuration."""

from common import COMMON_DEVIATIONS, TODAY, c, note

FILENAME = "part4-hands-on-labs"
TITLE = "Part 4 · Hands-On Labs"
SUBTITLE = "A Socratic study guide to the 5 cards of Part 4 of “JavaScript & TypeScript: Zero to Mastery”"
META_QUESTION = "How do you combine the pieces from Parts 1–3 into a small program that is correct on every input?"
META_DECOMPOSITION = (
    "Part A asks how plain JavaScript programs are built (cleaning input, guarding data, building results "
    "in a loop); B, how TypeScript's types carry a program (checking unknown input, typed results, "
    "reducers). Every section heading is a question, answered in its first sentence; every code sample "
    "was run or compiled. The Card-by-Card Solution Guide then works every card in the deck."
)

GROUPS = [
    ("A. How do the JavaScript pieces combine?", "Cleaning input, guarding data and building results.", ["c26"]),
    ("B. How do types carry a program?", "unknown input, typed results and reducers.", ["c27"]),
]

SYNTHESIS = r"""
A program is correct when it is right on every input it may receive, not just on the example in the task. Each Part is one way of making sure.

\textbf{The JavaScript habits (A).} Cleaning the input first shrinks the set of inputs the main logic must handle. Validating before changing data keeps each invariant true even when a call is rejected. An accumulator plus a final flush turns ``process each piece'' into a complete result. The edge cases---empty text, a zero, an exact fit---are where each habit is tested.

\textbf{What the types add (B).} \code{unknown} makes the program prove the shape of outside data before using it. A discriminated result makes every caller handle failure, because the value cannot be read otherwise. A \code{readonly} state makes the compiler reject changes in place, so a reducer can only build new state. Each turns a habit from Part A into a rule the compiler checks.

\textbf{The strongest objection} is that tests already catch these bugs. They catch the cases someone thought to write; the habits and types guard the cases nobody wrote down---which is why every lab's tests include the edge cases as well.
"""

TEST_QUESTIONS = [
    ("Why must an empty cell be tested before `Number(cell)`?", "c26"),
    ("What is an invariant, and why validate before changing any data?", "c26"),
    ("In a word-wrap loop, what is still left to do when the loop ends?", "c26"),
    ("What can you do with an `unknown` value before narrowing it, and how do you narrow it to an object?", "c27"),
    ("Why does `{ ok: true; value } | { ok: false; error }` force a caller to check `ok`?", "c27"),
    ("Which array methods does `readonly` reject, and which build new arrays instead?", "c27"),
]

SNIPPETS = {
    "c26-plan": {"lang": "js", "code": c("""
        const text = "a,b\\n\\n   \\n1,2\\n";
        const lines = text
          .split("\\n")
          .map((line) => line.trim())
          .filter(Boolean);
        console.log(lines.length, lines[0]);
        console.log(Number(""), Number.isNaN(Number("x")));
    """), "out": "2 a,b\n0 true"},
    "c26-state": {"lang": "js", "code": c("""
        class Stock {
          #n = 0;
          add(k) { this.#n += k; return this.#n; }
          take(k) {
            if (k > this.#n) throw new RangeError("not enough");
            this.#n -= k;
          }
        }
        const s = new Stock();
        s.add(2);
        try { s.take(5); } catch (e) { console.log(e.name); }
        console.log(s.add(0));
    """), "out": "RangeError\n2"},
    "c26-accumulate": {"lang": "js", "code": c("""
        const words = ["ab", "cd", "ef"];
        const lines = [];
        let line = "";
        for (const w of words) {
          if (line && line.length + 1 + w.length > 5) {
            lines.push(line);
            line = w;
          } else line = line ? line + " " + w : w;
        }
        if (line) lines.push(line);
        console.log(lines.join("|"));
    """), "out": "ab cd|ef"},
    "c27-unknown": {"lang": "ts", "compile": [], "code": c("""
        function size(input: unknown): number {
          if (typeof input === "object" && input !== null && "length" in input) {
            return typeof input.length === "number" ? input.length : 0;
          }
          return 0;
        }
        console.log(size([1, 2]), size(null), size("hi"));
    """), "out": "2 0 0"},
    "c27-result": {"lang": "ts", "compile": [7], "code": c("""
        type Result = { ok: true; value: number } | { ok: false; error: string };
        function check(n: number): Result {
          return n >= 0 ? { ok: true, value: n } : { ok: false, error: "negative" };
        }
        const r = check(-1);
        console.log(r.ok ? r.value : r.error);
        console.log(r.value);
    """), "out": "negative\nundefined"},
    "c27-reducer": {"lang": "ts", "compile": [8], "code": c("""
        type Todo = { id: number; done: boolean };
        function toggle(state: readonly Todo[], id: number): Todo[] {
          return state.map((t) => (t.id === id ? { ...t, done: !t.done } : t));
        }
        const before: readonly Todo[] = [{ id: 1, done: false }];
        const after = toggle(before, 1);
        console.log(after[0].done, before[0].done);
        before.push({ id: 2, done: false });
    """), "out": "true false"},
}

CARDS = {
    "lab-parse-csv": note(["c26"], ["c26-plan", "c26-accumulate"],
        "Split into lines, trim and drop blank ones; take the headers from the first line; map every other "
        "line to an object, converting a cell to a number only if it is non-empty and not NaN.",
        "Every row object has every header as a key; a missing cell is \"\".",
        "One array of lines, one object per row.",
        "string in; array of objects out.",
        "`Number(cells[i]) || cells[i]` turns \"0\" into the string \"0\"; not filtering blank lines adds empty rows.",
        "Plain CSV, spaces and blank lines, an empty cell, a 0, headers only, empty text.",
        "`Number(\"\")` is 0: check for the empty cell first."),
    "lab-inventory": note(["c26"], ["c26-state"],
        "Keep a private `#stock` Map; validate the quantity (and, for remove, what you have) before changing "
        "anything; delete an item that reaches 0.",
        "No quantity is 0 or below, and a rejected call changes nothing.",
        "One Map from item to quantity.",
        "string and number in; number or string array out.",
        "Setting 0 instead of deleting leaves empty items in `items()`; skipping the checks lets stock go negative.",
        "Add then remove, removing too much, quantity 0, unknown item, items sorted after a removal.",
        "Validate before you change anything."),
    "lab-word-wrap": note(["c26"], ["c26-accumulate"],
        "Keep the current line; per word, append it (with one space) if the result is at most `width`, "
        "otherwise push the line and start a new one; push the last line after the loop.",
        "No pushed line is longer than `width` unless it is a single long word.",
        "One current line, one array of lines.",
        "string and number in; string array out.",
        "`<` instead of `<=` breaks lines that fit exactly; forgetting the final push drops the last line.",
        "Normal text, an exact fit, one over, a word longer than width, width 1, empty text.",
        "Push the last line after the loop."),
    "lab-validate-signup": note(["c27"], ["c27-unknown", "c27-result"],
        "Rule out non-objects and null; read `email` and `age` with `in`; collect each error in order; "
        "return `{ ok: true, value: { email, age } }` only when both checks pass.",
        "ok is true exactly when errors would be empty; value holds only email and age.",
        "One array of error messages.",
        "unknown in; Result (a discriminated union on ok) out.",
        "Returning at the first error reports only one problem; returning `input` itself keeps extra fields.",
        "Valid, extra field, bad email, too young, not whole, exactly 13, empty object, null, a string.",
        "Collect every error before returning."),
    "lab-todo-reducer": note(["c27"], ["c27-reducer", "c27-result"],
        "Switch on `action.type`: add appends a new todo with id = largest id + 1; toggle maps the matching id "
        "to a copy with `done` flipped; remove filters it out.",
        "state is never changed; ids stay unique after removals.",
        "One new array per call; unchanged todos are shared.",
        "readonly Todo[] and Action in; Todo[] out.",
        "`state.length + 1` reuses an id after a removal; `state.push` doesn't compile on a readonly array.",
        "Add to empty, add after id 3, toggle, toggle a missing id, remove; type tests reject a bad action.",
        "Take the next id from the largest id, not the length."),
}

SOURCES = [
    (r"Course deck: \path{backend/app/content/js_ts_course/part4.py}, \path{quotes.py}", "In full",
     "Cards, tests, type tests, solutions, quotes, deck summaries"),
    ("MDN reference (source text): String.prototype.trim(), String.prototype.split(), RangeError",
     "The cited pages' opening sections", "Card quotes"),
    ("TypeScript Handbook (source text): Narrowing (the in operator); Object Types (ReadonlyArray)",
     "Relevant sections", "Ch.~27; card quotes"),
]
NOT_READ = ("The MDN JavaScript Guide and Keyed collections pages listed in the deck summaries were not "
            "re-read for this guide beyond the cited quotes; nothing else from Parts 1–3 was re-read.")

FLAGS = [
    "Outside the material: Ch.~26's claims (Number(\"\") is 0, validating first, flushing the last piece) "
    "were established by running code in Node, not from a quoted page.",
    "Ch.~27 relies on Part~3, Ch.~21 for discriminated unions; that chapter is in the Part~3 guide, not "
    "this one, so the term is restated briefly instead of linked.",
    "Conflicts: none found between the deck and the documentation.",
]

DEVIATIONS = COMMON_DEVIATIONS + [
    "Ch.~27's Result snippet deliberately includes one line that fails to compile (reading value without "
    "checking ok); the run shows what that line would print if the error were ignored.",
]
REVISIONS = [f"{TODAY}: first version."]

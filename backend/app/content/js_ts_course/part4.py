"""Part 4: hands-on labs — small programs that combine the earlier skills."""

from __future__ import annotations

from .model import MDN_JS, TS_HANDBOOK, CodeCard, Part, Source, Subdeck
from .part1 import c

TS = "typescript"

INVENTORY_DRIVER = """\
// Test driver: don't change. Runs each [method, ...args] and records the result.
function run(actions) {
  const inventory = new Inventory();
  return actions.map(([method, ...args]) => {
    try {
      return inventory[method](...args);
    } catch (error) {
      return `${error.name}: ${error.message}`;
    }
  });
}
"""

JS_LABS = Subdeck(
    name="26 · JavaScript Labs",
    summary=(
        "Small programs that combine strings, arrays, objects, Maps, classes and errors. Read "
        "the whole task first, then build it a step at a time; the tests cover the edge cases."
    ),
    sources=[
        Source("MDN — JavaScript Guide", MDN_JS + "Guide"),
        Source("MDN — Keyed collections", MDN_JS + "Guide/Keyed_collections"),
    ],
    cards=[
        CodeCard(
            key="lab-parse-csv",
            title="parseCsv(text)",
            task=(
                "Write `parseCsv(text)`: the first line holds the column names; turn every other "
                "line into an object keyed by them. Trim spaces around cells, skip blank lines, "
                'and turn cells that are numbers into numbers (`"36"` → 36). No lines at all → `[]`.'
            ),
            starter=c("""
                function parseCsv(text) {
                  // TODO
                  return [];
                }
            """),
            solution=c("""
                function parseCsv(text) {
                  const lines = text
                    .split("\\n")
                    .map((line) => line.trim())
                    .filter(Boolean);
                  if (lines.length === 0) return [];
                  const headers = lines[0].split(",").map((h) => h.trim());
                  return lines.slice(1).map((line) => {
                    const cells = line.split(",").map((cell) => cell.trim());
                    const row = {};
                    headers.forEach((header, i) => {
                      const cell = cells[i] ?? "";
                      row[header] = cell !== "" && !Number.isNaN(Number(cell)) ? Number(cell) : cell;
                    });
                    return row;
                  });
                }
            """),
            tests=[
                {
                    "input": ["name,age\nAda,36\nGrace,85"],
                    "expected": [{"name": "Ada", "age": 36}, {"name": "Grace", "age": 85}],
                },
                {
                    "input": [" name , city \n\n   \n Linus , Helsinki \n"],
                    "expected": [{"name": "Linus", "city": "Helsinki"}],
                },
                {"input": ["id,label\n7,"], "expected": [{"id": 7, "label": ""}]},
                {"input": ["item,qty\npens,0"], "expected": [{"item": "pens", "qty": 0}]},
                {"input": ["name,age"], "expected": []},
                {"input": [""], "expected": []},
            ],
            wrong=[
                c("""
                    function parseCsv(text) {
                      const lines = text.split("\\n");
                      if (lines.length === 0) return [];
                      const headers = lines[0].split(",").map((h) => h.trim());
                      return lines.slice(1).map((line) => {
                        const cells = line.split(",").map((cell) => cell.trim());
                        const row = {};
                        headers.forEach((header, i) => {
                          const cell = cells[i] ?? "";
                          row[header] = cell !== "" && !Number.isNaN(Number(cell)) ? Number(cell) : cell;
                        });
                        return row;
                      });
                    }
                """),
                c("""
                    function parseCsv(text) {
                      const lines = text
                        .split("\\n")
                        .map((line) => line.trim())
                        .filter(Boolean);
                      if (lines.length === 0) return [];
                      const headers = lines[0].split(",").map((h) => h.trim());
                      return lines.slice(1).map((line) => {
                        const cells = line.split(",").map((cell) => cell.trim());
                        const row = {};
                        headers.forEach((header, i) => {
                          row[header] = Number(cells[i]) || cells[i];
                        });
                        return row;
                      });
                    }
                """),
            ],
            why=(
                'Number("") is 0, so test for empty cells before converting. Splitting, '
                "trimming and filtering the lines first keeps the row logic simple."
            ),
            difficulty="Medium",
        ),
        CodeCard(
            key="lab-inventory",
            title="class Inventory",
            task=(
                "Finish `Inventory`, storing quantities in a private `Map`. `add(item, qty)` and "
                "`remove(item, qty)` return the new quantity; `count(item)` is 0 for unknown items; "
                '`items()` lists items in stock, sorted. Throw `RangeError("quantity must be '
                'positive")` for a quantity of 0 or less and `RangeError("not enough <item>")` '
                "when removing more than you have. An item that reaches 0 is no longer in stock. "
                "Don't change `run`."
            ),
            starter=INVENTORY_DRIVER
            + c("""

                class Inventory {
                  // TODO: #stock = new Map(); add, remove, count, items
                }
            """),
            solution=INVENTORY_DRIVER
            + c("""

                class Inventory {
                  #stock = new Map();

                  add(item, quantity) {
                    if (quantity <= 0) throw new RangeError("quantity must be positive");
                    const total = this.count(item) + quantity;
                    this.#stock.set(item, total);
                    return total;
                  }

                  remove(item, quantity) {
                    if (quantity <= 0) throw new RangeError("quantity must be positive");
                    const have = this.count(item);
                    if (quantity > have) throw new RangeError(`not enough ${item}`);
                    const left = have - quantity;
                    if (left === 0) this.#stock.delete(item);
                    else this.#stock.set(item, left);
                    return left;
                  }

                  count(item) {
                    return this.#stock.get(item) ?? 0;
                  }

                  items() {
                    return [...this.#stock.keys()].sort();
                  }
                }
            """),
            tests=[
                {
                    "input": [[["add", "apple", 5], ["remove", "apple", 2], ["count", "apple"]]],
                    "expected": [5, 3, 3],
                },
                {"input": [[["remove", "pear", 1]]], "expected": ["RangeError: not enough pear"]},
                {
                    "input": [[["add", "kiwi", 0]]],
                    "expected": ["RangeError: quantity must be positive"],
                },
                {"input": [[["count", "fig"]]], "expected": [0]},
                {
                    "input": [[["add", "a", 1], ["remove", "a", 0]]],
                    "expected": [1, "RangeError: quantity must be positive"],
                },
                {
                    "input": [[["add", "b", 1], ["add", "a", 2], ["remove", "b", 1], ["items"]]],
                    "expected": [1, 2, 0, ["a"]],
                },
                {
                    "input": [[["add", "a", 1], ["remove", "a", 2], ["count", "a"]]],
                    "expected": [1, "RangeError: not enough a", 1],
                },
            ],
            wrong=[
                INVENTORY_DRIVER
                + c("""

                    class Inventory {
                      #stock = new Map();

                      add(item, quantity) {
                        if (quantity <= 0) throw new RangeError("quantity must be positive");
                        const total = this.count(item) + quantity;
                        this.#stock.set(item, total);
                        return total;
                      }

                      remove(item, quantity) {
                        if (quantity <= 0) throw new RangeError("quantity must be positive");
                        const have = this.count(item);
                        if (quantity > have) throw new RangeError(`not enough ${item}`);
                        this.#stock.set(item, have - quantity);
                        return have - quantity;
                      }

                      count(item) {
                        return this.#stock.get(item) ?? 0;
                      }

                      items() {
                        return [...this.#stock.keys()].sort();
                      }
                    }
                """),
                INVENTORY_DRIVER
                + c("""

                    class Inventory {
                      #stock = new Map();

                      add(item, quantity) {
                        const total = this.count(item) + quantity;
                        this.#stock.set(item, total);
                        return total;
                      }

                      remove(item, quantity) {
                        const left = this.count(item) - quantity;
                        if (left <= 0) this.#stock.delete(item);
                        else this.#stock.set(item, left);
                        return left;
                      }

                      count(item) {
                        return this.#stock.get(item) ?? 0;
                      }

                      items() {
                        return [...this.#stock.keys()].sort();
                      }
                    }
                """),
            ],
            why=(
                "Validate before changing anything, so a rejected call leaves the stock as it "
                "was. Deleting empty items keeps items() honest."
            ),
            difficulty="Medium",
        ),
        CodeCard(
            key="lab-word-wrap",
            title="wordWrap(text, width)",
            task=(
                "Write `wordWrap(text, width)`: split `text` into lines of at most `width` "
                "characters, breaking only at spaces. A word longer than `width` gets a line of "
                "its own. Return the lines as an array (`[]` for empty text)."
            ),
            starter=c("""
                function wordWrap(text, width) {
                  // TODO
                  return [text];
                }
            """),
            solution=c("""
                function wordWrap(text, width) {
                  const lines = [];
                  let line = "";
                  for (const word of text.split(" ").filter(Boolean)) {
                    if (line === "") {
                      line = word;
                    } else if (line.length + 1 + word.length <= width) {
                      line += " " + word;
                    } else {
                      lines.push(line);
                      line = word;
                    }
                  }
                  if (line !== "") lines.push(line);
                  return lines;
                }
            """),
            tests=[
                {"input": ["the quick brown fox", 10], "expected": ["the quick", "brown fox"]},
                {"input": ["exactly ten", 11], "expected": ["exactly ten"]},
                {"input": ["exactly ten", 10], "expected": ["exactly", "ten"]},
                {
                    "input": ["supercalifragilistic is long", 10],
                    "expected": ["supercalifragilistic", "is long"],
                },
                {"input": ["a b c", 1], "expected": ["a", "b", "c"]},
                {"input": ["", 5], "expected": []},
            ],
            wrong=[
                c("""
                    function wordWrap(text, width) {
                      const lines = [];
                      let line = "";
                      for (const word of text.split(" ").filter(Boolean)) {
                        if (line === "") {
                          line = word;
                        } else if (line.length + 1 + word.length < width) {
                          line += " " + word;
                        } else {
                          lines.push(line);
                          line = word;
                        }
                      }
                      if (line !== "") lines.push(line);
                      return lines;
                    }
                """),
                c("""
                    function wordWrap(text, width) {
                      const lines = [];
                      let line = "";
                      for (const word of text.split(" ").filter(Boolean)) {
                        if (line === "") {
                          line = word;
                        } else if (line.length + 1 + word.length <= width) {
                          line += " " + word;
                        } else {
                          lines.push(line);
                          line = word;
                        }
                      }
                      return lines;
                    }
                """),
            ],
            why=(
                "Keep a current line and decide per word whether it fits (+1 for the space). "
                "Don't forget to push the last line after the loop."
            ),
            difficulty="Medium",
        ),
    ],
)

TS_LABS = Subdeck(
    name="27 · TypeScript Labs",
    summary=(
        "Programs where the types do real work: validating untrusted input into a "
        "discriminated result, and a reducer over immutable state."
    ),
    sources=[
        Source("TypeScript Handbook — Narrowing", TS_HANDBOOK + "narrowing.html"),
        Source("TypeScript Handbook — Object Types", TS_HANDBOOK + "objects.html"),
    ],
    cards=[
        CodeCard(
            key="lab-validate-signup",
            language=TS,
            title="validateSignup(input: unknown)",
            task=(
                "Change `Result` to a discriminated union — `{ ok: true; value: Signup }` or "
                "`{ ok: false; errors: string[] }` — and write `validateSignup`. Not an object → "
                '`["input must be an object"]`. Otherwise collect, in this order, '
                '`"email is invalid"` (email must be a string containing "@") and '
                '`"age must be 13 or older"` (a whole number ≥ 13). A valid signup returns only '
                "its email and age."
            ),
            starter=c("""
                type Signup = { email: string; age: number };
                type Result = { ok: boolean; value?: Signup; errors?: string[] };

                function validateSignup(input: unknown): Result {
                  // TODO
                  return { ok: true };
                }
            """),
            solution=c("""
                type Signup = { email: string; age: number };
                type Result = { ok: true; value: Signup } | { ok: false; errors: string[] };

                function validateSignup(input: unknown): Result {
                  if (typeof input !== "object" || input === null) {
                    return { ok: false, errors: ["input must be an object"] };
                  }
                  const email = "email" in input ? input.email : undefined;
                  const age = "age" in input ? input.age : undefined;
                  const errors: string[] = [];
                  if (typeof email !== "string" || !email.includes("@")) errors.push("email is invalid");
                  if (typeof age !== "number" || !Number.isInteger(age) || age < 13) {
                    errors.push("age must be 13 or older");
                  }
                  if (typeof email === "string" && typeof age === "number" && errors.length === 0) {
                    return { ok: true, value: { email, age } };
                  }
                  return { ok: false, errors };
                }
            """),
            tests=[
                {
                    "input": [{"email": "ada@example.com", "age": 36}],
                    "expected": {"ok": True, "value": {"email": "ada@example.com", "age": 36}},
                },
                {
                    "input": [{"email": "ada@example.com", "age": 36, "admin": True}],
                    "expected": {"ok": True, "value": {"email": "ada@example.com", "age": 36}},
                },
                {
                    "input": [{"email": "ada.example.com", "age": 36}],
                    "expected": {"ok": False, "errors": ["email is invalid"]},
                },
                {
                    "input": [{"email": "ada@example.com", "age": 12}],
                    "expected": {"ok": False, "errors": ["age must be 13 or older"]},
                },
                {
                    "input": [{"email": "a@b.c", "age": 13.5}],
                    "expected": {"ok": False, "errors": ["age must be 13 or older"]},
                },
                {
                    "input": [{"email": "a@b.c", "age": 13}],
                    "expected": {"ok": True, "value": {"email": "a@b.c", "age": 13}},
                },
                {
                    "input": [{}],
                    "expected": {
                        "ok": False,
                        "errors": ["email is invalid", "age must be 13 or older"],
                    },
                },
                {"input": [None], "expected": {"ok": False, "errors": ["input must be an object"]}},
                {
                    "input": ["hello"],
                    "expected": {"ok": False, "errors": ["input must be an object"]},
                },
            ],
            type_tests=c("""
                const r = validateSignup({});
                if (r.ok) {
                  const email: string = r.value.email;
                } else {
                  const first: string | undefined = r.errors[0];
                }
                // @ts-expect-error: errors only exist when ok is false
                r.errors;
            """),
            wrong=[
                c("""
                    type Signup = { email: string; age: number };
                    type Result = { ok: true; value: Signup } | { ok: false; errors: string[] };

                    function validateSignup(input: unknown): Result {
                      if (typeof input !== "object" || input === null) {
                        return { ok: false, errors: ["input must be an object"] };
                      }
                      const email = "email" in input ? input.email : undefined;
                      const age = "age" in input ? input.age : undefined;
                      if (typeof email !== "string" || !email.includes("@")) {
                        return { ok: false, errors: ["email is invalid"] };
                      }
                      if (typeof age !== "number" || !Number.isInteger(age) || age < 13) {
                        return { ok: false, errors: ["age must be 13 or older"] };
                      }
                      return { ok: true, value: { email, age } };
                    }
                """),
            ],
            why=(
                "With `ok` as the discriminant, code that checks r.ok gets r.value; code that "
                "doesn't can't touch either field. Collect every error before returning, so the "
                "user can fix them all at once."
            ),
            source=Source("TypeScript Handbook — Narrowing", TS_HANDBOOK + "narrowing.html"),
            difficulty="Hard",
        ),
        CodeCard(
            key="lab-todo-reducer",
            language=TS,
            title="todos(state, action)",
            task=(
                "Write the reducer `todos(state, action)`. It must never change `state` (typed "
                "`readonly`) and always return a new array. `add` appends `{ id, title, done: "
                "false }` with id one more than the largest id (1 for an empty list); `toggle` "
                "flips `done` on the matching id; `remove` drops it."
            ),
            starter=c("""
                type Todo = { id: number; title: string; done: boolean };
                type Action =
                  | { type: "add"; title: string }
                  | { type: "toggle"; id: number }
                  | { type: "remove"; id: number };

                function todos(state: readonly Todo[], action: Action): Todo[] {
                  // TODO: return a new array; never change state
                  return [...state];
                }
            """),
            solution=c("""
                type Todo = { id: number; title: string; done: boolean };
                type Action =
                  | { type: "add"; title: string }
                  | { type: "toggle"; id: number }
                  | { type: "remove"; id: number };

                function todos(state: readonly Todo[], action: Action): Todo[] {
                  switch (action.type) {
                    case "add": {
                      const id = state.reduce((max, todo) => Math.max(max, todo.id), 0) + 1;
                      return [...state, { id, title: action.title, done: false }];
                    }
                    case "toggle":
                      return state.map((todo) => (todo.id === action.id ? { ...todo, done: !todo.done } : todo));
                    case "remove":
                      return state.filter((todo) => todo.id !== action.id);
                  }
                }
            """),
            tests=[
                {
                    "input": [[], {"type": "add", "title": "Write"}],
                    "expected": [{"id": 1, "title": "Write", "done": False}],
                },
                {
                    "input": [
                        [{"id": 3, "title": "a", "done": False}],
                        {"type": "add", "title": "b"},
                    ],
                    "expected": [
                        {"id": 3, "title": "a", "done": False},
                        {"id": 4, "title": "b", "done": False},
                    ],
                },
                {
                    "input": [
                        [
                            {"id": 1, "title": "a", "done": False},
                            {"id": 2, "title": "b", "done": True},
                        ],
                        {"type": "toggle", "id": 2},
                    ],
                    "expected": [
                        {"id": 1, "title": "a", "done": False},
                        {"id": 2, "title": "b", "done": False},
                    ],
                },
                {
                    "input": [
                        [{"id": 1, "title": "a", "done": False}],
                        {"type": "toggle", "id": 9},
                    ],
                    "expected": [{"id": 1, "title": "a", "done": False}],
                },
                {
                    "input": [
                        [
                            {"id": 1, "title": "a", "done": False},
                            {"id": 2, "title": "b", "done": False},
                        ],
                        {"type": "remove", "id": 1},
                    ],
                    "expected": [{"id": 2, "title": "b", "done": False}],
                },
            ],
            type_tests=c("""
                const empty: readonly Todo[] = [];
                const next: Todo[] = todos(empty, { type: "add", title: "x" });
                // @ts-expect-error: toggle needs an id
                todos(empty, { type: "toggle" });
                // @ts-expect-error: there is no "clear" action
                todos(empty, { type: "clear" });
            """),
            wrong=[
                c("""
                    type Todo = { id: number; title: string; done: boolean };
                    type Action =
                      | { type: "add"; title: string }
                      | { type: "toggle"; id: number }
                      | { type: "remove"; id: number };

                    function todos(state: readonly Todo[], action: Action): Todo[] {
                      switch (action.type) {
                        case "add":
                          state.push({ id: state.length + 1, title: action.title, done: false });
                          return [...state];
                        case "toggle":
                          return state.map((todo) => (todo.id === action.id ? { ...todo, done: !todo.done } : todo));
                        case "remove":
                          return state.filter((todo) => todo.id !== action.id);
                      }
                    }
                """),
                c("""
                    type Todo = { id: number; title: string; done: boolean };
                    type Action =
                      | { type: "add"; title: string }
                      | { type: "toggle"; id: number }
                      | { type: "remove"; id: number };

                    function todos(state: readonly Todo[], action: Action): Todo[] {
                      switch (action.type) {
                        case "add":
                          return [...state, { id: state.length + 1, title: action.title, done: false }];
                        case "toggle":
                          return state.map((todo) => (todo.id === action.id ? { ...todo, done: !todo.done } : todo));
                        case "remove":
                          return state.filter((todo) => todo.id !== action.id);
                      }
                    }
                """),
            ],
            why=(
                "`readonly Todo[]` makes the compiler reject push, splice and friends on state. "
                "map, filter and spread build new arrays. Ids come from the largest id, not the "
                "length, or removing an item would reuse an id."
            ),
            source=Source("TypeScript Handbook — Object Types", TS_HANDBOOK + "objects.html"),
            difficulty="Hard",
        ),
    ],
)


PART4 = Part(
    name="Part 4 · Hands-On Labs",
    summary="Bigger exercises that combine the skills from Parts 1–3. Each is still one function or class.",
    subdecks=[JS_LABS, TS_LABS],
)

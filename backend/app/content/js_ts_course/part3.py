"""Part 3: intermediate TypeScript — modelling data and reusable code."""

from __future__ import annotations

from .model import TS_DOCS, TS_HANDBOOK, CodeCard, CompileCard, Part, Source, Subdeck
from .part1 import c

TS = "typescript"
UTILITY = TS_DOCS + "utility-types.html"
TS49 = TS_DOCS + "release-notes/typescript-4-9.html"

# ── 21 ────────────────────────────────────────────────────────────────────

UNIONS = Subdeck(
    name="21 · Discriminated Unions & Exhaustiveness",
    summary=(
        'Give each variant of a union a literal tag (`kind: "circle"`) and checking the tag '
        "narrows to that variant. Assigning the leftover value to `never` in the `default` "
        "branch makes the compiler flag any variant you forgot."
    ),
    sources=[
        Source(
            "TypeScript Handbook — Narrowing: discriminated unions", TS_HANDBOOK + "narrowing.html"
        )
    ],
    cards=[
        CodeCard(
            key="ts21-area",
            language=TS,
            title="area(shape)",
            task=(
                "Finish `area` for every `Shape`, switching on `kind`, and add a `default` branch "
                "that assigns `shape` to a `never` variable so a new shape can't be forgotten."
            ),
            starter=c("""
                type Shape =
                  | { kind: "circle"; radius: number }
                  | { kind: "square"; side: number }
                  | { kind: "rect"; width: number; height: number };

                function area(shape: Shape): number {
                  switch (shape.kind) {
                    case "circle":
                      return Math.PI * shape.radius ** 2;
                    // TODO: square, rect, and a never check
                  }
                }
            """),
            solution=c("""
                type Shape =
                  | { kind: "circle"; radius: number }
                  | { kind: "square"; side: number }
                  | { kind: "rect"; width: number; height: number };

                function area(shape: Shape): number {
                  switch (shape.kind) {
                    case "circle":
                      return Math.PI * shape.radius ** 2;
                    case "square":
                      return shape.side ** 2;
                    case "rect":
                      return shape.width * shape.height;
                    default: {
                      const unreachable: never = shape;
                      throw new Error(`unknown shape: ${JSON.stringify(unreachable)}`);
                    }
                  }
                }
            """),
            tests=[
                {"input": [{"kind": "circle", "radius": 1}], "expected": 3.141592653589793},
                {"input": [{"kind": "square", "side": 3}], "expected": 9},
                {"input": [{"kind": "rect", "width": 2, "height": 5}], "expected": 10},
            ],
            type_tests=c("""
                // @ts-expect-error: a triangle is not a Shape
                area({ kind: "triangle", base: 1, height: 2 });
            """),
            why=(
                'Inside `case "rect"`, TypeScript knows shape has width and height. In default '
                "every variant has been handled, so shape is `never`; add a variant without a "
                "case and that assignment stops compiling."
            ),
            source=Source(
                "TypeScript Handbook — Narrowing",
                TS_HANDBOOK + "narrowing.html",
                "The never type is assignable to every type; however, no type is assignable to "
                "never (except never itself). This means you can use narrowing and rely on never "
                "turning up to do exhaustive checking in a switch statement.",
            ),
        ),
        CompileCard(
            key="ts21-exhaustive",
            snippet=c("""
                type Shape =
                  | { kind: "circle"; radius: number }
                  | { kind: "square"; side: number }
                  | { kind: "triangle"; base: number; height: number };
                function area(shape: Shape): number {
                  switch (shape.kind) {
                    case "circle":
                      return Math.PI * shape.radius ** 2;
                    case "square":
                      return shape.side ** 2;
                    default: {
                      const unreachable: never = shape;
                      throw new Error(`unknown shape: ${JSON.stringify(unreachable)}`);
                    }
                  }
                }
            """),
            answer=(
                "No. `const unreachable: never = shape` fails: the triangle type is not "
                "assignable to type 'never' — there is no case for \"triangle\"."
            ),
            error_lines=[12],
            why=(
                "After the circle and square cases, the only thing shape can still be is a "
                "triangle, so it isn't never. Add the missing case and it compiles."
            ),
            source=Source("TypeScript Handbook — Narrowing", TS_HANDBOOK + "narrowing.html"),
        ),
        CodeCard(
            key="ts21-counter-actions",
            language=TS,
            kind="types",
            title="Type the counter's actions",
            task=(
                '`Action` is too loose: the compiler accepts `{ type: "add" }` with no amount, '
                "and actions that don't exist. Replace it with a discriminated union of the "
                "three real actions."
            ),
            starter=c("""
                type Action = { type: string; amount?: number };

                function counter(state: number, action: Action): number {
                  switch (action.type) {
                    case "increment":
                      return state + 1;
                    case "add":
                      return state + (action.amount ?? 0);
                    case "reset":
                      return 0;
                    default:
                      return state;
                  }
                }
            """),
            solution=c("""
                type Action =
                  | { type: "increment" }
                  | { type: "add"; amount: number }
                  | { type: "reset" };

                function counter(state: number, action: Action): number {
                  switch (action.type) {
                    case "increment":
                      return state + 1;
                    case "add":
                      return state + action.amount;
                    case "reset":
                      return 0;
                  }
                }
            """),
            tests=[
                {"input": [0, {"type": "increment"}], "expected": 1},
                {"input": [5, {"type": "add", "amount": 10}], "expected": 15},
                {"input": [7, {"type": "reset"}], "expected": 0},
            ],
            type_tests=c("""
                counter(0, { type: "add", amount: 2 });
                // @ts-expect-error: "add" needs an amount
                counter(0, { type: "add" });
                // @ts-expect-error: there is no "jump" action
                counter(0, { type: "jump" });
            """),
            wrong=[
                c("""
                    type Action = { type: "increment" | "add" | "reset"; amount?: number };

                    function counter(state: number, action: Action): number {
                      switch (action.type) {
                        case "increment":
                          return state + 1;
                        case "add":
                          return state + (action.amount ?? 0);
                        case "reset":
                          return 0;
                      }
                    }
                """),
            ],
            why=(
                'With one object type per action, "add" must carry an amount and unknown types '
                "are rejected where the action is created — and the switch needs no default."
            ),
            source=Source(
                "TypeScript Handbook — Narrowing",
                TS_HANDBOOK + "narrowing.html",
                "Discriminated unions are useful for more than just talking about circles and squares.",
            ),
            difficulty="Medium",
        ),
    ],
)

# ── 22 ────────────────────────────────────────────────────────────────────

GENERICS = Subdeck(
    name="22 · Generics, Constraints & keyof",
    summary=(
        "A type parameter (`<T>`) links the types going in to the types coming out, instead "
        "of losing them to `any`. `T extends Something` requires a minimum shape. `keyof T` is "
        "the union of T's keys, and `T[K]` the type stored under key K."
    ),
    sources=[
        Source("TypeScript Handbook — Generics", TS_HANDBOOK + "generics.html"),
        Source("TypeScript Handbook — Keyof Type Operator", TS_HANDBOOK + "keyof-types.html"),
    ],
    cards=[
        CodeCard(
            key="ts22-first-element",
            language=TS,
            kind="types",
            title="firstElement<T>(arr)",
            task=(
                "Write the generic `firstElement<T>(arr: T[]): T | undefined`: the first item, or "
                "`undefined` for an empty array. Callers must keep the item type and be told it "
                "might be missing."
            ),
            starter=c("""
                function firstElement(arr: any[]): any {
                  return undefined;
                }
            """),
            solution=c("""
                function firstElement<T>(arr: T[]): T | undefined {
                  return arr[0];
                }
            """),
            tests=[
                {"input": [["alpha", "beta"]], "expected": "alpha"},
                {"input": [[42, 99]], "expected": 42},
                {"input": [[]], "expected": {"$undefined": True}},
            ],
            type_tests=c("""
                const s: string | undefined = firstElement(["a", "b"]);
                const n: number | undefined = firstElement([1, 2]);
                // @ts-expect-error: the result may be undefined
                const definitely: number = firstElement([1]);
            """),
            wrong=[
                c("""
                    function firstElement(arr: any[]): any {
                      return arr[0];
                    }
                """),
                c("""
                    function firstElement<T>(arr: T[]): T {
                      return arr[0];
                    }
                """),
                c("""
                    function firstElement<T>(arr: T[]): T | null {
                      return arr.length > 0 ? arr[0] : null;
                    }
                """),
            ],
            why=(
                "T is filled in from the argument (string[] gives T = string). The `| undefined` "
                "is honest about empty arrays: arr[0] has type T, but at run time it can be undefined."
            ),
            source=Source("TypeScript Handbook — Generics", TS_HANDBOOK + "generics.html"),
        ),
        CodeCard(
            key="ts22-longest",
            language=TS,
            kind="types",
            title="longest<T>(a, b)",
            task=(
                "Write `longest(a, b)`: return whichever argument is longer (the first on a tie). "
                "It must accept anything with a numeric `length` — strings, arrays — keep the "
                "argument type, and reject numbers."
            ),
            starter=c("""
                function longest(a: any, b: any): any {
                  return a.length > b.length ? a : b;
                }
            """),
            solution=c("""
                function longest<T extends { length: number }>(a: T, b: T): T {
                  return b.length > a.length ? b : a;
                }
            """),
            tests=[
                {"input": ["alice", "bob"], "expected": "alice"},
                {"input": [[1, 2], [1, 2, 3]], "expected": [1, 2, 3]},
                {"input": ["ab", "cd"], "expected": "ab"},
            ],
            type_tests=c("""
                const s: string = longest("a", "bb");
                const arr: number[] = longest([1], [2, 3]);
                // @ts-expect-error: numbers have no length
                longest(10, 100);
            """),
            wrong=[
                c("""
                    function longest<T>(a: T, b: T): T {
                      return (b as any).length > (a as any).length ? b : a;
                    }
                """),
            ],
            why=(
                "`T extends { length: number }` lets the body use .length and makes the compiler "
                "reject arguments without it, while T still remembers the exact type passed in."
            ),
            source=Source(
                "TypeScript Handbook — Generics",
                TS_HANDBOOK + "generics.html",
                "Instead of working with any and all types, we'd like to constrain this function "
                "to work with any and all types that also have the .length property.",
            ),
        ),
        CodeCard(
            key="ts22-get-property",
            language=TS,
            kind="types",
            title="getProperty(obj, key)",
            task=(
                "Write `getProperty(obj, key)` so the key must be one of `obj`'s keys and the "
                "result has that property's type."
            ),
            starter=c("""
                function getProperty(obj: any, key: string): any {
                  return obj[key];
                }
            """),
            solution=c("""
                function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
                  return obj[key];
                }
            """),
            tests=[
                {"input": [{"id": 1, "name": "Ada"}, "name"], "expected": "Ada"},
                {"input": [{"id": 1}, "id"], "expected": 1},
            ],
            type_tests=c("""
                const userName: string = getProperty({ id: 1, name: "Ada" }, "name");
                const id: number = getProperty({ id: 1, name: "Ada" }, "id");
                // @ts-expect-error: "age" is not a key
                getProperty({ id: 1, name: "Ada" }, "age");
            """),
            why=(
                'keyof T is the union of T\'s keys ("id" | "name"); K extends it, so only real '
                "keys are allowed, and T[K] is the type stored under that key."
            ),
            source=Source(
                "TypeScript Handbook — Keyof Type Operator",
                TS_HANDBOOK + "keyof-types.html",
                "The keyof operator takes an object type and produces a string or numeric literal "
                "union of its keys.",
            ),
        ),
        CodeCard(
            key="ts22-pluck",
            language=TS,
            kind="types",
            title="pluck(items, key)",
            task=(
                "Write `pluck(items, key)`: the value of `key` from every item, as an array. Type "
                "it so the key must exist on the items and the result has the right element type."
            ),
            starter=c("""
                function pluck(items: any[], key: string): any[] {
                  return [];
                }
            """),
            solution=c("""
                function pluck<T, K extends keyof T>(items: T[], key: K): T[K][] {
                  return items.map((item) => item[key]);
                }
            """),
            tests=[
                {
                    "input": [[{"id": 1, "name": "Ada"}, {"id": 2, "name": "Grace"}], "name"],
                    "expected": ["Ada", "Grace"],
                },
                {"input": [[], "name"], "expected": []},
                {"input": [[{"v": 1}], "v"], "expected": [1]},
                {"input": [[{"v": 1}, {"v": 2}, {"v": 3}], "v"], "expected": [1, 2, 3]},
            ],
            type_tests=c("""
                const names: string[] = pluck([{ id: 1, name: "Ada" }], "name");
                const ids: number[] = pluck([{ id: 1, name: "Ada" }], "id");
                // @ts-expect-error: "age" is not a key of the items
                pluck([{ id: 1, name: "Ada" }], "age");
            """),
            wrong=[
                c("""
                    function pluck(items: any[], key: string): any[] {
                      return items.map((item) => item[key]);
                    }
                """),
                c("""
                    function pluck<T, K extends keyof T>(items: T[], key: K): T[K][] {
                      return [items[0][key], items[1][key]];
                    }
                """),
            ],
            why='The same keyof pattern as getProperty, applied to every item: T[K][] is "an array of whatever is under K".',
            difficulty="Medium",
        ),
    ],
)

# ── 23 ────────────────────────────────────────────────────────────────────

UTILITIES = Subdeck(
    name="23 · Utility Types",
    summary=(
        "Built-in generic types derive new types from old ones: `Partial<T>` (all optional), "
        "`Readonly<T>` (no reassignment, one level deep, compile time only), `Pick<T, K>` and "
        "`Omit<T, K>` (keep or drop keys), `Record<K, V>` (an object with exactly those keys)."
    ),
    sources=[Source("TypeScript Handbook — Utility Types", UTILITY)],
    cards=[
        CodeCard(
            key="ts23-update-todo",
            language=TS,
            kind="types",
            title="updateTodo(todo, changes)",
            task=(
                "Write `updateTodo(todo, changes)`: return a new todo with `changes` applied. "
                "`changes` may contain any subset of a todo's fields — and nothing else."
            ),
            starter=c("""
                interface Todo {
                  title: string;
                  done: boolean;
                  priority: number;
                }

                function updateTodo(todo: Todo, changes: Todo): Todo {
                  return todo;
                }
            """),
            solution=c("""
                interface Todo {
                  title: string;
                  done: boolean;
                  priority: number;
                }

                function updateTodo(todo: Todo, changes: Partial<Todo>): Todo {
                  return { ...todo, ...changes };
                }
            """),
            tests=[
                {
                    "input": [{"title": "Write", "done": False, "priority": 1}, {"done": True}],
                    "expected": {"title": "Write", "done": True, "priority": 1},
                },
                {
                    "input": [{"title": "Write", "done": False, "priority": 1}, {}],
                    "expected": {"title": "Write", "done": False, "priority": 1},
                },
                {
                    "input": [
                        {"title": "Write", "done": False, "priority": 1},
                        {"priority": 3, "title": "Edit"},
                    ],
                    "expected": {"title": "Edit", "done": False, "priority": 3},
                },
            ],
            type_tests=c("""
                const base: Todo = { title: "Write", done: false, priority: 1 };
                updateTodo(base, { done: true });
                updateTodo(base, {});
                // @ts-expect-error: there is no "color" field
                updateTodo(base, { color: "red" });
                // @ts-expect-error: done is a boolean
                updateTodo(base, { done: "yes" });
            """),
            wrong=[
                c("""
                    interface Todo {
                      title: string;
                      done: boolean;
                      priority: number;
                    }

                    function updateTodo(todo: Todo, changes: any): Todo {
                      return { ...todo, ...changes };
                    }
                """),
                c("""
                    interface Todo {
                      title: string;
                      done: boolean;
                      priority: number;
                    }

                    function updateTodo(todo: Todo, changes: Partial<Todo>): Todo {
                      return { ...changes, ...todo };
                    }
                """),
            ],
            why="Partial<Todo> is Todo with every property optional, which is exactly what a patch is.",
            source=Source(
                "TypeScript Handbook — Utility Types",
                UTILITY,
                "Constructs a type with all properties of Type set to optional. This utility will "
                "return a type that represents all subsets of a given type.",
            ),
        ),
        CodeCard(
            key="ts23-public-user",
            language=TS,
            kind="types",
            title="toPublicUser(user)",
            task=(
                "Write `toPublicUser(user)`: return the user without `passwordHash`, typed with "
                "`Omit` so the compiler also knows the hash is gone."
            ),
            starter=c("""
                interface User {
                  id: number;
                  name: string;
                  passwordHash: string;
                }

                function toPublicUser(user: User): User {
                  return user;
                }
            """),
            solution=c("""
                interface User {
                  id: number;
                  name: string;
                  passwordHash: string;
                }

                function toPublicUser(user: User): Omit<User, "passwordHash"> {
                  const { passwordHash, ...rest } = user;
                  return rest;
                }
            """),
            tests=[
                {
                    "input": [{"id": 1, "name": "Ada", "passwordHash": "x1"}],
                    "expected": {"id": 1, "name": "Ada"},
                },
            ],
            type_tests=c("""
                const pub = toPublicUser({ id: 1, name: "Ada", passwordHash: "x" });
                const n: string = pub.name;
                // @ts-expect-error: the hash is not part of the public type
                pub.passwordHash;
            """),
            wrong=[
                c("""
                    interface User {
                      id: number;
                      name: string;
                      passwordHash: string;
                    }

                    function toPublicUser(user: User): User {
                      const { passwordHash, ...rest } = user;
                      return rest as User;
                    }
                """),
            ],
            why=(
                "Removing the property at run time (rest destructuring) and in the type (Omit) "
                "go together: either one alone leaves a gap."
            ),
            source=Source("TypeScript Handbook — Utility Types", UTILITY),
        ),
        CodeCard(
            key="ts23-count-by-role",
            language=TS,
            kind="types",
            title="countByRole(roles)",
            task=(
                "Write `countByRole(roles)`: how many times each role appears, with every role "
                "present (0 if absent). Type the result as `Record<Role, number>`."
            ),
            starter=c("""
                type Role = "admin" | "editor" | "viewer";

                function countByRole(roles: string[]): Record<string, number> {
                  const counts: Record<string, number> = {};
                  for (const role of roles) counts[role] = (counts[role] ?? 0) + 1;
                  return counts;
                }
            """),
            solution=c("""
                type Role = "admin" | "editor" | "viewer";

                function countByRole(roles: Role[]): Record<Role, number> {
                  const counts: Record<Role, number> = { admin: 0, editor: 0, viewer: 0 };
                  for (const role of roles) counts[role]++;
                  return counts;
                }
            """),
            tests=[
                {
                    "input": [["admin", "viewer", "viewer"]],
                    "expected": {"admin": 1, "editor": 0, "viewer": 2},
                },
                {"input": [[]], "expected": {"admin": 0, "editor": 0, "viewer": 0}},
            ],
            type_tests=c("""
                const counts: Record<Role, number> = countByRole(["admin"]);
                // @ts-expect-error: "owner" is not a Role
                countByRole(["owner"]);
            """),
            why=(
                "Record<Role, number> requires every key of Role, so the compiler makes you "
                "start each count at 0 — and rejects roles that don't exist."
            ),
            source=Source("TypeScript Handbook — Utility Types", UTILITY),
        ),
        CompileCard(
            key="ts23-readonly-shallow",
            snippet=c("""
                interface Team {
                  name: string;
                  members: string[];
                }
                const team: Readonly<Team> = { name: "Core", members: ["Ada"] };
                team.members.push("Grace");
                team.name = "Platform";
            """),
            answer=(
                'No. `team.name = "Platform"` fails: name is a read-only property. '
                "`team.members.push(...)` compiles."
            ),
            error_lines=[7],
            why=(
                "Readonly only stops reassigning the object's own properties. The array inside "
                "can still be changed, and nothing is enforced at run time."
            ),
            source=Source(
                "TypeScript Handbook — Object Types",
                TS_HANDBOOK + "objects.html",
                "Using the readonly modifier doesn't necessarily imply that a value is totally "
                "immutable - or in other words, that its internal contents can't be changed. It "
                "just means the property itself can't be re-written to.",
            ),
        ),
    ],
)

# ── 24 ────────────────────────────────────────────────────────────────────

TS_CLASSES = Subdeck(
    name="24 · Classes in TypeScript",
    summary=(
        "TypeScript adds `public`, `private`, `protected` and `readonly` to classes, "
        "parameter properties (`constructor(private x: number)`) and `implements`. Its "
        "`private` is checked by the compiler only; JavaScript's `#field` is private at run time."
    ),
    sources=[Source("TypeScript Handbook — Classes", TS_HANDBOOK + "classes.html")],
    cards=[
        CodeCard(
            key="ts24-temperature",
            language=TS,
            title="class Temperature",
            task=(
                "Rewrite `Temperature` with a private, readonly parameter property `celsius`, a "
                '`fahrenheit` getter, and `describe()` returning e.g. `"100°C"`. Don\'t change `check`.'
            ),
            starter=c("""
                // Test driver: don't change.
                function check(celsius: number): [number, string] {
                  const t = new Temperature(celsius);
                  return [t.fahrenheit, t.describe()];
                }

                class Temperature {
                  celsius: number;
                  constructor(celsius: number) {
                    this.celsius = celsius;
                  }
                  // TODO
                }
            """),
            solution=c("""
                // Test driver: don't change.
                function check(celsius: number): [number, string] {
                  const t = new Temperature(celsius);
                  return [t.fahrenheit, t.describe()];
                }

                class Temperature {
                  constructor(private readonly celsius: number) {}

                  get fahrenheit(): number {
                    return (this.celsius * 9) / 5 + 32;
                  }

                  describe(): string {
                    return `${this.celsius}°C`;
                  }
                }
            """),
            tests=[
                {"input": [100], "expected": [212, "100°C"]},
                {"input": [0], "expected": [32, "0°C"]},
                {"input": [-40], "expected": [-40, "-40°C"]},
            ],
            type_tests=c("""
                const t = new Temperature(20);
                const f: number = t.fahrenheit;
                // @ts-expect-error: celsius is private
                t.celsius;
                // @ts-expect-error: fahrenheit has no setter
                t.fahrenheit = 0;
            """),
            wrong=[
                c("""
                    // Test driver: don't change.
                    function check(celsius: number): [number, string] {
                      const t = new Temperature(celsius);
                      return [t.fahrenheit, t.describe()];
                    }

                    class Temperature {
                      constructor(public celsius: number) {}

                      get fahrenheit(): number {
                        return (this.celsius * 9) / 5 + 32;
                      }

                      describe(): string {
                        return `${this.celsius}°C`;
                      }
                    }
                """),
            ],
            why=(
                "`constructor(private readonly celsius: number) {}` declares and assigns the "
                "field in one go. A getter with no setter is read-only to callers."
            ),
            source=Source(
                "TypeScript Handbook — Classes",
                TS_HANDBOOK + "classes.html",
                "TypeScript offers special syntax for turning a constructor parameter into a "
                "class property with the same name and value. These are called parameter "
                "properties and are created by prefixing a constructor argument with one of the "
                "visibility modifiers public, private, protected, or readonly.",
            ),
            difficulty="Medium",
        ),
        CompileCard(
            key="ts24-private-vs-hash",
            snippet=c("""
                class Account {
                  private pin = 1234;
                  #secret = "s3cret";
                }
                const account = new Account();
                console.log(account["pin"]);
                console.log(account.pin);
            """),
            answer=(
                "No. `account.pin` fails: Property 'pin' is private. `account[\"pin\"]` compiles."
            ),
            error_lines=[7],
            why=(
                "TypeScript's private is only checked by the compiler, and bracket access is "
                "allowed as an escape hatch. At run time pin is an ordinary property. A #field "
                "can't be reached from outside at all."
            ),
            source=Source(
                "TypeScript Handbook — Classes",
                TS_HANDBOOK + "classes.html",
                "This makes private-declared fields potentially easier to access for things like "
                "unit tests, with the drawback that these fields are soft private and don't "
                "strictly enforce privacy.",
            ),
        ),
        CodeCard(
            key="ts24-implements",
            language=TS,
            title="class MemoryLogger implements Logger",
            task=(
                "Write `MemoryLogger` so it `implements Logger`: `log` stores messages in a "
                "private array and `history()` returns a copy, so callers can't change the "
                "stored log. Don't change `check` or `Logger`."
            ),
            starter=c("""
                // Test driver: don't change.
                function check(messages: string[]): string[] {
                  const logger: Logger = new MemoryLogger();
                  messages.forEach((m) => logger.log(m));
                  logger.history().push("tampered");
                  return logger.history();
                }

                interface Logger {
                  log(message: string): void;
                  history(): string[];
                }

                class MemoryLogger {
                  // TODO
                }
            """),
            solution=c("""
                // Test driver: don't change.
                function check(messages: string[]): string[] {
                  const logger: Logger = new MemoryLogger();
                  messages.forEach((m) => logger.log(m));
                  logger.history().push("tampered");
                  return logger.history();
                }

                interface Logger {
                  log(message: string): void;
                  history(): string[];
                }

                class MemoryLogger implements Logger {
                  private messages: string[] = [];

                  log(message: string): void {
                    this.messages.push(message);
                  }

                  history(): string[] {
                    return [...this.messages];
                  }
                }
            """),
            tests=[
                {"input": [["a", "b"]], "expected": ["a", "b"]},
                {"input": [[]], "expected": []},
            ],
            wrong=[
                c("""
                    // Test driver: don't change.
                    function check(messages: string[]): string[] {
                      const logger: Logger = new MemoryLogger();
                      messages.forEach((m) => logger.log(m));
                      logger.history().push("tampered");
                      return logger.history();
                    }

                    interface Logger {
                      log(message: string): void;
                      history(): string[];
                    }

                    class MemoryLogger implements Logger {
                      private messages: string[] = [];

                      log(message: string): void {
                        this.messages.push(message);
                      }

                      history(): string[] {
                        return this.messages;
                      }
                    }
                """),
            ],
            why=(
                "`implements` makes the compiler check the class against the interface. Returning "
                "the private array itself would let any caller change it; return a copy."
            ),
            source=Source("TypeScript Handbook — Classes", TS_HANDBOOK + "classes.html"),
            difficulty="Medium",
        ),
    ],
)

# ── 25 ────────────────────────────────────────────────────────────────────

STRICTNESS = Subdeck(
    name="25 · Strict Checks & satisfies",
    summary=(
        "`strict` turns on `strictNullChecks`: null and undefined must be handled before "
        "use. `noUncheckedIndexedAccess` (not part of strict) adds `| undefined` to index "
        "lookups. `satisfies` checks a value against a type without widening the value's own type."
    ),
    sources=[
        Source(
            "TypeScript Handbook — Everyday Types: null and undefined",
            TS_HANDBOOK + "everyday-types.html",
        ),
        Source(
            "TSConfig reference — noUncheckedIndexedAccess",
            "https://www.typescriptlang.org/tsconfig/#noUncheckedIndexedAccess",
        ),
        Source("TypeScript 4.9 release notes — satisfies", TS49),
    ],
    cards=[
        CompileCard(
            key="ts25-strict-null",
            snippet=c("""
                function initial(name: string | null): string {
                  return name[0];
                }
                function initialSafe(name: string | null): string {
                  return name?.[0] ?? "?";
                }
            """),
            answer="No. `return name[0]` fails: 'name' is possibly 'null'. initialSafe compiles.",
            error_lines=[2],
            why=(
                "With strictNullChecks, string | null must be narrowed before use. ?. stops at "
                "null and ?? supplies the fallback, so every path returns a string."
            ),
            source=Source(
                "TypeScript Handbook — Everyday Types",
                TS_HANDBOOK + "everyday-types.html",
                "With strictNullChecks on, when a value is null or undefined, you will need to "
                "test for those values before using methods or properties on that value.",
            ),
        ),
        CompileCard(
            key="ts25-unchecked-index",
            options={"noUncheckedIndexedAccess": True},
            snippet=c("""
                const scores = [90, 85];
                const first = scores[0];
                console.log(first.toFixed(1));
                const safe = scores[0] ?? 0;
                console.log(safe.toFixed(1));
            """),
            answer=(
                "No. `first.toFixed(1)` fails: 'first' is possibly 'undefined'. The `safe` lines compile."
            ),
            error_lines=[3],
            why=(
                "With noUncheckedIndexedAccess, scores[0] is number | undefined, because an index "
                "may be past the end. Without the flag the same code compiles and would crash "
                "on an empty array."
            ),
            source=Source(
                "TSConfig reference — noUncheckedIndexedAccess",
                "https://www.typescriptlang.org/tsconfig/#noUncheckedIndexedAccess",
            ),
        ),
        CompileCard(
            key="ts25-satisfies",
            snippet=c("""
                type Color = string | [number, number, number];
                const annotated: Record<"red" | "green", Color> = { red: "#f00", green: [0, 255, 0] };
                const checked = { red: "#f00", green: [0, 255, 0] } satisfies Record<"red" | "green", Color>;
                annotated.red.toUpperCase();
                checked.red.toUpperCase();
            """),
            answer=(
                "No. `annotated.red.toUpperCase()` fails: toUpperCase does not exist on the tuple "
                "type. `checked.red.toUpperCase()` compiles."
            ),
            error_lines=[4],
            why=(
                "An annotation replaces the value's type, so annotated.red is just Color. "
                "satisfies checks the object against the type but keeps what it inferred: "
                "checked.red is a string."
            ),
            source=Source(
                "TypeScript 4.9 release notes",
                TS49,
                "The new satisfies operator lets us validate that the type of an expression "
                "matches some type, without changing the resulting type of that expression.",
            ),
        ),
    ],
)


PART3 = Part(
    name="Part 3 · Intermediate TypeScript",
    summary=(
        "Modelling data and writing reusable, type-safe code: discriminated unions, generics "
        "and keyof, utility types, TypeScript classes, and the stricter compiler checks."
    ),
    subdecks=[UNIONS, GENERICS, UTILITIES, TS_CLASSES, STRICTNESS],
)

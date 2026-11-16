"""Part 2: TypeScript core — types as a safety layer (TypeScript Handbook)."""

from __future__ import annotations

from .model import TS_DOCS, TS_HANDBOOK, CodeCard, CompileCard, Part, PredictCard, Source, Subdeck
from .part1 import c

TS = "typescript"
TS51 = TS_DOCS + "release-notes/typescript-5-1.html"

# ── 15 ────────────────────────────────────────────────────────────────────

COMPILER = Subdeck(
    name="15 · TypeScript & the Compiler",
    summary=(
        "TypeScript is JavaScript plus types. The compiler checks the types, then strips them: "
        "they never change what the program does, and by default `tsc` still writes the "
        "JavaScript when it finds errors. So data from outside (JSON, user input) has to be "
        "checked with real code. A few TypeScript features, like `enum`, do produce code."
    ),
    sources=[
        Source("TypeScript Handbook — The Basics", TS_HANDBOOK + "basic-types.html"),
        Source("TypeScript for the New Programmer", TS_DOCS + "typescript-from-scratch.html"),
    ],
    cards=[
        PredictCard(
            key="ts15-emits-anyway",
            language=TS,
            prompt=(
                "`tsc` reports a type error in this file but still writes the JavaScript (that is "
                "its default). What does running the output print?"
            ),
            snippet=c("""
                const count: number = "3" as any;
                const label: string = 42 as any;
                console.log(count + 1, label + 1);
            """),
            output="31 43",
            why=(
                "Types are erased before the code runs, so they cannot convert or check values. "
                'count is really the string "3" (so + concatenates) and label the number 42. '
                "Fix type errors; don't silence them with any."
            ),
            source=Source(
                "TypeScript Handbook — The Basics",
                TS_HANDBOOK + "basic-types.html",
                "Remember: Type annotations never change the runtime behavior of your program.",
            ),
        ),
        PredictCard(
            key="ts15-enum-emits",
            language=TS,
            snippet=c("""
                enum Direction {
                  Up,
                  Down,
                }
                console.log(Direction.Down, Direction[0], Object.keys(Direction).length);
            """),
            output="1 Up 4",
            why=(
                "enum is one of the few TypeScript features that is not erased: it compiles to a "
                "real object. A numeric enum also maps numbers back to names, so it has four keys: "
                '"0", "1", "Up" and "Down".'
            ),
            source=Source("TypeScript Handbook — Enums", TS_DOCS + "enums.html"),
            difficulty="Medium",
        ),
        CodeCard(
            key="ts15-parse-user",
            language=TS,
            kind="types",
            title="parseUser(data: unknown)",
            task=(
                "`data` came from `JSON.parse`, so its type is `unknown`. Return a `User` (only "
                "its `name` and `age`) when `data` is an object with a string `name` and a number "
                "`age`; otherwise return `null`. The `as User` in the starter checks nothing."
            ),
            starter=c("""
                type User = { name: string; age: number };

                function parseUser(data: unknown): User | null {
                  return data as User;
                }
            """),
            solution=c("""
                type User = { name: string; age: number };

                function parseUser(data: unknown): User | null {
                  if (typeof data !== "object" || data === null) return null;
                  if (!("name" in data) || typeof data.name !== "string") return null;
                  if (!("age" in data) || typeof data.age !== "number") return null;
                  return { name: data.name, age: data.age };
                }
            """),
            tests=[
                {"input": [{"name": "Ada", "age": 36}], "expected": {"name": "Ada", "age": 36}},
                {
                    "input": [{"name": "Ada", "age": 36, "admin": True}],
                    "expected": {"name": "Ada", "age": 36},
                },
                {"input": [{"name": "Ada"}], "expected": None},
                {"input": [{"name": "Ada", "age": "36"}], "expected": None},
                {"input": [None], "expected": None},
                {"input": ["Ada"], "expected": None},
            ],
            type_tests=c("""
                const parsed: { name: string; age: number } | null = parseUser(JSON.parse("{}"));
                parseUser(42);
            """),
            wrong=[
                c("""
                    type User = { name: string; age: number };

                    function parseUser(data: any): User | null {
                      return data?.name ? data : null;
                    }
                """),
                c("""
                    type User = { name: string; age: number };

                    function parseUser(data: User): User | null {
                      if (typeof data.name !== "string" || typeof data.age !== "number") return null;
                      return { name: data.name, age: data.age };
                    }
                """),
            ],
            why=(
                "A type annotation or `as` only tells the compiler what to assume. For data from "
                "outside, check it with typeof and `in`; TypeScript narrows `unknown` as you go."
            ),
            source=Source(
                "TypeScript Handbook — The Basics",
                TS_HANDBOOK + "basic-types.html",
                "Most TypeScript-specific code gets erased away, and likewise, here our type "
                "annotations were completely erased.",
            ),
            difficulty="Medium",
        ),
    ],
)

# ── 16 ────────────────────────────────────────────────────────────────────

ANNOTATIONS = Subdeck(
    name="16 · Annotations & Inference",
    summary=(
        "Annotate function parameters and the values TypeScript can't work out; let it infer "
        "the rest. With `strict` on, `noImplicitAny` rejects parameters with no type. A "
        "variable initialised with a value keeps that value's type."
    ),
    sources=[
        Source("TypeScript Handbook — The Basics", TS_HANDBOOK + "basic-types.html"),
        Source("TypeScript Handbook — Everyday Types", TS_HANDBOOK + "everyday-types.html"),
    ],
    cards=[
        CodeCard(
            key="ts16-total-price",
            language=TS,
            kind="types",
            title="Add types to totalPrice",
            task=(
                "This JavaScript doesn't compile under `strict`: its parameters are implicitly "
                "`any`. Add types — items are `{ price: number; quantity: number }` — so it "
                "compiles and rejects bad calls."
            ),
            starter=c("""
                function totalPrice(items, taxRate) {
                  const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
                  return Math.round(subtotal * (1 + taxRate) * 100) / 100;
                }
            """),
            solution=c("""
                type LineItem = { price: number; quantity: number };

                function totalPrice(items: LineItem[], taxRate: number): number {
                  const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
                  return Math.round(subtotal * (1 + taxRate) * 100) / 100;
                }
            """),
            tests=[
                {
                    "input": [[{"price": 10, "quantity": 2}, {"price": 5, "quantity": 1}], 0.1],
                    "expected": 27.5,
                },
                {"input": [[], 0.2], "expected": 0},
            ],
            type_tests=c("""
                const total: number = totalPrice([{ price: 1, quantity: 1 }], 0);
                // @ts-expect-error: the tax rate is a number, not a string
                totalPrice([], "0.1");
                // @ts-expect-error: every item needs a quantity
                totalPrice([{ price: 1 }], 0);
            """),
            wrong=[
                c("""
                    function totalPrice(items: any[], taxRate: any): number {
                      const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
                      return Math.round(subtotal * (1 + taxRate) * 100) / 100;
                    }
                """),
            ],
            why=(
                "Parameters are where types matter most: inside the function TypeScript infers "
                "the rest (`sum`, `item`, `subtotal`). Typing them `any` compiles but checks nothing."
            ),
            source=Source(
                "TypeScript Handbook — The Basics",
                TS_HANDBOOK + "basic-types.html",
                "Turning on the noImplicitAny flag will issue an error on any variables whose "
                "type is implicitly inferred as any.",
            ),
        ),
        CompileCard(
            key="ts16-inferred-type",
            snippet=c("""
                let count = 5;
                count = "five";
                let label;
                label = "five";
                label = 5;
            """),
            answer=(
                "No. `count = \"five\"` fails: Type 'string' is not assignable to type 'number'. "
                "The label lines compile."
            ),
            error_lines=[2],
            why=(
                "count was inferred as number from its initial value, and that type sticks. "
                "label had no initial value, so its type follows each assignment."
            ),
            source=Source(
                "TypeScript Handbook — The Basics",
                TS_HANDBOOK + "basic-types.html",
                'In many cases, TypeScript can even just infer (or "figure out") the types for '
                "us even if we omit them.",
            ),
            difficulty="Easy",
        ),
        CodeCard(
            key="ts16-format-price",
            language=TS,
            kind="fix",
            title="Fix formatPrice(cents)",
            task=(
                "This doesn't compile: the return type says `string` but the body returns a "
                'number. Return the price as dollars with two decimals, e.g. 1250 → `"$12.50"`.'
            ),
            starter=c("""
                function formatPrice(cents: number): string {
                  return cents / 100;
                }
            """),
            solution=c("""
                function formatPrice(cents: number): string {
                  return `$${(cents / 100).toFixed(2)}`;
                }
            """),
            tests=[
                {"input": [1250], "expected": "$12.50"},
                {"input": [5], "expected": "$0.05"},
                {"input": [0], "expected": "$0.00"},
            ],
            wrong=[
                c("""
                    function formatPrice(cents: number): string {
                      return "$" + cents / 100;
                    }
                """),
            ],
            why=(
                'A return type annotation turns "returns the wrong kind of value" into a compile '
                'error at the function, instead of a bug wherever it is used. toFixed(2) keeps "12.50".'
            ),
        ),
    ],
)

# ── 17 ────────────────────────────────────────────────────────────────────

OBJECT_TYPES = Subdeck(
    name="17 · Object Types & Interfaces",
    summary=(
        "An interface (or type alias) names the shape of an object; `?` marks optional "
        "properties and `readonly` stops reassignment. TypeScript compares shapes, not names. "
        "Object literals get an extra check: properties the target type doesn't have are errors."
    ),
    sources=[Source("TypeScript Handbook — Object Types", TS_HANDBOOK + "objects.html")],
    cards=[
        CodeCard(
            key="ts17-product",
            language=TS,
            kind="types",
            title="interface Product",
            task=(
                "Write an interface `Product` with `id` and `name` (strings), `price` (number) "
                "and an optional numeric `discount`, then type `finalPrice` with it."
            ),
            starter=c("""
                // TODO: interface Product { ... }

                function finalPrice(product) {
                  const discount = product.discount ?? 0;
                  return product.price * (1 - discount);
                }
            """),
            solution=c("""
                interface Product {
                  id: string;
                  name: string;
                  price: number;
                  discount?: number;
                }

                function finalPrice(product: Product): number {
                  const discount = product.discount ?? 0;
                  return product.price * (1 - discount);
                }
            """),
            tests=[
                {"input": [{"id": "a", "name": "Pen", "price": 10}], "expected": 10},
                {
                    "input": [{"id": "b", "name": "Pad", "price": 20, "discount": 0.25}],
                    "expected": 15,
                },
            ],
            type_tests=c("""
                finalPrice({ id: "a", name: "Pen", price: 10 });
                // @ts-expect-error: price is required
                finalPrice({ id: "a", name: "Pen" });
                // @ts-expect-error: discount is a number
                finalPrice({ id: "a", name: "Pen", price: 10, discount: "10%" });
            """),
            wrong=[
                c("""
                    interface Product {
                      id: string;
                      name: string;
                      price: number;
                      discount?: any;
                    }

                    function finalPrice(product: Product): number {
                      const discount = product.discount ?? 0;
                      return product.price * (1 - discount);
                    }
                """),
            ],
            why=(
                "`discount?: number` means the property may be missing, so its type inside the "
                "function is number | undefined — which is why `?? 0` is needed."
            ),
        ),
        CompileCard(
            key="ts17-excess-property",
            snippet=c("""
                interface Point {
                  x: number;
                  y: number;
                }
                function draw(p: Point): void {}
                draw({ x: 1, y: 2, color: "red" });
                const p = { x: 1, y: 2, color: "red" };
                draw(p);
            """),
            answer=(
                "No. `draw({ x: 1, y: 2, color: \"red\" })` fails: 'color' does not exist in type "
                "'Point'. Passing the variable p compiles."
            ),
            error_lines=[6],
            why=(
                "An object literal written straight into a call gets an excess property check, "
                "since an unknown property there is probably a typo. A variable is just checked "
                "for having x and y."
            ),
            source=Source(
                "TypeScript Handbook — Object Types",
                TS_HANDBOOK + "objects.html",
                "Object literals get special treatment and undergo excess property checking when "
                "assigning them to other variables, or passing them as arguments.",
            ),
        ),
        CodeCard(
            key="ts17-readonly-sort",
            language=TS,
            kind="fix",
            title="Fix sortedCopy(nums)",
            task=(
                "`sortedCopy` must not change its input, so its parameter is `readonly number[]` "
                "— and now it doesn't compile, because `sort` sorts in place. Fix it."
            ),
            starter=c("""
                function sortedCopy(nums: readonly number[]): number[] {
                  return nums.sort((a, b) => a - b);
                }
            """),
            solution=c("""
                function sortedCopy(nums: readonly number[]): number[] {
                  return [...nums].sort((a, b) => a - b);
                }
            """),
            tests=[
                {"input": [[3, 1, 2]], "expected": [1, 2, 3]},
                {"input": [[10, 9, 100]], "expected": [9, 10, 100]},
                {"input": [[]], "expected": []},
            ],
            type_tests=c("""
                const frozen: readonly number[] = [2, 1];
                const out: number[] = sortedCopy(frozen);
            """),
            wrong=[
                c("""
                    function sortedCopy(nums: number[]): number[] {
                      return nums.sort((a, b) => a - b);
                    }
                """),
            ],
            why=(
                "A readonly array type has no mutating methods (push, sort, splice…), so the "
                "compiler catches the accidental mutation. Copy first, or use toSorted()."
            ),
        ),
        CompileCard(
            key="ts17-structural",
            snippet=c("""
                interface Named {
                  name: string;
                }
                class Dog {
                  constructor(public name: string, public breed: string) {}
                }
                const pet: Named = new Dog("Rex", "lab");
                const thing: Named = { title: "Rex" };
            """),
            answer=(
                "No. `const thing: Named = { title: \"Rex\" }` fails ('title' does not exist in "
                "type 'Named'). The Dog line compiles."
            ),
            error_lines=[8],
            why=(
                "TypeScript compares shapes, not class names: a Dog has a string name, so it is a "
                "Named. The literal has no name (and an unknown title)."
            ),
            source=Source(
                "TypeScript for JavaScript Programmers", TS_DOCS + "typescript-in-5-minutes.html"
            ),
        ),
    ],
)

# ── 18 ────────────────────────────────────────────────────────────────────

NARROWING = Subdeck(
    name="18 · Unions & Narrowing",
    summary=(
        "A union `A | B` allows either type; until you narrow it you can only use what both "
        "share. `typeof`, `Array.isArray`, `in`, `instanceof`, equality and truthiness checks "
        "narrow it. A type predicate (`value is string`) turns your own function into a check "
        "the compiler understands — and trusts without verifying."
    ),
    sources=[
        Source("TypeScript Handbook — Narrowing", TS_HANDBOOK + "narrowing.html"),
        Source(
            "TypeScript Handbook — Everyday Types: Union Types", TS_HANDBOOK + "everyday-types.html"
        ),
    ],
    cards=[
        CodeCard(
            key="ts18-format-id",
            language=TS,
            kind="fix",
            title="Fix formatId(id)",
            task=(
                "This doesn't compile: `toUpperCase` doesn't exist on numbers. Narrow the union: "
                'numbers become 6 digits with leading zeros (`42` → `"000042"`), strings are '
                "upper-cased."
            ),
            starter=c("""
                function formatId(id: number | string): string {
                  return id.toUpperCase();
                }
            """),
            solution=c("""
                function formatId(id: number | string): string {
                  if (typeof id === "number") return String(id).padStart(6, "0");
                  return id.toUpperCase();
                }
            """),
            tests=[
                {"input": [42], "expected": "000042"},
                {"input": [123456], "expected": "123456"},
                {"input": ["ab12"], "expected": "AB12"},
            ],
            type_tests=c("""
                // @ts-expect-error: only numbers and strings are ids
                formatId(true);
            """),
            wrong=[
                c("""
                    function formatId(id: any): string {
                      if (typeof id === "number") return String(id).padStart(6, "0");
                      return id.toUpperCase();
                    }
                """),
            ],
            why='After `typeof id === "number"` returns, TypeScript knows id is a string on the next line.',
            source=Source(
                "TypeScript Handbook — Everyday Types",
                TS_HANDBOOK + "everyday-types.html",
                "Narrowing occurs when TypeScript can deduce a more specific type for a value "
                "based on the structure of the code.",
            ),
        ),
        CodeCard(
            key="ts18-describe-input",
            language=TS,
            title="describeInput(value)",
            task=(
                'Write `describeInput(value: string | string[] | null): string` — `"nothing"` '
                'for null, `"text: <value>"` for a string, `"list of <n>"` for an array.'
            ),
            starter=c("""
                function describeInput(value: string | string[] | null): string {
                  return "text: " + value;
                }
            """),
            solution=c("""
                function describeInput(value: string | string[] | null): string {
                  if (value === null) return "nothing";
                  if (Array.isArray(value)) return `list of ${value.length}`;
                  return `text: ${value}`;
                }
            """),
            tests=[
                {"input": ["hi"], "expected": "text: hi"},
                {"input": [""], "expected": "text: "},
                {"input": [["a", "b"]], "expected": "list of 2"},
                {"input": [[]], "expected": "list of 0"},
                {"input": [None], "expected": "nothing"},
            ],
            type_tests=c("""
                // @ts-expect-error: numbers aren't allowed
                describeInput(5);
            """),
            wrong=[
                c("""
                    function describeInput(value: string | string[] | null): string {
                      if (!value) return "nothing";
                      if (Array.isArray(value)) return `list of ${value.length}`;
                      return `text: ${value}`;
                    }
                """),
            ],
            why="Check null and arrays first; whatever is left must be a string. An empty string is not null.",
        ),
        CodeCard(
            key="ts18-is-string",
            language=TS,
            kind="types",
            title="Type guard isString",
            task=(
                '`isString` works at run time, but `["a", 1].filter(isString)` still has the type '
                "`(string | number)[]`. Change its return type to a type predicate so the filter "
                "result is `string[]`."
            ),
            starter=c("""
                function isString(value: unknown): boolean {
                  return typeof value === "string";
                }
            """),
            solution=c("""
                function isString(value: unknown): value is string {
                  return typeof value === "string";
                }
            """),
            tests=[
                {"input": ["a"], "expected": True},
                {"input": [""], "expected": True},
                {"input": [1], "expected": False},
                {"input": [None], "expected": False},
            ],
            type_tests=c("""
                const words: string[] = ["a", 1, "b"].filter(isString);
            """),
            why=(
                '`value is string` tells TypeScript that true means "value is a string", and '
                "filter uses that to narrow its result. The compiler does not check that your "
                "body really tests for a string: a wrong guard lies to it."
            ),
            source=Source(
                "TypeScript Handbook — Narrowing",
                TS_HANDBOOK + "narrowing.html",
                "To define a user-defined type guard, we simply need to define a function whose "
                "return type is a type predicate:",
            ),
            difficulty="Medium",
        ),
        CompileCard(
            key="ts18-union-access",
            snippet=c("""
                function shout(value: string | number) {
                  return value.toUpperCase();
                }
                function size(value: string | string[]) {
                  return value.length;
                }
            """),
            answer=(
                "No. `value.toUpperCase()` fails: it does not exist on type 'number'. "
                "`value.length` compiles."
            ),
            error_lines=[2],
            why=(
                "Without narrowing you may only use what every member of the union has. Both "
                "strings and arrays have length; numbers have no toUpperCase."
            ),
            source=Source(
                "TypeScript Handbook — Everyday Types",
                TS_HANDBOOK + "everyday-types.html",
                "If every member in a union has a property in common, you can use that property "
                "without narrowing:",
            ),
        ),
    ],
)

# ── 19 ────────────────────────────────────────────────────────────────────

FUNCTION_TYPES = Subdeck(
    name="19 · Function Types: Optional, Default & Overloads",
    summary=(
        "`param?: T` may be left out (its type is T | undefined); `param = value` has a "
        "default and an inferred type. Overload signatures give one function several typed "
        "call shapes. A function typed `: undefined` needs no return statement (TypeScript 5.1+)."
    ),
    sources=[
        Source("TypeScript Handbook — More on Functions", TS_HANDBOOK + "functions.html"),
        Source("TypeScript 5.1 release notes", TS51),
    ],
    cards=[
        CodeCard(
            key="ts19-greet",
            language=TS,
            title="greet(name, greeting?, punctuation?)",
            task=(
                'Write `greet`: `greeting` defaults to `"Hello"` and `punctuation` is optional '
                '(`"!"` when missing). `greet("Ada")` → `"Hello, Ada!"`.'
            ),
            starter=c("""
                function greet(name: string, greeting: string, punctuation: string): string {
                  return `${greeting}, ${name}${punctuation}`;
                }
            """),
            solution=c("""
                function greet(name: string, greeting = "Hello", punctuation?: string): string {
                  return `${greeting}, ${name}${punctuation ?? "!"}`;
                }
            """),
            tests=[
                {"input": ["Ada"], "expected": "Hello, Ada!"},
                {"input": ["Ada", "Hi"], "expected": "Hi, Ada!"},
                {"input": ["Ada", "Hi", "."], "expected": "Hi, Ada."},
                {"input": ["Ada", "Hi", ""], "expected": "Hi, Ada"},
                {"input": ["Ada", {"$undefined": True}, "?"], "expected": "Hello, Ada?"},
            ],
            type_tests=c("""
                greet("Ada");
                greet("Ada", "Hi");
                // @ts-expect-error: name is required
                greet();
                // @ts-expect-error: greeting is a string
                greet("Ada", 5);
            """),
            wrong=[
                c("""
                    function greet(name: string, greeting: any = "Hello", punctuation?: string): string {
                      return `${greeting}, ${name}${punctuation ?? "!"}`;
                    }
                """),
            ],
            why=(
                "A default value also gives the parameter its type (string) and makes it "
                "optional; passing undefined uses the default."
            ),
            source=Source(
                "TypeScript Handbook — More on Functions", TS_HANDBOOK + "functions.html"
            ),
        ),
        CompileCard(
            key="ts19-undefined-return",
            snippet=c("""
                function logValue(value: string): undefined {
                  console.log(value);
                }
                function getValue(): string {
                  console.log("no return");
                }
            """),
            answer=(
                "No. getValue fails: a function whose declared type is neither undefined, void "
                "nor any must return a value. logValue compiles (TypeScript 5.1+)."
            ),
            error_lines=[4],
            why=(
                "Since TypeScript 5.1, a function that returns undefined needs no return "
                "statement, just like JavaScript. A function promising a string must return one."
            ),
            source=Source(
                "TypeScript 5.1 release notes",
                TS51,
                "In JavaScript, if a function finishes running without hitting a return, it "
                "returns the value undefined.",
            ),
        ),
        CodeCard(
            key="ts19-overloads",
            language=TS,
            kind="types",
            title="Overloads for parse(value)",
            task=(
                "`parse` turns a string into a number and a number into a 2-decimal string, but "
                "callers always get `string | number`. Add overload signatures so "
                '`parse("42")` is a number and `parse(3)` a string.'
            ),
            starter=c("""
                function parse(value: string | number): string | number {
                  return typeof value === "string" ? Number(value) : value.toFixed(2);
                }
            """),
            solution=c("""
                function parse(value: string): number;
                function parse(value: number): string;
                function parse(value: string | number): string | number {
                  return typeof value === "string" ? Number(value) : value.toFixed(2);
                }
            """),
            tests=[
                {"input": ["42"], "expected": 42},
                {"input": [3.14159], "expected": "3.14"},
            ],
            type_tests=c("""
                const n: number = parse("42");
                const s: string = parse(3);
            """),
            why=(
                "Callers see only the overload signatures; the last signature is the "
                "implementation's and must be compatible with all of them."
            ),
            source=Source(
                "TypeScript Handbook — More on Functions",
                TS_HANDBOOK + "functions.html",
                "In TypeScript, we can specify a function that can be called in different ways "
                "by writing overload signatures.",
            ),
            difficulty="Medium",
        ),
    ],
)

# ── 20 ────────────────────────────────────────────────────────────────────

TOP_TYPES = Subdeck(
    name="20 · any vs unknown",
    summary=(
        "`any` switches type checking off. `unknown` also accepts any value, but you must "
        "narrow it before using it — the safe choice for data you haven't checked yet."
    ),
    sources=[
        Source(
            "TypeScript Handbook — More on Functions: unknown",
            TS_HANDBOOK + "functions.html#unknown",
        )
    ],
    cards=[
        CompileCard(
            key="ts20-any-vs-unknown",
            snippet=c("""
                const a: any = "hello";
                a.launch();
                const u: unknown = "hello";
                u.launch();
                if (typeof u === "string") {
                  console.log(u.toUpperCase());
                }
            """),
            answer=(
                "No. `u.launch()` fails: 'u' is of type 'unknown'. `a.launch()` compiles (and "
                "would crash at run time); inside the typeof check, u is a string."
            ),
            error_lines=[4],
            why="any turns checking off; unknown keeps it on and asks you to prove the type first.",
            source=Source(
                "TypeScript Handbook — More on Functions",
                TS_HANDBOOK + "functions.html#unknown",
                "This is similar to the any type, but is safer because it's not legal to do "
                "anything with an unknown value:",
            ),
        ),
        CodeCard(
            key="ts20-length-of",
            language=TS,
            kind="fix",
            title="Fix lengthOf(value: unknown)",
            task=(
                "This doesn't compile: `value` is `unknown`. Return the length of a string or "
                "array, and 0 for anything else — including objects that happen to have a "
                "`length` property."
            ),
            starter=c("""
                function lengthOf(value: unknown): number {
                  return value.length;
                }
            """),
            solution=c("""
                function lengthOf(value: unknown): number {
                  if (typeof value === "string" || Array.isArray(value)) return value.length;
                  return 0;
                }
            """),
            tests=[
                {"input": ["abc"], "expected": 3},
                {"input": [[1, 2]], "expected": 2},
                {"input": [42], "expected": 0},
                {"input": [None], "expected": 0},
                {"input": [{"length": 5}], "expected": 0},
            ],
            wrong=[
                c("""
                    function lengthOf(value: any): number {
                      return value?.length ?? 0;
                    }
                """),
            ],
            why="Narrow unknown with real checks. Switching to any compiles, but then anything with a length gets through.",
        ),
    ],
)


PART2 = Part(
    name="Part 2 · TypeScript Core",
    summary=(
        "Types as a safety layer: what the compiler does and doesn't do, annotations and "
        "inference, object types, unions and narrowing, function types, and any vs unknown. "
        "Every code answer here is type-checked."
    ),
    subdecks=[COMPILER, ANNOTATIONS, OBJECT_TYPES, NARROWING, FUNCTION_TYPES, TOP_TYPES],
)

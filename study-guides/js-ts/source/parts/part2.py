"""Part 2 · TypeScript Core — guide configuration."""

from common import COMMON_DEVIATIONS, TODAY, c, note

FILENAME = "part2-typescript-core"
TITLE = "Part 2 · TypeScript Core"
SUBTITLE = "A Socratic study guide to the 19 cards of Part 2 of “JavaScript & TypeScript: Zero to Mastery”"
META_QUESTION = "How do TypeScript's types make JavaScript safer, and where do they stop protecting you?"
META_DECOMPOSITION = (
    "Part A asks what TypeScript is and what its types do and do not do at run time; B, how you write "
    "types for values, objects and unions; C, how you type functions and values of unknown type. Every "
    "section heading is a question, answered in its first sentence; every code sample was run, and every "
    "claim about the compiler was checked with \\code{tsc}. The Card-by-Card Solution Guide then works "
    "every card in the deck."
)

GROUPS = [
    ("A. What do types do, and what don't they?", "The compiler, type erasure and run-time data.", ["c15", "c16"]),
    ("B. How do you describe values with types?", "Object shapes, unions and narrowing.", ["c17", "c18"]),
    ("C. How do you type functions and unknown data?", "Parameters, overloads, any and unknown.", ["c19", "c20"]),
]

SYNTHESIS = r"""
TypeScript makes JavaScript safer in one way only: it reads your code before it runs and refuses promises the code breaks. Each Part marks out where that protection reaches.

\textbf{What the checker sees (A).} It sees annotations and what it can infer, and it stops at run time: types are erased, \code{tsc} emits JavaScript even with errors, and an \code{as} assertion checks nothing. So the protection covers your code's internal consistency, not the data that arrives from outside---that still needs real checks.

\textbf{What you tell it (B).} Interfaces describe shapes, matched structurally; unions say ``one of these''; narrowing turns a union back into one type as your checks prove it. Each of these lets the compiler reject a mistake at the line that makes it: a missing property, an extra one, a method the value might not have.

\textbf{Where it is weakest (C).} Functions get exactly the promises you write: optional versus default parameters, overloads for several call shapes. \code{any} removes the checker entirely; \code{unknown} keeps it and makes you prove the type. A type predicate is trusted without being checked.

\textbf{The strongest objection} is that types slow you down without changing what the program does. The answer: they don't change what it does, but they change \emph{when} you find out it is wrong---at the line where the mistake is made, before any user runs it. The cards in this Part are mostly bugs that JavaScript would only reveal at run time.
"""

TEST_QUESTIONS = [
    ("Does a type annotation change what a program does when it runs? Name one TypeScript feature that does produce code.", "c15"),
    ("What does `data as User` check?", "c15"),
    ("Why does `let count = 5; count = \"five\";` fail, while `let label; label = \"x\"; label = 5;` compiles?", "c16"),
    ("What does `noImplicitAny` reject, and why?", "c16"),
    ("Why is passing `{ x: 1, y: 2, z: 3 }` straight to a `Point` parameter an error, but passing it through a variable is not?", "c17"),
    ("Why does `sort` not compile on a `readonly number[]`, and what do you use instead?", "c17"),
    ("What may you do with a `string | number` before narrowing it?", "c18"),
    ("What does the return type `value is string` promise, and who checks it?", "c18"),
    ("How does `greeting = \"Hello\"` differ from `greeting?: string`?", "c19"),
    ("Why does `parse(\"42\")` have the type `number` only after you add overload signatures?", "c19"),
    ("Why is `unknown` safer than `any` for data from `JSON.parse`?", "c20"),
]

SNIPPETS = {
    "c15-checker": {"lang": "ts", "run": False, "compile": [4], "code": c("""
        function greet(name: string): string {
          return "Hi " + name;
        }
        greet(42);
    """)},
    "c15-erasure": {"lang": "ts", "compile": [], "code": c("""
        const count: number = "3" as any;
        console.log(count + 1, typeof count);
    """), "out": "31 string"},
    "c15-enum": {"lang": "ts", "compile": [], "code": c("""
        enum Level { Low, High }
        console.log(Level.High, Level[0]);
    """), "out": "1 Low"},
    "c15-runtime": {"lang": "ts", "compile": [], "code": c("""
        const data: unknown = JSON.parse('{"name": "Ada"}');
        if (typeof data === "object" && data !== null && "name" in data) {
          console.log(typeof data.name);
        }
    """), "out": "string"},
    "c16-infer": {"lang": "ts", "run": False, "compile": [2], "code": c("""
        let count = 5;
        count = "five";
    """)},
    "c16-any": {"lang": "ts", "run": False, "compile": [1], "code": c("""
        function total(items) {
          return items.length;
        }
    """)},
    "c16-return": {"lang": "ts", "run": False, "compile": [2], "code": c("""
        function price(cents: number): string {
          return cents / 100;
        }
    """)},
    "c17-interface": {"lang": "ts", "compile": [], "code": c("""
        interface Product { name: string; price: number; discount?: number }
        function cost(p: Product): number {
          return p.price * (1 - (p.discount ?? 0));
        }
        console.log(cost({ name: "Pen", price: 10 }));
    """), "out": "10"},
    "c17-structural": {"lang": "ts", "compile": [], "code": c("""
        interface Named { name: string }
        class Dog { constructor(public name: string) {} }
        const pet: Named = new Dog("Rex");
        console.log(pet.name);
    """), "out": "Rex"},
    "c17-excess": {"lang": "ts", "run": False, "compile": [2], "code": c("""
        interface Point { x: number; y: number }
        const p: Point = { x: 1, y: 2, z: 3 };
        const raw = { x: 1, y: 2, z: 3 };
        const q: Point = raw;
    """)},
    "c17-readonly": {"lang": "ts", "run": False, "compile": [2], "code": c("""
        function first(nums: readonly number[]): number {
          nums.push(0);
          return nums[0];
        }
    """)},
    "c18-union": {"lang": "ts", "run": False, "compile": [5], "code": c("""
        function size(x: string | string[]) {
          return x.length;
        }
        function shout(x: string | number) {
          return x.toUpperCase();
        }
    """)},
    "c18-narrow": {"lang": "ts", "compile": [], "code": c("""
        function describe(v: string | string[] | null): string {
          if (v === null) return "nothing";
          if (Array.isArray(v)) return `list of ${v.length}`;
          return `text: ${v.toUpperCase()}`;
        }
        console.log(describe(null), describe(["a"]), describe("hi"));
    """), "out": "nothing list of 1 text: HI"},
    "c18-predicate": {"lang": "ts", "compile": [], "code": c("""
        function isText(v: unknown): v is string {
          return typeof v === "string";
        }
        const words: string[] = ["a", 1, "b"].filter(isText);
        console.log(words.join(""));
    """), "out": "ab"},
    "c19-optional": {"lang": "ts", "compile": [], "code": c("""
        function greet(name: string, greeting = "Hello", mark?: string) {
          return `${greeting}, ${name}${mark ?? "!"}`;
        }
        console.log(greet("Ada"), greet("Ada", undefined, "?"));
    """), "out": "Hello, Ada! Hello, Ada?"},
    "c19-overloads": {"lang": "ts", "compile": [], "code": c("""
        function parse(v: string): number;
        function parse(v: number): string;
        function parse(v: string | number): string | number {
          return typeof v === "string" ? Number(v) : v.toFixed(2);
        }
        const n: number = parse("42");
        console.log(n + 1);
    """), "out": "43"},
    "c19-undefined": {"lang": "ts", "run": False, "compile": [4], "code": c("""
        function log(v: string): undefined {
          console.log(v);
        }
        function get(): string {
          console.log("none");
        }
    """)},
    "c20-any": {"lang": "ts", "run": False, "compile": [], "code": c("""
        const a: any = "hello";
        a.launch();
    """)},
    "c20-unknown": {"lang": "ts", "compile": [], "code": c("""
        function lengthOf(v: unknown): number {
          if (typeof v === "string" || Array.isArray(v)) return v.length;
          return 0;
        }
        console.log(lengthOf("abc"), lengthOf({ length: 5 }));
    """), "out": "3 0"},
}

R = "Run it, then change one line and predict again."
T = "Paste it into the TypeScript Playground (or run `tsc --strict`) and read the error."

CARDS = {
    "ts15-emits-anyway": note(["c15"], ["c15-erasure"],
        "The `as any` silences the checker; at run time `count` is the string \"3\" and `label` the number 42.",
        "Types never change values at run time.",
        "A string and a number, whatever their annotations say.",
        "declared number and string; actually string and number.",
        'Answering "4 \\"421\\"" by trusting the annotations.', R,
        "An annotation is a promise, not a conversion."),
    "ts15-enum-emits": note(["c15"], ["c15-enum"],
        "The enum compiles to an object with Up = 0, Down = 1, plus reverse entries 0 → \"Up\" and 1 → \"Down\".",
        "A numeric enum maps names to numbers and numbers back to names.",
        "One object with four keys.",
        "numbers, strings.",
        "Answering 2 keys (forgetting the reverse mapping).", R,
        "enum is real code, with a reverse mapping."),
    "ts15-parse-user": note(["c15", "c20"], ["c15-runtime", "c20-unknown"],
        "Reject non-objects and null, check `\"name\" in data` with a string type and `\"age\" in data` with a number type, then return only those two fields.",
        "Only objects with a string name and a number age come back, without extra fields.",
        "A new two-field object.",
        "unknown in; `User | null` out.",
        "Typing the parameter `any` lets strings slip through; typing it `User` rejects `parseUser(42)` at compile time.",
        "A valid user, extra fields, a missing age, a string age, null and a plain string.",
        "`as User` checks nothing; real checks must."),
    "ts16-total-price": note(["c16"], ["c16-any", "c16-infer"],
        "Type `items` as an array of `{ price: number; quantity: number }` and `taxRate` as `number`; let the rest be inferred.",
        "Every item has a numeric price and quantity.",
        "One running subtotal.",
        "`LineItem[]` and `number` in; `number` out.",
        "Typing the parameters `any` compiles but lets a string tax rate and items without quantity through.",
        "A normal cart and an empty one; type tests reject a string rate and a missing quantity.",
        "`any` makes the error go away and the checking too."),
    "ts16-inferred-type": note(["c16"], ["c16-infer"],
        "`count` was inferred as `number` from 5; `label` had no initial value, so its type follows each assignment.",
        "An initialised variable keeps its inferred type.",
        "Two variables.",
        "number; string then number.",
        "Thinking `label = 5` also fails.", T,
        "No initial value means no fixed type yet."),
    "ts16-format-price": note(["c16"], ["c16-return"],
        "Return `` `$${(cents / 100).toFixed(2)}` `` — a string, with two decimals.",
        "The function always returns a string.",
        "No state.",
        "number in; string out.",
        "`\"$\" + cents / 100` compiles but prints \"$12.5\".",
        "1250, 5 and 0.",
        "toFixed(2) keeps the trailing zero."),
    "ts17-product": note(["c17"], ["c17-interface"],
        "Declare `interface Product` with `discount?: number`, type the parameter, and keep `?? 0`.",
        "Every product has id, name and price; discount may be missing.",
        "No state.",
        "Product in; number out.",
        "`discount?: any` lets \"10%\" through; a required discount rejects products without one.",
        "With and without a discount; type tests reject a missing price and a string discount.",
        "Optional means `number | undefined` inside the function."),
    "ts17-excess-property": note(["c17"], ["c17-excess"],
        "Only the call with the object literal gets an excess property check; the variable passes because it has x and y.",
        "A fresh literal may not add unknown properties.",
        "Two objects with a colour.",
        "Point, object literal.",
        "Expecting both calls to fail, or neither.", T,
        "Excess property checks apply to fresh literals only."),
    "ts17-readonly-sort": note(["c17"], ["c17-readonly"],
        "Copy, then sort: `[...nums].sort((a, b) => a - b)`.",
        "The input array is never changed.",
        "One new array.",
        "`readonly number[]` in; `number[]` out.",
        "Changing the parameter to `number[]` compiles but sorts the caller's array.",
        "Unsorted numbers, numbers that sort wrongly as text, and empty.",
        "`sort` sorts in place."),
    "ts17-structural": note(["c17"], ["c17-structural", "c17-excess"],
        "A Dog has a string `name`, so it is a `Named`; the literal has no `name` and an unknown `title`.",
        "Types match by shape.",
        "One Dog instance.",
        "Named, Dog, object literal.",
        "Expecting the Dog line to fail because Dog never mentions Named.", T,
        "TypeScript checks shapes, not class names."),
    "ts18-format-id": note(["c18"], ["c18-narrow"],
        "Branch on `typeof id === \"number\"`: pad with `padStart(6, \"0\")`; otherwise upper-case the string.",
        "Inside each branch, `id` has one type.",
        "No state.",
        "`number | string` in; string out.",
        "Typing `id` as `any` compiles but lets `true` through.",
        "42, 123456 and \"ab12\"; a type test rejects `true`.",
        "Narrow before calling a type-specific method."),
    "ts18-describe-input": note(["c18"], ["c18-narrow"],
        "Check `=== null`, then `Array.isArray`; what is left is a string.",
        "Each branch handles exactly one member of the union.",
        "No state.",
        "`string | string[] | null` in; string out.",
        "`!value` treats the empty string as null.",
        "\"hi\", \"\", [\"a\", \"b\"], [] and null.",
        "An empty string is not null."),
    "ts18-is-string": note(["c18"], ["c18-predicate"],
        "Change the return type to `value is string`; the body stays the same.",
        "`true` means the value is a string.",
        "No state.",
        "unknown in; boolean (as a type predicate) out.",
        "Returning plain `boolean` leaves `filter`'s result as `(string | number)[]`.",
        "Runtime cases pass either way; the type test needs `string[]`.",
        "The compiler trusts a type predicate; it doesn't check the body."),
    "ts18-union-access": note(["c18"], ["c18-union"],
        "`toUpperCase` isn't on number, so line 2 fails; `length` exists on both string and string[].",
        "Without narrowing only shared members are allowed.",
        "No state.",
        "`string | number`, `string | string[]`.",
        "Expecting `value.length` to fail too.", T,
        "Shared members are allowed; the rest need narrowing."),
    "ts19-greet": note(["c19"], ["c19-optional"],
        "`greeting = \"Hello\"` as a default, `punctuation?: string` with `?? \"!\"`.",
        "`name` is required; the others may be missing or undefined.",
        "No state.",
        "strings in; string out.",
        "Typing greeting `any` lets `greet(\"Ada\", 5)` compile; `||` would turn an empty punctuation into \"!\".",
        "One, two and three arguments, an explicit undefined, and \"\" as punctuation.",
        "A default is used for undefined; `??` keeps \"\"."),
    "ts19-undefined-return": note(["c19"], ["c19-undefined"],
        "`logValue` may end without return (TS 5.1+); `getValue` promises a string and returns none.",
        "A function with a value return type must return one.",
        "No state.",
        "undefined, string.",
        "Expecting `logValue` to fail as in older TypeScript.", T,
        "Since 5.1, `: undefined` needs no return statement."),
    "ts19-overloads": note(["c19"], ["c19-overloads"],
        "Add `function parse(value: string): number;` and `function parse(value: number): string;` above the implementation.",
        "Callers see only the overloads.",
        "No state.",
        "string → number, number → string.",
        "Without overloads every call returns `string | number`.",
        "Runtime cases pass either way; the type tests need the precise types.",
        "The implementation signature isn't callable from outside."),
    "ts20-any-vs-unknown": note(["c20"], ["c20-any", "c20-unknown"],
        "`any` allows `a.launch()`; `unknown` refuses `u.launch()`; inside `typeof u === \"string\"` u is a string.",
        "unknown must be narrowed before use.",
        "No state.",
        "any, unknown, string.",
        "Expecting `a.launch()` to fail at compile time.", T,
        "any compiles and crashes later; unknown refuses up front."),
    "ts20-length-of": note(["c20"], ["c20-unknown"],
        "Narrow with `typeof value === \"string\" || Array.isArray(value)` and return the length; else 0.",
        "Only strings and arrays report a length.",
        "No state.",
        "unknown in; number out.",
        "Switching to `any` compiles but returns 5 for `{ length: 5 }`.",
        "\"abc\", [1, 2], 42, null and `{ length: 5 }`.",
        "Duck-typing on `length` lets impostors through."),
}

SOURCES = [
    (r"Course deck: \path{backend/app/content/js_ts_course/part2.py}, \path{quotes.py}", "In full",
     "Cards, tests, type tests, solutions, quotes, deck summaries"),
    ("TypeScript Handbook (source text, TypeScript-Website repository): The Basics; Everyday Types; Narrowing; "
     "More on Functions; Object Types; TypeScript for the New Programmer; TypeScript for JavaScript Programmers; "
     "Enums", "Searched by keyword; relevant sections read", "Chapter facts; card quotes"),
    ("TypeScript 5.1 release notes", "Section on undefined-returning functions read", "Ch.~19; card quote"),
    ("TSConfig reference: strict, noImplicitAny", "Opening paragraphs", "Ch.~16"),
]
NOT_READ = ("the rest of the TypeScript Handbook (modules, declaration files, type manipulation beyond "
            "Part 3's needs); the TypeScript specification and compiler source.")

FLAGS = [
    "Outside the material: compiler messages quoted in this guide come from running tsc " "5.9.3, not from "
    "the documentation; Node's ability to run TypeScript directly (type stripping) is a property of the "
    "runtime used for the checks, not something the material describes.",
    "Conflicts: none found between the deck and the documentation.",
    "The TypeScript Playground is mentioned as a way to see compiler errors; it was not used for any check.",
    "Analogies are authored and simplify; for example, structural typing also allows extra properties when "
    "the value is not a fresh object literal, which the key-and-lock image does not show.",
]

DEVIATIONS = COMMON_DEVIATIONS + [
    "Snippets that exist to show a compiler error were checked with tsc but not run (their run-time output "
    "is beside the point); each shows the compiler's verdict under it.",
]
REVISIONS = [f"{TODAY}: first version."]

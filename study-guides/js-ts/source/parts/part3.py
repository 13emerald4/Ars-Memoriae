"""Part 3 · Intermediate TypeScript — guide configuration."""

from common import COMMON_DEVIATIONS, TODAY, c, note

FILENAME = "part3-intermediate-typescript"
TITLE = "Part 3 · Intermediate TypeScript"
SUBTITLE = "A Socratic study guide to the 17 cards of Part 3 of “JavaScript & TypeScript: Zero to Mastery”"
META_QUESTION = "How do you make the compiler enforce the rules of your data, instead of checking them by hand?"
META_DECOMPOSITION = (
    "Part A asks how to describe data precisely (discriminated unions and generics); B, how to derive and "
    "protect types (utility types and classes); C, which compiler checks catch the bugs that remain. Every "
    "section heading is a question, answered in its first sentence; every code sample was run or "
    "compiled. The Card-by-Card Solution Guide then works every card in the deck."
)

GROUPS = [
    ("A. How do you describe data precisely?", "Discriminated unions, generics and keyof.", ["c21", "c22"]),
    ("B. How do you derive and protect types?", "Utility types and TypeScript classes.", ["c23", "c24"]),
    ("C. Which checks catch what is left?", "strictNullChecks, noUncheckedIndexedAccess and satisfies.", ["c25"]),
]

SYNTHESIS = r"""
The compiler can only enforce rules it can see. Each Part is a way of writing a rule down so that it can.

\textbf{Precise descriptions (A).} A discriminated union writes down ``a shape is one of these, and nothing else'', so a missing case fails at the \code{never} line and an impossible action fails where it is written. A generic writes down ``what comes out has the type of what went in'', and \code{keyof} writes down ``only these keys''. Without them, the same rules live only in comments and your memory.

\textbf{Derived and protected types (B).} Utility types derive one type from another, so a change to the source (a new field) flows into every derived type. Access modifiers and \code{implements} write down who may touch what and what a class promises---checked by the compiler, though TypeScript's \code{private}, unlike \code{\#}, is gone at run time.

\textbf{The remaining holes (C).} Even precise types can lie: \code{arr[0]} claims a value that may not exist, and a nullable value is easy to use unchecked. \code{strictNullChecks} and \code{noUncheckedIndexedAccess} close those holes; \code{satisfies} checks without losing precision.

\textbf{The strongest objection} is that these types grow more complex than the code they describe. The answer: each one replaces a check you would otherwise write and test by hand at every call site---and unlike a hand check, the compiler never forgets one.
"""

TEST_QUESTIONS = [
    ("What makes a union ``discriminated'', and what does checking the discriminant do?", "c21"),
    ("How does assigning to a `never` variable catch a forgotten case?", "c21"),
    ("What does the `T` in `first<T>(arr: T[])` capture that `any` would lose?", "c22"),
    ("What does `K extends keyof T` allow, and what is `T[K]`?", "c22"),
    ("Why must you remove a field at run time as well as with `Omit`?", "c23"),
    ("Does `Readonly<T>` stop `team.members.push(...)`? Why?", "c23"),
    ("How private is TypeScript's `private` at run time, compared with `#`?", "c24"),
    ("What does `noUncheckedIndexedAccess` change about `arr[0]`?", "c25"),
    ("How does `satisfies` differ from a type annotation?", "c25"),
]

SNIPPETS = {
    "c21-tag": {"lang": "ts", "compile": [], "code": c("""
        type Shape =
          | { kind: "circle"; r: number }
          | { kind: "square"; side: number };
        function area(s: Shape): number {
          return s.kind === "circle" ? Math.PI * s.r ** 2 : s.side ** 2;
        }
        console.log(area({ kind: "square", side: 3 }));
    """), "out": "9"},
    "c21-never": {"lang": "ts", "run": False, "compile": [7], "code": c("""
        type Light = "red" | "green" | "amber";
        function next(l: Light): Light {
          switch (l) {
            case "red": return "green";
            case "green": return "amber";
            default: {
              const unhandled: never = l;
              return unhandled;
            }
          }
        }
    """)},
    "c21-actions": {"lang": "ts", "run": False, "compile": [5], "code": c("""
        type Action = { type: "add"; amount: number } | { type: "reset" };
        function apply(n: number, a: Action): number {
          return a.type === "add" ? n + a.amount : 0;
        }
        apply(1, { type: "add" });
    """)},
    "c22-generic": {"lang": "ts", "compile": [], "code": c("""
        function first<T>(arr: T[]): T | undefined {
          return arr[0];
        }
        const word: string | undefined = first(["a", "b"]);
        console.log(word, first([]));
    """), "out": "a undefined"},
    "c22-constraint": {"lang": "ts", "compile": [5], "code": c("""
        function longer<T extends { length: number }>(a: T, b: T): T {
          return b.length > a.length ? b : a;
        }
        console.log(longer("ab", "c"), longer([1], [2, 3]).length);
        longer(1, 2);
    """), "out": "ab 2"},
    "c22-keyof": {"lang": "ts", "compile": [7], "code": c("""
        function get<T, K extends keyof T>(obj: T, key: K): T[K] {
          return obj[key];
        }
        const user = { id: 1, name: "Ada" };
        const userName: string = get(user, "name");
        console.log(userName);
        get(user, "age");
    """), "out": "Ada"},
    "c23-partial": {"lang": "ts", "compile": [], "code": c("""
        interface Todo { title: string; done: boolean }
        function update(t: Todo, changes: Partial<Todo>): Todo {
          return { ...t, ...changes };
        }
        console.log(update({ title: "x", done: false }, { done: true }).done);
    """), "out": "true"},
    "c23-omit": {"lang": "ts", "compile": [], "code": c("""
        interface User { id: number; hash: string }
        function publicUser(u: User): Omit<User, "hash"> {
          const { hash, ...rest } = u;
          return rest;
        }
        console.log(Object.keys(publicUser({ id: 1, hash: "x" })).join());
    """), "out": "id"},
    "c23-record": {"lang": "ts", "run": False, "compile": [2], "code": c("""
        type Role = "admin" | "viewer";
        const counts: Record<Role, number> = { admin: 1 };
    """)},
    "c23-readonly": {"lang": "ts", "compile": [], "code": c("""
        type Team = { name: string; members: string[] };
        const team: Readonly<Team> = { name: "Core", members: [] };
        team.members.push("Ada");
        console.log(team.members.length);
    """), "out": "1"},
    "c24-modifiers": {"lang": "ts", "compile": [], "code": c("""
        class Temp {
          constructor(private readonly c: number) {}
          get f(): number { return (this.c * 9) / 5 + 32; }
        }
        console.log(new Temp(100).f);
    """), "out": "212"},
    "c24-private": {"lang": "ts", "compile": [6], "code": c("""
        class Box {
          private secret = 1;
        }
        const b = new Box();
        console.log(b["secret"]);
        console.log(b.secret);
    """), "out": "1\n1"},
    "c24-implements": {"lang": "ts", "run": False, "compile": [2], "code": c("""
        interface Logger { log(m: string): void }
        class Quiet implements Logger {
          write(m: string) {}
        }
    """)},
    "c25-null": {"lang": "ts", "run": False, "compile": [2], "code": c("""
        function initial(name: string | null): string {
          return name[0];
        }
    """)},
    "c25-index": {"lang": "ts", "compile": [3], "options": {"noUncheckedIndexedAccess": True}, "code": c("""
        const scores: number[] = [];
        const first = scores[0];
        console.log(first.toFixed(1));
    """), "out": "TypeError: Cannot read properties of undefined (reading 'toFixed')"},
    "c25-satisfies": {"lang": "ts", "compile": [], "code": c("""
        type Colors = Record<"red" | "blue", string | number[]>;
        const palette = { red: "#f00", blue: [0, 0, 255] } satisfies Colors;
        console.log(palette.red.toUpperCase());
    """), "out": "#F00"},
}

T = "Paste it into the TypeScript Playground (or run `tsc --strict`) and read the error."

CARDS = {
    "ts21-area": note(["c21"], ["c21-tag", "c21-never"],
        "Switch on `shape.kind` with a case per variant, and in `default` assign `shape` to a `never` variable.",
        "Each case sees exactly one variant; `default` sees none.",
        "No state.",
        "Shape in; number out.",
        "A missing case returns undefined at run time and fails to compile with the never check.",
        "One shape of each kind; a type test rejects a triangle.",
        "Without the never line, a new variant fails silently."),
    "ts21-exhaustive": note(["c21"], ["c21-never"],
        "After the circle and square cases, a triangle can still reach `default`, so `shape` isn't `never` there.",
        "In `default`, only unhandled variants remain.",
        "No state.",
        "Shape, never.",
        "Expecting the error at the type definition or at the switch.", T,
        "The never assignment is where the compiler reports the missing case."),
    "ts21-counter-actions": note(["c21"], ["c21-actions", "c21-tag"],
        "Replace `Action` with a union of three object types, one per `type`, with `amount` only on \"add\".",
        "\"add\" always carries an amount; no other `type` is possible.",
        "No state.",
        "number and Action in; number out.",
        "A single type with `type: \"increment\" | \"add\" | \"reset\"` and an optional amount still accepts an \"add\" with no amount.",
        "Each action; type tests reject an \"add\" without amount and a \"jump\".",
        "One loose object type can't tie data to its action."),
    "ts22-first-element": note(["c22"], ["c22-generic"],
        "Declare `<T>`, take `arr: T[]`, return `arr[0]` typed `T | undefined`.",
        "The result has the array's element type, or undefined.",
        "No state.",
        "`T[]` in; `T | undefined` out.",
        "Returning `T` claims a value even for empty arrays; `any` loses the type; `null` is the wrong \"missing\".",
        "A string array, a number array, an empty array; type tests require `| undefined`.",
        "`arr[0]` on an empty array is undefined, whatever the type says."),
    "ts22-longest": note(["c22"], ["c22-constraint"],
        "Constrain `T extends { length: number }` and return `b` only when it is strictly longer.",
        "Both arguments have the same type `T`, which has a numeric length.",
        "No state.",
        "two `T`s in; `T` out.",
        "An unconstrained `T` with casts compiles for numbers; `>=` returns the second on a tie.",
        "Two strings, two arrays, a tie; a type test rejects numbers.",
        "On a tie, return the first argument."),
    "ts22-get-property": note(["c22"], ["c22-keyof"],
        "Declare `<T, K extends keyof T>` and return `obj[key]` typed `T[K]`.",
        "Only real keys are accepted, and the result has that key's type.",
        "No state.",
        "`T` and `K` in; `T[K]` out.",
        "`key: string` and an `any` result accept missing keys and lose the type.",
        "A string property and a number property; a type test rejects \"age\".",
        "`keyof T` is the union of T's keys."),
    "ts22-pluck": note(["c22"], ["c22-keyof", "c22-generic"],
        "Same pattern as getProperty, mapped over the items: return `items.map((item) => item[key])` typed `T[K][]`.",
        "Every element of the result has the type stored under `key`.",
        "One new array.",
        "`T[]` and `K` in; `T[K][]` out.",
        "Hard-coding two items passes a two-item test only; `any` types let a missing key through.",
        "Empty, one, two and three items; a type test rejects \"age\".",
        "Test 0, 1 and 3 items, not just 2."),
    "ts23-update-todo": note(["c23"], ["c23-partial"],
        "Type `changes` as `Partial<Todo>` and return `{ ...todo, ...changes }`.",
        "The result is a full Todo with the changes applied.",
        "One new object.",
        "`Todo` and `Partial<Todo>` in; `Todo` out.",
        "`changes: any` accepts unknown fields; spreading in the wrong order ignores the changes.",
        "A one-field change, no change, two fields; type tests reject an unknown field and a wrong type.",
        "Spread the changes last."),
    "ts23-public-user": note(["c23"], ["c23-omit"],
        "Take `passwordHash` out with rest destructuring and type the result `Omit<User, \"passwordHash\">`.",
        "Neither the object nor its type contains the hash.",
        "One new object without the hash.",
        "`User` in; `Omit<User, \"passwordHash\">` out.",
        "Keeping the return type `User` (with a cast) leaves the hash readable to the compiler.",
        "Run-time output has no hash; a type test requires reading it to be an error.",
        "Remove the field in both the value and the type."),
    "ts23-count-by-role": note(["c23"], ["c23-record"],
        "Start `counts: Record<Role, number>` with every role at 0, then increment for each role in the list.",
        "Every role is a key, even with count 0.",
        "One object with three counters.",
        "`Role[]` in; `Record<Role, number>` out.",
        "Counting into an empty object misses roles that never appear; `string[]` accepts roles that don't exist.",
        "Some roles, no roles; a type test rejects \"owner\".",
        "Record requires every key, so initialise every key."),
    "ts23-readonly-shallow": note(["c23"], ["c23-readonly"],
        "`Readonly` blocks reassigning `team.name`; pushing onto `team.members` changes the array, not the property.",
        "Readonly applies to the object's own properties only.",
        "One object holding one array.",
        "`Readonly<Team>`.",
        "Expecting the `push` line to fail too.", T,
        "Readonly is shallow."),
    "ts24-temperature": note(["c24"], ["c24-modifiers", "c24-private"],
        "Use `constructor(private readonly celsius: number) {}`, a `get fahrenheit()` and `describe()`.",
        "celsius is set once and hidden from callers; fahrenheit has no setter.",
        "One private number per instance.",
        "number in; number and string out.",
        "`public celsius` lets callers read it, which a type test forbids.",
        "100, 0 and -40; type tests forbid reading celsius and assigning fahrenheit.",
        "A getter without a setter is read-only to callers."),
    "ts24-private-vs-hash": note(["c24"], ["c24-private"],
        "Dot access to a `private` member fails; bracket access is TypeScript's escape hatch and compiles.",
        "private is enforced only by the compiler.",
        "One instance with two fields.",
        "Account.",
        "Expecting the bracket access to fail as well.", T,
        "TypeScript's private is soft: brackets get through."),
    "ts24-implements": note(["c24"], ["c24-implements", "c24-private"],
        "Write `class MemoryLogger implements Logger` with a private array; `history()` returns a copy.",
        "The stored log can only change through `log`.",
        "One private array of messages.",
        "strings in; string array out.",
        "Returning the private array itself lets the caller's push change the log.",
        "Two messages then a tampering push; no messages.",
        "Return copies of private arrays."),
    "ts25-strict-null": note(["c25"], ["c25-null"],
        "`name` may be null, so `name[0]` fails; `name?.[0] ?? \"?\"` handles null and returns a string.",
        "Under strictNullChecks, null must be ruled out before use.",
        "No state.",
        "`string | null`.",
        "Expecting the `?.` version to fail too.", T,
        "`?.` plus `??` handles null in one expression."),
    "ts25-unchecked-index": note(["c25"], ["c25-index"],
        "With the option on, `scores[0]` is `number | undefined`, so `first.toFixed` fails; the `??` line is safe.",
        "Every index lookup may be undefined.",
        "One array of two numbers.",
        "number | undefined.",
        "Expecting it to compile because the array clearly has two items.", T,
        "The compiler doesn't track array lengths."),
    "ts25-satisfies": note(["c25"], ["c25-satisfies"],
        "The annotation widens `annotated.red` to `Color`, which may be a tuple; `satisfies` keeps `checked.red` a string.",
        "satisfies checks without replacing the inferred type.",
        "Two objects with the same data.",
        "Record, string, tuple.",
        "Expecting `checked.red.toUpperCase()` to fail too.", T,
        "An annotation replaces the type; satisfies keeps it."),
}

SOURCES = [
    (r"Course deck: \path{backend/app/content/js_ts_course/part3.py}, \path{quotes.py}", "In full",
     "Cards, tests, type tests, solutions, quotes, deck summaries"),
    ("TypeScript Handbook (source text): Narrowing; Generics; Keyof Type Operator; Indexed Access Types; "
     "Utility Types; Object Types; Classes; Everyday Types", "Searched by keyword; relevant sections read",
     "Chapter facts; card quotes"),
    ("TypeScript 4.9 release notes (satisfies); TSConfig reference: noUncheckedIndexedAccess, strict",
     "Relevant sections", "Ch.~25; card quotes"),
]
NOT_READ = ("Handbook chapters on conditional and mapped types beyond what Part 3 uses, declaration files, "
            "modules and decorators; the TypeScript specification.")

FLAGS = [
    "Outside the material: compiler messages come from running tsc 5.9.3; the run-time TypeError message in "
    "Ch.~25 comes from running Node, not from the documentation.",
    "Conflicts: none found between the deck and the documentation.",
    "Analogies are authored and simplify; for example, a generic's type parameter can be inferred from "
    "several arguments at once, which the mould image does not show.",
]

DEVIATIONS = COMMON_DEVIATIONS + [
    "Snippets that exist to show a compiler error were checked with tsc but not run, except where the run "
    "itself makes the point (Ch.~24's bracket access and Ch.~25's crash on an empty array).",
]
REVISIONS = [f"{TODAY}: first version."]

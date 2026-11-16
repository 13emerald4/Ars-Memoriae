"""Part 1: JavaScript fundamentals, learned by reading and writing code."""

from __future__ import annotations

from textwrap import dedent

from .model import MDN_JS, CodeCard, Part, PredictCard, Source, Subdeck

U = {"$undefined": True}


def c(text: str) -> str:
    """Dedent a code block and drop the blank first line."""
    return dedent(text).strip("\n") + "\n"


def throws(text: str) -> dict:
    return {"$throws": text}


# ── 01 ────────────────────────────────────────────────────────────────────

VALUES = Subdeck(
    name="01 · Values, Variables & Types",
    summary=(
        "JavaScript has seven primitive types (string, number, bigint, boolean, undefined, "
        "symbol, null) and objects. `typeof` names them, with two traps: `typeof null` is "
        '"object", and arrays are objects too. `const` stops a variable being reassigned, '
        "not the object it points to from changing."
    ),
    sources=[
        Source("MDN — JavaScript data types and data structures", MDN_JS + "Guide/Data_structures"),
        Source("MDN — let", MDN_JS + "Reference/Statements/let"),
    ],
    cards=[
        PredictCard(
            key="js01-typeof",
            snippet=c("""
                console.log(typeof 42);
                console.log(typeof "42");
                console.log(typeof null);
                console.log(typeof []);
                console.log(typeof undefined);
                console.log(typeof 10n);
            """),
            output="number\nstring\nobject\nobject\nundefined\nbigint",
            why=(
                'typeof null is "object" (a bug kept for compatibility), so test for null with '
                "=== null. Arrays are objects, so use Array.isArray to spot them. 10n is a BigInt."
            ),
            source=Source(
                "MDN — JavaScript data types",
                MDN_JS + "Guide/Data_structures",
                'typeof null returns "object", so one has to use === null to test for null.',
            ),
        ),
        CodeCard(
            key="js01-describe-type",
            title="describeType(value)",
            task=(
                'Write `describeType(value)`: return `"null"` for `null`, `"array"` for arrays, '
                "and what `typeof` says for everything else."
            ),
            starter=c("""
                function describeType(value) {
                  // TODO: handle null and arrays before falling back to typeof
                  return typeof value;
                }
            """),
            solution=c("""
                function describeType(value) {
                  if (value === null) return "null";
                  if (Array.isArray(value)) return "array";
                  return typeof value;
                }
            """),
            tests=[
                {"input": [None], "expected": "null"},
                {"input": [[1, 2]], "expected": "array"},
                {"input": [{}], "expected": "object"},
                {"input": ["hi"], "expected": "string"},
                {"input": [""], "expected": "string"},
                {"input": [0], "expected": "number"},
                {"input": [U], "expected": "undefined"},
            ],
            wrong=[
                c("""
                    function describeType(value) {
                      if (!value) return "null";
                      if (Array.isArray(value)) return "array";
                      return typeof value;
                    }
                """),
                c("""
                    function describeType(value) {
                      if (value == null) return "null";
                      if (Array.isArray(value)) return "array";
                      return typeof value;
                    }
                """),
            ],
            why=(
                "`=== null` is the only reliable null check, and `Array.isArray` the only reliable "
                'array check. `!value` would also catch 0, "" and undefined; `== null` would '
                "also catch undefined."
            ),
        ),
        CodeCard(
            key="js01-parse-count",
            title="parseCount(text)",
            task=(
                "Write `parseCount(text)`: return the whole number written in `text`, or `null` "
                'if it isn\'t one. `"007"` is 7, `"-4"` is -4; `""`, `"   "`, `"3.5"` and '
                '`"12abc"` are all `null`.'
            ),
            starter=c("""
                function parseCount(text) {
                  return parseInt(text, 10);
                }
            """),
            solution=c("""
                function parseCount(text) {
                  if (text.trim() === "") return null;
                  const n = Number(text);
                  return Number.isInteger(n) ? n : null;
                }
            """),
            tests=[
                {"input": ["12"], "expected": 12},
                {"input": ["007"], "expected": 7},
                {"input": ["-4"], "expected": -4},
                {"input": [""], "expected": None},
                {"input": ["   "], "expected": None},
                {"input": ["3.5"], "expected": None},
                {"input": ["12abc"], "expected": None},
            ],
            wrong=[
                c("""
                    function parseCount(text) {
                      const n = Number(text);
                      return Number.isInteger(n) ? n : null;
                    }
                """),
                c("""
                    function parseCount(text) {
                      const n = parseInt(text, 10);
                      return Number.isNaN(n) ? null : n;
                    }
                """),
            ],
            why=(
                '`parseInt("12abc")` stops at the first bad character and returns 12; '
                '`Number("12abc")` is NaN. But `Number("")` and `Number("   ")` are 0, so empty '
                "input needs its own check."
            ),
        ),
        PredictCard(
            key="js01-const",
            snippet=c("""
                const settings = { theme: "dark" };
                settings.theme = "light";
                console.log(settings.theme);
                try {
                  settings = {};
                } catch (error) {
                  console.log(error.name);
                }
            """),
            output="light\nTypeError",
            why=(
                "const stops the variable from being reassigned (a TypeError at run time), but "
                "the object it points to can still change."
            ),
            source=Source("MDN — const", MDN_JS + "Reference/Statements/const"),
        ),
        PredictCard(
            key="js01-pass-by-sharing",
            snippet=c("""
                function rename(user) {
                  user.name = "Grace";
                  user = { name: "Linus" };
                }
                const person = { name: "Ada" };
                rename(person);
                console.log(person.name);
            """),
            output="Grace",
            why=(
                "JavaScript passes every argument by value. For an object that value is a "
                "reference, so changing a property through it is seen by the caller, but "
                "pointing the parameter at a new object is not."
            ),
            source=Source("MDN — Functions", MDN_JS + "Guide/Functions"),
        ),
        PredictCard(
            key="js01-tdz",
            snippet=c("""
                console.log(typeof hoisted);
                try {
                  console.log(early);
                } catch (error) {
                  console.log(error.name);
                }
                let early = 1;
                var hoisted = 2;
            """),
            output="undefined\nReferenceError",
            why=(
                "A var exists (as undefined) from the top of its function. A let or const exists "
                "too, but reading it before its declaration line throws: it is in the temporal "
                "dead zone."
            ),
            source=Source(
                "MDN — let",
                MDN_JS + "Reference/Statements/let",
                "While inside the TDZ, the variable has not been initialized with a value, and "
                "any attempt to access it will result in a ReferenceError.",
            ),
        ),
    ],
)

# ── 02 ────────────────────────────────────────────────────────────────────

OPERATORS = Subdeck(
    name="02 · Operators, Equality & Conditionals",
    summary=(
        "`===` compares without converting types; `==` converts first, with surprising "
        "results. `||` picks the right side for any falsy value, `??` only for null and "
        "undefined. `&&`, `||` and `??` return one of their operands, not true/false."
    ),
    sources=[
        Source(
            "MDN — Equality comparisons and sameness", MDN_JS + "Equality_comparisons_and_sameness"
        ),
        Source(
            "MDN — Nullish coalescing operator (??)",
            MDN_JS + "Reference/Operators/Nullish_coalescing",
        ),
    ],
    cards=[
        PredictCard(
            key="js02-equality",
            snippet=c("""
                console.log(0 == "");
                console.log(0 === "");
                console.log(null == undefined);
                console.log(null == 0);
                console.log(NaN === NaN);
            """),
            output="true\nfalse\ntrue\nfalse\nfalse",
            why=(
                '== converts "" to 0 before comparing; === does not convert. null == undefined is '
                "true, but null is not == 0. NaN is not equal to anything, itself included: use "
                "Number.isNaN."
            ),
        ),
        CodeCard(
            key="js02-port-default",
            kind="fix",
            title="Fix getPort(config)",
            task=(
                "`getPort(config)` should return `config.port`, or `3000` when the port is "
                "missing (`undefined` or `null`). Port `0` is valid and must be kept. Fix the bug."
            ),
            starter=c("""
                function getPort(config) {
                  return config.port || 3000;
                }
            """),
            solution=c("""
                function getPort(config) {
                  return config.port ?? 3000;
                }
            """),
            tests=[
                {"input": [{"port": 8080}], "expected": 8080},
                {"input": [{"port": 0}], "expected": 0},
                {"input": [{}], "expected": 3000},
                {"input": [{"port": None}], "expected": 3000},
            ],
            wrong=[
                c("""
                    function getPort(config) {
                      return config.port ? config.port : 3000;
                    }
                """),
                c("""
                    function getPort(config) {
                      return "port" in config ? config.port : 3000;
                    }
                """),
            ],
            why="`||` replaces every falsy value, 0 included; `??` replaces only null and undefined.",
            source=Source(
                "MDN — Nullish coalescing operator (??)",
                MDN_JS + "Reference/Operators/Nullish_coalescing",
                "The nullish coalescing (??) operator is a logical operator that returns its "
                "right-hand side operand when its left-hand side operand is null or undefined, "
                "and otherwise returns its left-hand side operand.",
            ),
        ),
        CodeCard(
            key="js02-letter-grade",
            title="letterGrade(score)",
            task='Write `letterGrade(score)`: `"A"` for 90 and up, `"B"` for 80–89, `"C"` for 70–79, `"F"` below 70.',
            starter=c("""
                function letterGrade(score) {
                  // TODO
                  return "";
                }
            """),
            solution=c("""
                function letterGrade(score) {
                  if (score >= 90) return "A";
                  if (score >= 80) return "B";
                  if (score >= 70) return "C";
                  return "F";
                }
            """),
            tests=[
                {"input": [95], "expected": "A"},
                {"input": [90], "expected": "A"},
                {"input": [89], "expected": "B"},
                {"input": [80], "expected": "B"},
                {"input": [79], "expected": "C"},
                {"input": [70], "expected": "C"},
                {"input": [69], "expected": "F"},
                {"input": [0], "expected": "F"},
            ],
            wrong=[
                c("""
                    function letterGrade(score) {
                      if (score > 90) return "A";
                      if (score > 80) return "B";
                      if (score > 70) return "C";
                      return "F";
                    }
                """),
                c("""
                    function letterGrade(score) {
                      if (score >= 70) return "C";
                      if (score >= 80) return "B";
                      if (score >= 90) return "A";
                      return "F";
                    }
                """),
            ],
            why=(
                "Check the highest band first and return early: each later `if` then only sees "
                "scores below the previous threshold. Test every boundary (90, 89, 80, …)."
            ),
            source=Source("MDN — if...else", MDN_JS + "Reference/Statements/if...else"),
        ),
        PredictCard(
            key="js02-logical-operands",
            snippet=c("""
                console.log("" || "fallback");
                console.log("value" && 42);
                console.log(0 ?? "zero");
                console.log(null ?? "none");
                console.log(0 || null);
            """),
            output="fallback\n42\n0\nnone\nnull",
            why=(
                "a || b returns a if it is truthy, else b. a && b returns a if it is falsy, else b. "
                'a ?? b returns b only when a is null or undefined, so 0 ?? "zero" is 0.'
            ),
        ),
        CodeCard(
            key="js02-count-truthy",
            title="countTruthy(values)",
            task="Write `countTruthy(values)`: how many items in the array are truthy?",
            starter=c("""
                function countTruthy(values) {
                  let count = 0;
                  // TODO
                  return count;
                }
            """),
            solution=c("""
                function countTruthy(values) {
                  return values.filter(Boolean).length;
                }
            """),
            tests=[
                {"input": [[0, 1, "", "hi", None, [], {}, False, True]], "expected": 5},
                {"input": [[]], "expected": 0},
                {"input": [[U, "0", "false"]], "expected": 2},
                {"input": [[[], "0"]], "expected": 2},
            ],
            wrong=[
                c("""
                    function countTruthy(values) {
                      return values.filter((v) => v !== null && v !== undefined).length;
                    }
                """),
                c("""
                    function countTruthy(values) {
                      return values.filter((v) => v != false).length;
                    }
                """),
            ],
            why=(
                'The falsy values are false, 0, -0, 0n, "", null, undefined and NaN. Everything '
                'else is truthy, including [], {} and the strings "0" and "false".'
            ),
        ),
    ],
)

# ── 03 ────────────────────────────────────────────────────────────────────

LOOPS = Subdeck(
    name="03 · Loops",
    summary=(
        "`for` counts, `while` repeats until a condition fails, `for...of` walks the values of "
        "an array or string, and `for...in` walks an object's keys (as strings, including "
        "inherited ones). A loop can `return` or `break` early."
    ),
    sources=[
        Source("MDN — Loops and iteration", MDN_JS + "Guide/Loops_and_iteration"),
        Source("MDN — for...in", MDN_JS + "Reference/Statements/for...in"),
        Source("MDN — Closures", MDN_JS + "Guide/Closures"),
    ],
    cards=[
        CodeCard(
            key="js03-sum-to",
            title="sumTo(n)",
            task="Write `sumTo(n)` with a `for` loop: return 1 + 2 + … + n. `sumTo(0)` is 0.",
            starter=c("""
                function sumTo(n) {
                  let total = 0;
                  // TODO: loop from 1 to n
                  return total;
                }
            """),
            solution=c("""
                function sumTo(n) {
                  let total = 0;
                  for (let i = 1; i <= n; i++) {
                    total += i;
                  }
                  return total;
                }
            """),
            tests=[
                {"input": [0], "expected": 0},
                {"input": [1], "expected": 1},
                {"input": [5], "expected": 15},
                {"input": [100], "expected": 5050},
            ],
            wrong=[
                c("""
                    function sumTo(n) {
                      let total = 0;
                      for (let i = 1; i < n; i++) {
                        total += i;
                      }
                      return total;
                    }
                """),
            ],
            why="`i <= n` includes n itself; `i < n` is the classic off-by-one that stops one short.",
            source=Source("MDN — Loops and iteration", MDN_JS + "Guide/Loops_and_iteration"),
        ),
        CodeCard(
            key="js03-count-vowels",
            title="countVowels(text)",
            task="Write `countVowels(text)` using `for...of`: count a, e, i, o and u in either case.",
            starter=c("""
                function countVowels(text) {
                  let count = 0;
                  // TODO: for (const ch of ...)
                  return count;
                }
            """),
            solution=c("""
                function countVowels(text) {
                  let count = 0;
                  for (const ch of text.toLowerCase()) {
                    if ("aeiou".includes(ch)) count++;
                  }
                  return count;
                }
            """),
            tests=[
                {"input": ["hello"], "expected": 2},
                {"input": ["AEIOU"], "expected": 5},
                {"input": ["rhythm"], "expected": 0},
                {"input": [""], "expected": 0},
                {"input": ["Programming Is Fun"], "expected": 5},
            ],
            wrong=[
                c("""
                    function countVowels(text) {
                      let count = 0;
                      for (const ch of text) {
                        if ("aeiou".includes(ch)) count++;
                      }
                      return count;
                    }
                """),
            ],
            why="`for...of` gives each character of a string. Lower-case once so one check covers both cases.",
        ),
        CodeCard(
            key="js03-fizzbuzz",
            title="fizzBuzz(n)",
            task=(
                'Write `fizzBuzz(n)`: return an array of strings for 1..n — `"Fizz"` for multiples '
                'of 3, `"Buzz"` for multiples of 5, `"FizzBuzz"` for both, otherwise the number '
                "as a string."
            ),
            starter=c("""
                function fizzBuzz(n) {
                  const out = [];
                  // TODO
                  return out;
                }
            """),
            solution=c("""
                function fizzBuzz(n) {
                  const out = [];
                  for (let i = 1; i <= n; i++) {
                    if (i % 15 === 0) out.push("FizzBuzz");
                    else if (i % 3 === 0) out.push("Fizz");
                    else if (i % 5 === 0) out.push("Buzz");
                    else out.push(String(i));
                  }
                  return out;
                }
            """),
            tests=[
                {"input": [5], "expected": ["1", "2", "Fizz", "4", "Buzz"]},
                {
                    "input": [15],
                    "expected": [
                        "1",
                        "2",
                        "Fizz",
                        "4",
                        "Buzz",
                        "Fizz",
                        "7",
                        "8",
                        "Fizz",
                        "Buzz",
                        "11",
                        "Fizz",
                        "13",
                        "14",
                        "FizzBuzz",
                    ],
                },
                {"input": [0], "expected": []},
            ],
            wrong=[
                c("""
                    function fizzBuzz(n) {
                      const out = [];
                      for (let i = 1; i <= n; i++) {
                        if (i % 3 === 0) out.push("Fizz");
                        else if (i % 5 === 0) out.push("Buzz");
                        else if (i % 15 === 0) out.push("FizzBuzz");
                        else out.push(String(i));
                      }
                      return out;
                    }
                """),
                c("""
                    function fizzBuzz(n) {
                      const out = [];
                      for (let i = 1; i <= n; i++) {
                        if (i % 15 === 0) out.push("FizzBuzz");
                        else if (i % 3 === 0) out.push("Fizz");
                        else if (i % 5 === 0) out.push("Buzz");
                        else out.push(i);
                      }
                      return out;
                    }
                """),
            ],
            why=(
                "Test the most specific case (divisible by both) first, or 15 is caught by the "
                "3 check. The remainder operator % tells you divisibility."
            ),
        ),
        CodeCard(
            key="js03-first-index-over",
            title="firstIndexOver(nums, limit)",
            task=(
                "Write `firstIndexOver(nums, limit)`: return the index of the first number "
                "greater than `limit`, or -1 if there is none. Stop as soon as you find it."
            ),
            starter=c("""
                function firstIndexOver(nums, limit) {
                  // TODO
                  return -1;
                }
            """),
            solution=c("""
                function firstIndexOver(nums, limit) {
                  for (let i = 0; i < nums.length; i++) {
                    if (nums[i] > limit) return i;
                  }
                  return -1;
                }
            """),
            tests=[
                {"input": [[1, 5, 9], 4], "expected": 1},
                {"input": [[1, 2], 5], "expected": -1},
                {"input": [[], 0], "expected": -1},
                {"input": [[5, 5, 6], 5], "expected": 2},
                {"input": [[7, 8], 5], "expected": 0},
            ],
            wrong=[
                c("""
                    function firstIndexOver(nums, limit) {
                      for (let i = 0; i < nums.length; i++) {
                        if (nums[i] >= limit) return i;
                      }
                      return -1;
                    }
                """),
                c("""
                    function firstIndexOver(nums, limit) {
                      let found = -1;
                      for (let i = 0; i < nums.length; i++) {
                        if (nums[i] > limit) found = i;
                      }
                      return found;
                    }
                """),
            ],
            why=(
                "`return` inside the loop ends it at the first match. Without it you would "
                "keep overwriting the answer and end up with the last match."
            ),
        ),
        PredictCard(
            key="js03-closure-in-loop",
            snippet=c("""
                const withVar = [];
                for (var i = 0; i < 3; i++) {
                  withVar.push(() => i);
                }
                const withLet = [];
                for (let j = 0; j < 3; j++) {
                  withLet.push(() => j);
                }
                console.log(withVar.map((f) => f()).join(" "));
                console.log(withLet.map((f) => f()).join(" "));
            """),
            output="3 3 3\n0 1 2",
            why=(
                "var makes one i for the whole loop, so every function sees its final value, 3. "
                "let makes a fresh j for each iteration, so each function keeps its own."
            ),
            source=Source(
                "MDN — Closures",
                MDN_JS + "Guide/Closures",
                "Prior to the introduction of the let keyword, a common problem with closures "
                "occurred when you created them inside a loop.",
            ),
        ),
        PredictCard(
            key="js03-for-in-vs-of",
            snippet=c("""
                const scores = [10, 20];
                scores.label = "round 1";
                const keys = [];
                for (const key in scores) keys.push(key);
                const values = [];
                for (const value of scores) values.push(value);
                console.log(keys.join(","));
                console.log(values.join(","));
            """),
            output="0,1,label\n10,20",
            why=(
                "for...in visits every enumerable string key, extra and inherited properties "
                "included, and gives indexes as strings. Use for...of for the values of an array."
            ),
            source=Source(
                "MDN — for...in",
                MDN_JS + "Reference/Statements/for...in",
                "The for...in statement iterates over all enumerable string properties of an "
                "object (ignoring properties keyed by symbols), including inherited enumerable "
                "properties.",
            ),
        ),
    ],
)

# ── 04 ────────────────────────────────────────────────────────────────────

STRINGS = Subdeck(
    name="04 · Strings",
    summary=(
        "Strings are immutable: `toUpperCase`, `slice`, `replace` and friends return new "
        "strings. `split` turns a string into an array and `join` turns it back. `+` with a "
        "string concatenates; the other arithmetic operators convert to numbers."
    ),
    sources=[Source("MDN — String", MDN_JS + "Reference/Global_Objects/String")],
    cards=[
        CodeCard(
            key="js04-capitalize",
            title="capitalize(word)",
            task='Write `capitalize(word)`: first letter upper-case, the rest lower-case. `""` stays `""`.',
            starter=c("""
                function capitalize(word) {
                  // TODO
                  return word;
                }
            """),
            solution=c("""
                function capitalize(word) {
                  if (word === "") return "";
                  return word[0].toUpperCase() + word.slice(1).toLowerCase();
                }
            """),
            tests=[
                {"input": ["hello"], "expected": "Hello"},
                {"input": ["wORLD"], "expected": "World"},
                {"input": ["a"], "expected": "A"},
                {"input": [""], "expected": ""},
            ],
            wrong=[
                c("""
                    function capitalize(word) {
                      return word[0].toUpperCase() + word.slice(1).toLowerCase();
                    }
                """),
                c("""
                    function capitalize(word) {
                      if (word === "") return "";
                      return word[0].toUpperCase() + word.slice(1);
                    }
                """),
            ],
            why=(
                '`word[0]` is undefined for "", and calling a method on undefined throws. '
                "`slice(1)` returns everything after the first character."
            ),
        ),
        CodeCard(
            key="js04-palindrome",
            title="isPalindrome(text)",
            task=(
                "Write `isPalindrome(text)`: true if `text` reads the same backwards, ignoring "
                "case, spaces and punctuation."
            ),
            starter=c("""
                function isPalindrome(text) {
                  // TODO
                  return false;
                }
            """),
            solution=c(r"""
                function isPalindrome(text) {
                  const letters = text.toLowerCase().replace(/[^a-z0-9]/g, "");
                  return letters === [...letters].reverse().join("");
                }
            """),
            tests=[
                {"input": ["racecar"], "expected": True},
                {"input": ["Race Car"], "expected": True},
                {"input": ["A man, a plan, a canal: Panama"], "expected": True},
                {"input": ["hello"], "expected": False},
                {"input": [""], "expected": True},
            ],
            wrong=[
                c("""
                    function isPalindrome(text) {
                      const letters = text.toLowerCase();
                      return letters === [...letters].reverse().join("");
                    }
                """),
                c(r"""
                    function isPalindrome(text) {
                      const letters = text.replace(/[^a-zA-Z0-9]/g, "");
                      return letters === [...letters].reverse().join("");
                    }
                """),
            ],
            why=(
                "Clean the text first, then compare it with its reverse. Strings have no "
                "reverse(): spread into an array, reverse, and join back."
            ),
        ),
        CodeCard(
            key="js04-initials",
            title="initials(fullName)",
            task=(
                'Write `initials(fullName)`: `"Ada Lovelace"` → `"A.L."`. Names may be lower-case '
                "and have extra spaces."
            ),
            starter=c("""
                function initials(fullName) {
                  // TODO
                  return "";
                }
            """),
            solution=c(r"""
                function initials(fullName) {
                  return fullName
                    .trim()
                    .split(/\s+/)
                    .map((part) => part[0].toUpperCase() + ".")
                    .join("");
                }
            """),
            tests=[
                {"input": ["Ada Lovelace"], "expected": "A.L."},
                {"input": ["grace brewster hopper"], "expected": "G.B.H."},
                {"input": ["  linus   torvalds "], "expected": "L.T."},
                {"input": ["Cher"], "expected": "C."},
            ],
            wrong=[
                c("""
                    function initials(fullName) {
                      return fullName
                        .split(" ")
                        .map((part) => part[0].toUpperCase() + ".")
                        .join("");
                    }
                """),
            ],
            why=(
                '`split(" ")` leaves empty strings between repeated spaces; trim first and split '
                "on the pattern /\\s+/ (one or more whitespace characters)."
            ),
        ),
        PredictCard(
            key="js04-plus-coercion",
            snippet=c("""
                console.log("5" + 3);
                console.log("5" - 3);
                console.log("5" * "2");
                console.log(1 + 2 + "3");
                console.log("1" + 2 + 3);
            """),
            output="53\n2\n10\n33\n123",
            why=(
                "+ concatenates as soon as either side is a string; -, * and / convert to numbers. "
                'Evaluation runs left to right: 1 + 2 is 3 before "3" is joined on.'
            ),
        ),
        PredictCard(
            key="js04-immutable",
            snippet=c("""
                const word = "cat";
                const upper = word.toUpperCase();
                const replaced = word.replace("c", "b");
                console.log(word, upper, replaced);
            """),
            output="cat CAT bat",
            why="String methods return new strings; the original never changes.",
            source=Source(
                "MDN — JavaScript data types",
                MDN_JS + "Guide/Data_structures",
                "JavaScript strings are immutable. This means that once a string is created, it "
                "is not possible to modify it.",
            ),
        ),
    ],
)

# ── 05 ────────────────────────────────────────────────────────────────────

FUNCTIONS = Subdeck(
    name="05 · Functions, Scope & Closures",
    summary=(
        "Function declarations are hoisted; function expressions assigned to `const` are not "
        "usable before their line. A closure is a function that keeps using the variables of "
        "the scope it was created in, which is how you keep state private. Rest parameters "
        "(`...args`) collect any number of arguments into a real array."
    ),
    sources=[
        Source("MDN — Functions", MDN_JS + "Guide/Functions"),
        Source("MDN — Closures", MDN_JS + "Guide/Closures"),
    ],
    cards=[
        PredictCard(
            key="js05-hoisting",
            snippet=c("""
                console.log(declared());
                try {
                  console.log(expressed());
                } catch (error) {
                  console.log(error.name);
                }
                function declared() {
                  return "declared works";
                }
                const expressed = function () {
                  return "expressed works";
                };
            """),
            output="declared works\nReferenceError",
            why=(
                "A function declaration is created before any code runs. A const is not usable "
                "until its line runs, so calling it earlier throws a ReferenceError."
            ),
        ),
        CodeCard(
            key="js05-make-counter",
            title="makeCounter(start)",
            task=(
                "Write `makeCounter(start)`: return an object with `increment()` (adds 1, returns "
                "the new count) and `current()`. Each counter must keep its own private count. "
                "Don't change `check`."
            ),
            starter=c("""
                // Test driver: don't change.
                function check(start) {
                  const a = makeCounter(start);
                  const b = makeCounter(100);
                  return [a.increment(), a.increment(), b.increment(), a.current(), b.current()];
                }

                function makeCounter(start) {
                  // TODO: keep the count in a variable the returned functions close over
                  return { increment() {}, current() {} };
                }
            """),
            solution=c("""
                // Test driver: don't change.
                function check(start) {
                  const a = makeCounter(start);
                  const b = makeCounter(100);
                  return [a.increment(), a.increment(), b.increment(), a.current(), b.current()];
                }

                function makeCounter(start) {
                  let count = start;
                  return {
                    increment() {
                      count += 1;
                      return count;
                    },
                    current() {
                      return count;
                    },
                  };
                }
            """),
            tests=[
                {"input": [0], "expected": [1, 2, 101, 2, 101]},
                {"input": [10], "expected": [11, 12, 101, 12, 101]},
            ],
            wrong=[
                c("""
                    // Test driver: don't change.
                    function check(start) {
                      const a = makeCounter(start);
                      const b = makeCounter(100);
                      return [a.increment(), a.increment(), b.increment(), a.current(), b.current()];
                    }

                    let count = 0;
                    function makeCounter(start) {
                      count = start;
                      return {
                        increment() {
                          count += 1;
                          return count;
                        },
                        current() {
                          return count;
                        },
                      };
                    }
                """),
            ],
            why=(
                "Each call to makeCounter creates a new `count`, and the returned methods close "
                "over that one. A variable outside the function would be shared by every counter."
            ),
            source=Source("MDN — Closures", MDN_JS + "Guide/Closures"),
            difficulty="Medium",
        ),
        CodeCard(
            key="js05-once",
            title="once(fn)",
            task=(
                "Write `once(fn)`: return a function that calls `fn` the first time only and "
                "returns that first result on every later call — even when the result is "
                "`undefined`. Don't change `check`."
            ),
            starter=c("""
                // Test driver: don't change.
                function check(values) {
                  let calls = 0;
                  const double = once((x) => {
                    calls++;
                    return x * 2;
                  });
                  const results = values.map((v) => double(v));
                  let logs = 0;
                  const log = once(() => {
                    logs++;
                  });
                  log();
                  log();
                  return { results, calls, logs };
                }

                function once(fn) {
                  // TODO
                  return fn;
                }
            """),
            solution=c("""
                // Test driver: don't change.
                function check(values) {
                  let calls = 0;
                  const double = once((x) => {
                    calls++;
                    return x * 2;
                  });
                  const results = values.map((v) => double(v));
                  let logs = 0;
                  const log = once(() => {
                    logs++;
                  });
                  log();
                  log();
                  return { results, calls, logs };
                }

                function once(fn) {
                  let done = false;
                  let result;
                  return (...args) => {
                    if (!done) {
                      done = true;
                      result = fn(...args);
                    }
                    return result;
                  };
                }
            """),
            tests=[
                {"input": [[3, 5, 7]], "expected": {"results": [6, 6, 6], "calls": 1, "logs": 1}},
                {"input": [[]], "expected": {"results": [], "calls": 0, "logs": 1}},
            ],
            wrong=[
                c("""
                    // Test driver: don't change.
                    function check(values) {
                      let calls = 0;
                      const double = once((x) => {
                        calls++;
                        return x * 2;
                      });
                      const results = values.map((v) => double(v));
                      let logs = 0;
                      const log = once(() => {
                        logs++;
                      });
                      log();
                      log();
                      return { results, calls, logs };
                    }

                    function once(fn) {
                      let result;
                      return (...args) => {
                        if (result === undefined) result = fn(...args);
                        return result;
                      };
                    }
                """),
            ],
            why=(
                'Track "already called" in its own flag. Using the result itself as the flag '
                "breaks for a function that returns undefined: it gets called again."
            ),
            difficulty="Medium",
        ),
        CodeCard(
            key="js05-sum-rest",
            title="sum(...numbers)",
            task="Write `sum(...numbers)`: add up any number of arguments. `sum()` is 0.",
            starter=c("""
                function sum(numbers) {
                  // TODO
                  return 0;
                }
            """),
            solution=c("""
                function sum(...numbers) {
                  return numbers.reduce((total, n) => total + n, 0);
                }
            """),
            tests=[
                {"input": [1, 2, 3], "expected": 6},
                {"input": [], "expected": 0},
                {"input": [5], "expected": 5},
                {"input": [-1, 1, 10], "expected": 10},
            ],
            wrong=[
                c("""
                    function sum(...numbers) {
                      return numbers.reduce((total, n) => total + n);
                    }
                """),
                c("""
                    function sum(numbers) {
                      return numbers.reduce((total, n) => total + n, 0);
                    }
                """),
            ],
            why=(
                "`...numbers` gathers all arguments into a real array. reduce needs the initial "
                "value 0, or an empty array throws a TypeError."
            ),
            source=Source("MDN — Functions", MDN_JS + "Guide/Functions"),
        ),
    ],
)

# ── 06 ────────────────────────────────────────────────────────────────────

ARRAYS = Subdeck(
    name="06 · Arrays & Iteration",
    summary=(
        "`map` transforms every item, `filter` keeps some, `reduce` folds them into one "
        "value (give it a starting value), and `forEach` only runs side effects — it always "
        "returns undefined. `sort` sorts in place and, without a compare function, as strings. "
        "Assigning an array copies the reference, not the items."
    ),
    sources=[
        Source("MDN — Array.prototype.sort()", MDN_JS + "Reference/Global_Objects/Array/sort"),
        Source("MDN — Array.prototype.reduce()", MDN_JS + "Reference/Global_Objects/Array/reduce"),
    ],
    cards=[
        PredictCard(
            key="js06-sort-default",
            snippet=c("""
                const nums = [10, 9, 1, 100];
                nums.sort();
                console.log(nums.join(" "));
                nums.sort((a, b) => a - b);
                console.log(nums.join(" "));
            """),
            output="1 10 100 9\n1 9 10 100",
            why=(
                'Without a compare function, sort compares the items as strings, and "100" comes '
                'before "9". (a, b) => a - b sorts numbers ascending. sort also changes the '
                "array in place."
            ),
            source=Source(
                "MDN — Array.prototype.sort()",
                MDN_JS + "Reference/Global_Objects/Array/sort",
                "The default sort order is ascending, built upon converting the elements into "
                "strings, then comparing their sequences of UTF-16 code unit values.",
            ),
        ),
        CodeCard(
            key="js06-squares-of-evens",
            title="squaresOfEvens(nums)",
            task="Write `squaresOfEvens(nums)` with `filter` and `map`: the squares of the even numbers, in order.",
            starter=c("""
                function squaresOfEvens(nums) {
                  // TODO: filter, then map
                  return nums;
                }
            """),
            solution=c("""
                function squaresOfEvens(nums) {
                  return nums.filter((n) => n % 2 === 0).map((n) => n * n);
                }
            """),
            tests=[
                {"input": [[1, 2, 3, 4]], "expected": [4, 16]},
                {"input": [[]], "expected": []},
                {"input": [[-2, 3, 0]], "expected": [4, 0]},
                {"input": [[1, 3]], "expected": []},
            ],
            wrong=[
                c("""
                    function squaresOfEvens(nums) {
                      return nums.filter((n) => n % 2 === 1).map((n) => n * n);
                    }
                """),
                c("""
                    function squaresOfEvens(nums) {
                      return nums.map((n) => n * n);
                    }
                """),
            ],
            why="filter keeps the items whose callback returns true; map returns a new array of the same length.",
        ),
        CodeCard(
            key="js06-average",
            title="average(nums)",
            task="Write `average(nums)` using `reduce`: the mean of the numbers, or 0 for an empty array.",
            starter=c("""
                function average(nums) {
                  // TODO
                  return 0;
                }
            """),
            solution=c("""
                function average(nums) {
                  if (nums.length === 0) return 0;
                  const total = nums.reduce((sum, n) => sum + n, 0);
                  return total / nums.length;
                }
            """),
            tests=[
                {"input": [[2, 4, 6]], "expected": 4},
                {"input": [[]], "expected": 0},
                {"input": [[5]], "expected": 5},
                {"input": [[1, 2]], "expected": 1.5},
            ],
            wrong=[
                c("""
                    function average(nums) {
                      return nums.reduce((sum, n) => sum + n) / nums.length;
                    }
                """),
                c("""
                    function average(nums) {
                      return nums.reduce((sum, n) => sum + n, 0) / nums.length;
                    }
                """),
            ],
            why=(
                "reduce without a starting value throws on an empty array, and 0 / 0 is NaN, so "
                "an empty array needs its own answer."
            ),
            source=Source(
                "MDN — Array.prototype.reduce()", MDN_JS + "Reference/Global_Objects/Array/reduce"
            ),
        ),
        CodeCard(
            key="js06-foreach-returns-undefined",
            kind="fix",
            title="Fix doubled(nums)",
            task="`doubled(nums)` should return a new array with every number doubled, but it returns `undefined`. Fix it.",
            starter=c("""
                function doubled(nums) {
                  return nums.forEach((n) => n * 2);
                }
            """),
            solution=c("""
                function doubled(nums) {
                  return nums.map((n) => n * 2);
                }
            """),
            tests=[
                {"input": [[1, 2, 3]], "expected": [2, 4, 6]},
                {"input": [[]], "expected": []},
                {"input": [[-1]], "expected": [-2]},
            ],
            why=(
                "forEach runs the callback for its side effects and always returns undefined. "
                "To build a new array from the results, use map."
            ),
            source=Source(
                "MDN — Array.prototype.forEach()", MDN_JS + "Reference/Global_Objects/Array/forEach"
            ),
        ),
        CodeCard(
            key="js06-group-by-category",
            title="groupByCategory(items)",
            task=(
                "Write `groupByCategory(items)` with `reduce`: given `{ name, category }` objects, "
                "return an object mapping each category to the names in it, in order."
            ),
            starter=c("""
                function groupByCategory(items) {
                  // TODO: items.reduce((groups, item) => ..., {})
                  return {};
                }
            """),
            solution=c("""
                function groupByCategory(items) {
                  return items.reduce((groups, item) => {
                    if (!groups[item.category]) groups[item.category] = [];
                    groups[item.category].push(item.name);
                    return groups;
                  }, {});
                }
            """),
            tests=[
                {
                    "input": [
                        [
                            {"name": "Apple", "category": "Fruit"},
                            {"name": "Carrot", "category": "Vegetable"},
                            {"name": "Banana", "category": "Fruit"},
                        ]
                    ],
                    "expected": {"Fruit": ["Apple", "Banana"], "Vegetable": ["Carrot"]},
                },
                {"input": [[]], "expected": {}},
                {
                    "input": [[{"name": "Kale", "category": "Leafy"}]],
                    "expected": {"Leafy": ["Kale"]},
                },
            ],
            wrong=[
                c("""
                    function groupByCategory(items) {
                      return items.reduce((groups, item) => {
                        groups[item.category] = [item.name];
                        return groups;
                      }, {});
                    }
                """),
                c("""
                    function groupByCategory(items) {
                      return items.reduce((groups, item) => {
                        if (!groups[item.category]) groups[item.category] = [];
                        groups[item.category].push(item);
                        return groups;
                      }, {});
                    }
                """),
            ],
            why=(
                "The accumulator starts as {} and must be returned from every callback. Create "
                "the category's array the first time you see it, then push."
            ),
            difficulty="Medium",
        ),
        PredictCard(
            key="js06-shared-reference",
            snippet=c("""
                const original = [1, 2, 3];
                const alias = original;
                const copy = [...original];
                alias.push(4);
                copy.push(5, 6);
                console.log(original.length, alias.length, copy.length);
                console.log(original === alias, original === copy);
            """),
            output="4 4 5\ntrue false",
            why=(
                "alias = original copies the reference, so both names point at one array. "
                "[...original] builds a new array with the same items."
            ),
        ),
    ],
)

# ── 07 ────────────────────────────────────────────────────────────────────

OBJECTS = Subdeck(
    name="07 · Objects, Destructuring & Spread",
    summary=(
        "Destructuring pulls properties into variables, with renames (`{ a: b }`) and defaults "
        "(`{ a = 1 }`, used only for undefined). Spread (`{ ...obj }`) copies one level deep: "
        "nested objects are shared. Optional chaining (`?.`) stops at null or undefined "
        "instead of throwing."
    ),
    sources=[
        Source("MDN — Destructuring", MDN_JS + "Reference/Operators/Destructuring"),
        Source("MDN — Spread syntax", MDN_JS + "Reference/Operators/Spread_syntax"),
        Source("MDN — Optional chaining", MDN_JS + "Reference/Operators/Optional_chaining"),
    ],
    cards=[
        CodeCard(
            key="js07-format-user",
            title="formatUser(user)",
            task=(
                "Write `formatUser(user)`: given `{ firstName, lastName, role }`, return "
                '`"LastName, FirstName (ROLE)"` with the role in upper case. A missing role '
                'means `"GUEST"`. Use destructuring with a default.'
            ),
            starter=c("""
                function formatUser(user) {
                  // TODO: const { firstName, lastName, role = ... } = user;
                  return "";
                }
            """),
            solution=c("""
                function formatUser(user) {
                  const { firstName, lastName, role = "GUEST" } = user;
                  return `${lastName}, ${firstName} (${role.toUpperCase()})`;
                }
            """),
            tests=[
                {
                    "input": [{"firstName": "Ada", "lastName": "Lovelace", "role": "admin"}],
                    "expected": "Lovelace, Ada (ADMIN)",
                },
                {
                    "input": [{"firstName": "Alan", "lastName": "Turing"}],
                    "expected": "Turing, Alan (GUEST)",
                },
                {
                    "input": [{"firstName": "Grace", "lastName": "Hopper", "role": U}],
                    "expected": "Hopper, Grace (GUEST)",
                },
                {
                    "input": [{"firstName": "Linus", "lastName": "Torvalds", "role": "eDiToR"}],
                    "expected": "Torvalds, Linus (EDITOR)",
                },
            ],
            wrong=[
                c("""
                    function formatUser(user) {
                      const { firstName, lastName, role } = user;
                      return `${lastName}, ${firstName} (${role.toUpperCase()})`;
                    }
                """),
                c("""
                    function formatUser(user) {
                      const { firstName, lastName, role = "GUEST" } = user;
                      return `${firstName} ${lastName} (${role.toUpperCase()})`;
                    }
                """),
            ],
            why='A destructuring default applies when the property is missing or undefined (not for null or "").',
            source=Source("MDN — Destructuring", MDN_JS + "Reference/Operators/Destructuring"),
        ),
        PredictCard(
            key="js07-shallow-spread",
            snippet=c("""
                const original = { name: "Ada", skills: ["math"] };
                const copy = { ...original };
                copy.name = "Grace";
                copy.skills.push("code");
                console.log(original.name);
                console.log(original.skills.join(","));
            """),
            output="Ada\nmath,code",
            why=(
                "Spread copies the top-level properties. copy.name is its own string, but "
                "copy.skills is the same array as original.skills. For a deep copy use "
                "structuredClone."
            ),
            source=Source(
                "MDN — Spread syntax",
                MDN_JS + "Reference/Operators/Spread_syntax",
                "Spread syntax effectively goes one level deep while copying an array.",
            ),
        ),
        CodeCard(
            key="js07-with-defaults",
            title="withDefaults(options)",
            task=(
                "Write `withDefaults(options)`: return a new object starting from "
                '`{ theme: "light", fontSize: 14, autosave: true }`, overridden by whatever '
                "`options` sets. Use spread."
            ),
            starter=c("""
                function withDefaults(options) {
                  const defaults = { theme: "light", fontSize: 14, autosave: true };
                  // TODO
                  return defaults;
                }
            """),
            solution=c("""
                function withDefaults(options) {
                  const defaults = { theme: "light", fontSize: 14, autosave: true };
                  return { ...defaults, ...options };
                }
            """),
            tests=[
                {"input": [{}], "expected": {"theme": "light", "fontSize": 14, "autosave": True}},
                {
                    "input": [{"theme": "dark"}],
                    "expected": {"theme": "dark", "fontSize": 14, "autosave": True},
                },
                {
                    "input": [{"autosave": False, "fontSize": 18}],
                    "expected": {"theme": "light", "fontSize": 18, "autosave": False},
                },
            ],
            wrong=[
                c("""
                    function withDefaults(options) {
                      const defaults = { theme: "light", fontSize: 14, autosave: true };
                      return { ...options, ...defaults };
                    }
                """),
            ],
            why="Later properties win, so spread the defaults first and the overrides second.",
        ),
        CodeCard(
            key="js07-pick",
            title="pick(obj, keys)",
            task=(
                "Write `pick(obj, keys)`: a new object with only the listed keys that `obj` "
                "actually has. Keep keys whose value is `null`."
            ),
            starter=c("""
                function pick(obj, keys) {
                  const result = {};
                  // TODO
                  return result;
                }
            """),
            solution=c("""
                function pick(obj, keys) {
                  const result = {};
                  for (const key of keys) {
                    if (key in obj) result[key] = obj[key];
                  }
                  return result;
                }
            """),
            tests=[
                {"input": [{"a": 1, "b": 2, "c": 3}, ["a", "c"]], "expected": {"a": 1, "c": 3}},
                {"input": [{"a": 1}, ["a", "z"]], "expected": {"a": 1}},
                {"input": [{"a": 1}, []], "expected": {}},
                {"input": [{"a": None}, ["a"]], "expected": {"a": None}},
            ],
            wrong=[
                c("""
                    function pick(obj, keys) {
                      const result = {};
                      for (const key of keys) result[key] = obj[key];
                      return result;
                    }
                """),
                c("""
                    function pick(obj, keys) {
                      const result = {};
                      for (const key of keys) {
                        if (obj[key]) result[key] = obj[key];
                      }
                      return result;
                    }
                """),
            ],
            why=(
                "`key in obj` asks whether the property exists. Testing its value instead drops "
                'real properties that hold null, 0 or "", and copying blindly adds undefined keys.'
            ),
        ),
        PredictCard(
            key="js07-optional-chaining",
            snippet=c("""
                const user = { profile: null };
                console.log(user.profile?.email);
                console.log(user.settings?.theme ?? "default");
                try {
                  console.log(user.profile.email);
                } catch (error) {
                  console.log(error.name);
                }
            """),
            output="undefined\ndefault\nTypeError",
            why=(
                "?. returns undefined as soon as the value on its left is null or undefined. "
                "Plain . on null throws a TypeError."
            ),
            source=Source(
                "MDN — Optional chaining", MDN_JS + "Reference/Operators/Optional_chaining"
            ),
        ),
    ],
)

# ── 08 ────────────────────────────────────────────────────────────────────

COLLECTIONS = Subdeck(
    name="08 · Map & Set",
    summary=(
        "A `Set` holds unique values; a `Map` holds key → value pairs where keys can be any "
        "type and stay in insertion order. Plain objects turn keys into strings and inherit "
        'keys such as "constructor", which makes them risky as dictionaries.'
    ),
    sources=[Source("MDN — Keyed collections", MDN_JS + "Guide/Keyed_collections")],
    cards=[
        CodeCard(
            key="js08-unique",
            title="unique(values)",
            task="Write `unique(values)` with a `Set`: the values without duplicates, in first-seen order.",
            starter=c("""
                function unique(values) {
                  // TODO
                  return values;
                }
            """),
            solution=c("""
                function unique(values) {
                  return [...new Set(values)];
                }
            """),
            tests=[
                {"input": [[3, 1, 3, 2, 1]], "expected": [3, 1, 2]},
                {"input": [[]], "expected": []},
                {"input": [["a", "A", "a"]], "expected": ["a", "A"]},
                {"input": [[1, "1"]], "expected": [1, "1"]},
            ],
            wrong=[
                c("""
                    function unique(values) {
                      return [...new Set(values)].sort();
                    }
                """),
            ],
            why="A Set keeps one of each value, compared with ===, in insertion order. Spread it back into an array.",
        ),
        CodeCard(
            key="js08-most-frequent-word",
            title="mostFrequentWord(text)",
            task=(
                "Write `mostFrequentWord(text)` with a `Map`: the most common word, lower-cased. "
                'On a tie, return the word that appeared first. Empty text gives `""`.'
            ),
            starter=c("""
                function mostFrequentWord(text) {
                  const counts = new Map();
                  // TODO
                  return "";
                }
            """),
            solution=c(r"""
                function mostFrequentWord(text) {
                  const counts = new Map();
                  for (const word of text.toLowerCase().split(/\s+/).filter(Boolean)) {
                    counts.set(word, (counts.get(word) ?? 0) + 1);
                  }
                  let best = "";
                  let bestCount = 0;
                  for (const [word, count] of counts) {
                    if (count > bestCount) {
                      best = word;
                      bestCount = count;
                    }
                  }
                  return best;
                }
            """),
            tests=[
                {"input": ["the cat and the hat"], "expected": "the"},
                {"input": ["Go go GO stop"], "expected": "go"},
                {"input": ["a b"], "expected": "a"},
                {"input": ["b a a b"], "expected": "b"},
                {"input": [""], "expected": ""},
            ],
            wrong=[
                c(r"""
                    function mostFrequentWord(text) {
                      const counts = new Map();
                      for (const word of text.toLowerCase().split(/\s+/).filter(Boolean)) {
                        counts.set(word, (counts.get(word) ?? 0) + 1);
                      }
                      let best = "";
                      let bestCount = 0;
                      for (const [word, count] of counts) {
                        if (count >= bestCount) {
                          best = word;
                          bestCount = count;
                        }
                      }
                      return best;
                    }
                """),
                c(r"""
                    function mostFrequentWord(text) {
                      const counts = new Map();
                      for (const word of text.split(/\s+/).filter(Boolean)) {
                        counts.set(word, (counts.get(word) ?? 0) + 1);
                      }
                      let best = "";
                      let bestCount = 0;
                      for (const [word, count] of counts) {
                        if (count > bestCount) {
                          best = word;
                          bestCount = count;
                        }
                      }
                      return best;
                    }
                """),
            ],
            why=(
                "A Map iterates in insertion order, so a strict > keeps the first word on a tie. "
                "`counts.get(word) ?? 0` starts a new word at zero."
            ),
            difficulty="Medium",
        ),
        PredictCard(
            key="js08-map-keys",
            snippet=c("""
                const obj = {};
                obj[1] = "number key";
                obj["1"] = "string key";
                const map = new Map();
                map.set(1, "number key");
                map.set("1", "string key");
                console.log(Object.keys(obj).length, map.size);
                console.log(map.get(1));
            """),
            output="1 2\nnumber key",
            why=(
                'Object keys are strings, so 1 and "1" are the same key and the second write '
                'replaces the first. A Map keeps the number 1 and the string "1" apart.'
            ),
            source=Source(
                "MDN — Keyed collections",
                MDN_JS + "Guide/Keyed_collections",
                "Map objects, however, have a few more advantages that make them better maps.",
            ),
        ),
        CodeCard(
            key="js08-group-by-map",
            kind="fix",
            title="Fix groupByCategory for any category",
            task=(
                "This `groupByCategory(items)` crashes when a category is called "
                '`"constructor"` or `"toString"`. Fix it by grouping in a `Map`, then return a '
                "plain object with `Object.fromEntries`."
            ),
            starter=c("""
                function groupByCategory(items) {
                  const groups = {};
                  for (const item of items) {
                    if (!groups[item.category]) groups[item.category] = [];
                    groups[item.category].push(item.name);
                  }
                  return groups;
                }
            """),
            solution=c("""
                function groupByCategory(items) {
                  const groups = new Map();
                  for (const item of items) {
                    if (!groups.has(item.category)) groups.set(item.category, []);
                    groups.get(item.category).push(item.name);
                  }
                  return Object.fromEntries(groups);
                }
            """),
            tests=[
                {
                    "input": [
                        [
                            {"name": "Apple", "category": "Fruit"},
                            {"name": "Pear", "category": "Fruit"},
                        ]
                    ],
                    "expected": {"Fruit": ["Apple", "Pear"]},
                },
                {
                    "input": [
                        [
                            {"name": "Vue", "category": "constructor"},
                            {"name": "React", "category": "constructor"},
                        ]
                    ],
                    "expected": {"constructor": ["Vue", "React"]},
                },
                {
                    "input": [[{"name": "x", "category": "toString"}]],
                    "expected": {"toString": ["x"]},
                },
                {"input": [[]], "expected": {}},
            ],
            why=(
                "Every plain object inherits properties like constructor and toString, so "
                '`groups["constructor"]` already exists and isn\'t an array. A Map starts truly '
                "empty."
            ),
            difficulty="Medium",
        ),
    ],
)

# ── 09 ────────────────────────────────────────────────────────────────────

RECURSION = Subdeck(
    name="09 · Recursion",
    summary=(
        "A recursive function calls itself on a smaller piece of the problem and stops at a "
        "base case. It fits nested data — arrays inside arrays, folders inside folders — "
        "whose depth you don't know in advance."
    ),
    sources=[Source("MDN — Functions: recursion", MDN_JS + "Guide/Functions#recursion")],
    cards=[
        CodeCard(
            key="js09-factorial",
            title="factorial(n)",
            task="Write `factorial(n)` recursively: n × (n − 1) × … × 1, with `factorial(0)` = 1.",
            starter=c("""
                function factorial(n) {
                  // TODO: base case, then n * factorial(n - 1)
                  return n;
                }
            """),
            solution=c("""
                function factorial(n) {
                  if (n <= 1) return 1;
                  return n * factorial(n - 1);
                }
            """),
            tests=[
                {"input": [0], "expected": 1},
                {"input": [1], "expected": 1},
                {"input": [5], "expected": 120},
                {"input": [10], "expected": 3628800},
            ],
            wrong=[
                c("""
                    function factorial(n) {
                      if (n === 1) return 1;
                      return n * factorial(n - 1);
                    }
                """),
            ],
            why="Without a base case that covers 0, factorial(0) recurses forever and overflows the stack.",
        ),
        CodeCard(
            key="js09-sum-nested",
            title="sumNested(items)",
            task="Write `sumNested(items)`: add every number in an array whose items can be arrays, nested to any depth.",
            starter=c("""
                function sumNested(items) {
                  let total = 0;
                  // TODO
                  return total;
                }
            """),
            solution=c("""
                function sumNested(items) {
                  let total = 0;
                  for (const item of items) {
                    total += Array.isArray(item) ? sumNested(item) : item;
                  }
                  return total;
                }
            """),
            tests=[
                {"input": [[1, [2, 3], [[4]]]], "expected": 10},
                {"input": [[]], "expected": 0},
                {"input": [[[[]]]], "expected": 0},
                {"input": [[5]], "expected": 5},
            ],
            wrong=[
                c("""
                    function sumNested(items) {
                      return items.flat().reduce((total, n) => total + n, 0);
                    }
                """),
            ],
            why="Each array is the same problem, smaller. `flat()` only removes one level of nesting.",
        ),
        CodeCard(
            key="js09-count-files",
            title="countFiles(folder)",
            task=(
                "A folder is `{ name, files: string[], folders: Folder[] }`. Write "
                "`countFiles(folder)`: the number of files in it and every folder below it."
            ),
            starter=c("""
                function countFiles(folder) {
                  // TODO
                  return folder.files.length;
                }
            """),
            solution=c("""
                function countFiles(folder) {
                  let total = folder.files.length;
                  for (const child of folder.folders) {
                    total += countFiles(child);
                  }
                  return total;
                }
            """),
            tests=[
                {"input": [{"name": "root", "files": ["a"], "folders": []}], "expected": 1},
                {
                    "input": [
                        {
                            "name": "root",
                            "files": ["a", "b"],
                            "folders": [
                                {
                                    "name": "docs",
                                    "files": ["c"],
                                    "folders": [
                                        {"name": "deep", "files": ["d", "e"], "folders": []}
                                    ],
                                },
                                {"name": "empty", "files": [], "folders": []},
                            ],
                        }
                    ],
                    "expected": 5,
                },
            ],
            wrong=[
                c("""
                    function countFiles(folder) {
                      return folder.files.length + folder.folders.reduce((sum, f) => sum + f.files.length, 0);
                    }
                """),
            ],
            why="The base case is a folder with no sub-folders: the loop doesn't run and it returns its own file count.",
        ),
        PredictCard(
            key="js09-trace",
            snippet=c("""
                function countdown(n) {
                  if (n === 0) return "liftoff";
                  return n + " " + countdown(n - 1);
                }
                console.log(countdown(3));
            """),
            output="3 2 1 liftoff",
            why="Each call waits for the smaller call to return, then puts its own number in front.",
        ),
    ],
)

# ── 10 ────────────────────────────────────────────────────────────────────

ERRORS = Subdeck(
    name="10 · Errors: throw, try, catch, finally",
    summary=(
        "`throw` stops the function and travels up the call stack until a `try...catch` "
        "handles it. Catch only where you can do something useful; catching and returning a "
        "default hides the failure. `finally` runs whichever way the block exits."
    ),
    sources=[
        Source(
            "MDN — Control flow and error handling",
            MDN_JS + "Guide/Control_flow_and_error_handling",
        )
    ],
    cards=[
        CodeCard(
            key="js10-parse-age",
            title="parseAge(text)",
            task=(
                "Write `parseAge(text)`: return the age as a number. For anything that isn't a "
                "whole number from 0 to 150 (including empty text), throw a `RangeError` with "
                'the message `"age must be a whole number from 0 to 150"`.'
            ),
            starter=c("""
                function parseAge(text) {
                  // TODO: validate, and throw new RangeError(...) for bad input
                  return Number(text);
                }
            """),
            solution=c("""
                function parseAge(text) {
                  const age = Number(text);
                  if (text.trim() === "" || !Number.isInteger(age) || age < 0 || age > 150) {
                    throw new RangeError("age must be a whole number from 0 to 150");
                  }
                  return age;
                }
            """),
            tests=[
                {"input": ["42"], "expected": 42},
                {"input": ["0"], "expected": 0},
                {"input": ["150"], "expected": 150},
                {"input": ["151"], "expected": throws("RangeError: age must be a whole number")},
                {"input": ["-1"], "expected": throws("RangeError")},
                {"input": ["4.5"], "expected": throws("RangeError")},
                {"input": ["abc"], "expected": throws("RangeError")},
                {"input": [""], "expected": throws("RangeError")},
                {"input": ["   "], "expected": throws("RangeError")},
            ],
            wrong=[
                c("""
                    function parseAge(text) {
                      const age = Number(text);
                      if (text.trim() === "" || !Number.isInteger(age) || age < 0 || age > 150) {
                        throw new Error("age must be a whole number from 0 to 150");
                      }
                      return age;
                    }
                """),
                c("""
                    function parseAge(text) {
                      const age = Number(text);
                      if (!Number.isInteger(age) || age < 0 || age > 150) {
                        throw new RangeError("age must be a whole number from 0 to 150");
                      }
                      return age;
                    }
                """),
            ],
            why=(
                "Throw the most specific built-in error (RangeError for out-of-range values) so "
                'callers can tell failures apart. Number("") is 0, so empty input needs its own check.'
            ),
            source=Source(
                "MDN — Control flow and error handling",
                MDN_JS + "Guide/Control_flow_and_error_handling",
                "You can throw exceptions using the throw statement and handle them using the "
                "try...catch statements.",
            ),
        ),
        PredictCard(
            key="js10-finally",
            snippet=c("""
                function load() {
                  try {
                    console.log("try");
                    return "result";
                  } finally {
                    console.log("finally");
                  }
                }
                console.log(load());
            """),
            output="try\nfinally\nresult",
            why="finally runs on every exit from the try block, return included, before the caller gets the value.",
        ),
        CodeCard(
            key="js10-dont-swallow",
            kind="fix",
            title="Fix readConfig(json)",
            task=(
                "`readConfig(json)` hides broken input by returning `{}`, so callers never find "
                "out the config is invalid. Let a parse error reach the caller, but keep "
                "returning `{}` for empty or blank text."
            ),
            starter=c("""
                function readConfig(json) {
                  try {
                    return JSON.parse(json);
                  } catch {
                    return {};
                  }
                }
            """),
            solution=c("""
                function readConfig(json) {
                  if (json.trim() === "") return {};
                  return JSON.parse(json);
                }
            """),
            tests=[
                {"input": ['{"debug": true}'], "expected": {"debug": True}},
                {"input": [""], "expected": {}},
                {"input": ["   "], "expected": {}},
                {"input": ["{not json"], "expected": throws("SyntaxError")},
            ],
            wrong=[
                c("""
                    function readConfig(json) {
                      return JSON.parse(json);
                    }
                """),
            ],
            why=(
                'Swallowing an error turns "your file is broken" into "you have no settings". '
                "Handle the case you expect (empty text) and let real errors propagate."
            ),
            difficulty="Medium",
        ),
        CodeCard(
            key="js10-custom-error",
            title="ValidationError",
            task=(
                'Make `ValidationError` an error whose `name` is `"ValidationError"`. Then make '
                '`validateUser(user)` throw one with the message `"name is required"` or '
                '`"email is required"` when that field is missing or empty, and return `true` otherwise.'
            ),
            starter=c("""
                function validateUser(user) {
                  // TODO: throw a ValidationError for a missing name or email
                  return true;
                }

                class ValidationError extends Error {
                  // TODO: set this.name
                }
            """),
            solution=c("""
                function validateUser(user) {
                  if (!user.name) throw new ValidationError("name is required");
                  if (!user.email) throw new ValidationError("email is required");
                  return true;
                }

                class ValidationError extends Error {
                  constructor(message) {
                    super(message);
                    this.name = "ValidationError";
                  }
                }
            """),
            tests=[
                {"input": [{"name": "Ada", "email": "ada@example.com"}], "expected": True},
                {
                    "input": [{"email": "ada@example.com"}],
                    "expected": throws("ValidationError: name is required"),
                },
                {
                    "input": [{"name": "Ada"}],
                    "expected": throws("ValidationError: email is required"),
                },
                {
                    "input": [{"name": "", "email": "x@example.com"}],
                    "expected": throws("ValidationError: name is required"),
                },
            ],
            wrong=[
                c("""
                    function validateUser(user) {
                      if (!user.name) throw new ValidationError("name is required");
                      if (!user.email) throw new ValidationError("email is required");
                      return true;
                    }

                    class ValidationError extends Error {}
                """),
            ],
            why=(
                'A subclass of Error inherits message and stack, but its name stays "Error" '
                "unless you set it. Callers can then check `error instanceof ValidationError`."
            ),
            difficulty="Medium",
        ),
    ],
)

# ── 11 ────────────────────────────────────────────────────────────────────

JSON_DECK = Subdeck(
    name="11 · JSON",
    summary=(
        "`JSON.parse` turns text into values and throws a SyntaxError on bad input. "
        "`JSON.stringify` turns values into text: undefined and functions disappear from "
        "objects (null in arrays), Dates become strings, and Maps become `{}`."
    ),
    sources=[Source("MDN — JSON.stringify()", MDN_JS + "Reference/Global_Objects/JSON/stringify")],
    cards=[
        PredictCard(
            key="js11-stringify-drops",
            snippet=c("""
                const data = {
                  name: "Ada",
                  nickname: undefined,
                  greet() {
                    return "hi";
                  },
                  tags: [undefined, "math"],
                  born: new Date(Date.UTC(1815, 11, 10)),
                };
                console.log(JSON.stringify(data));
            """),
            output='{"name":"Ada","tags":[null,"math"],"born":"1815-12-10T00:00:00.000Z"}',
            why=(
                "undefined and functions are not JSON: they are left out of objects and become "
                "null in arrays. A Date is written as its ISO string (and comes back as a string, "
                "not a Date)."
            ),
            source=Source(
                "MDN — JSON.stringify()",
                MDN_JS + "Reference/Global_Objects/JSON/stringify",
                "undefined, Function, and Symbol values are not valid JSON values. If any such "
                "values are encountered during conversion, they are either omitted (when found "
                "in an object) or changed to null (when found in an array).",
            ),
        ),
        CodeCard(
            key="js11-load-settings",
            title="loadSettings(json)",
            task=(
                "Write `loadSettings(json)`: parse the JSON text and return `{ volume, muted }`, "
                "with `volume` 50 and `muted` false when missing. A saved 0 or false must be kept. "
                "Ignore any other fields."
            ),
            starter=c("""
                function loadSettings(json) {
                  const data = JSON.parse(json);
                  // TODO
                  return data;
                }
            """),
            solution=c("""
                function loadSettings(json) {
                  const data = JSON.parse(json);
                  return { volume: data.volume ?? 50, muted: data.muted ?? false };
                }
            """),
            tests=[
                {
                    "input": ['{"volume": 80, "muted": true}'],
                    "expected": {"volume": 80, "muted": True},
                },
                {"input": ["{}"], "expected": {"volume": 50, "muted": False}},
                {"input": ['{"volume": 0}'], "expected": {"volume": 0, "muted": False}},
                {
                    "input": ['{"muted": false, "extra": 1}'],
                    "expected": {"volume": 50, "muted": False},
                },
            ],
            wrong=[
                c("""
                    function loadSettings(json) {
                      const data = JSON.parse(json);
                      return { volume: data.volume || 50, muted: data.muted || false };
                    }
                """),
                c("""
                    function loadSettings(json) {
                      return { volume: 50, muted: false, ...JSON.parse(json) };
                    }
                """),
            ],
            why="Build the result from just the fields you want, with `??` so real 0 and false values survive.",
        ),
        CodeCard(
            key="js11-pretty",
            title="prettyJson(text)",
            task="Write `prettyJson(text)`: reformat compact JSON text with 2-space indentation.",
            starter=c("""
                function prettyJson(text) {
                  // TODO: parse, then stringify with indentation
                  return text;
                }
            """),
            solution=c("""
                function prettyJson(text) {
                  return JSON.stringify(JSON.parse(text), null, 2);
                }
            """),
            tests=[
                {
                    "input": ['{"a":1,"b":[1,2]}'],
                    "expected": '{\n  "a": 1,\n  "b": [\n    1,\n    2\n  ]\n}',
                },
                {"input": ["[]"], "expected": "[]"},
                {"input": ['"hi"'], "expected": '"hi"'},
            ],
            wrong=[
                c("""
                    function prettyJson(text) {
                      return JSON.stringify(text, null, 2);
                    }
                """),
            ],
            why=(
                "The third argument of JSON.stringify is the indentation. Stringifying the text "
                "itself (without parsing) just wraps it in quotes."
            ),
        ),
        PredictCard(
            key="js11-map-to-json",
            snippet=c("""
                const scores = new Map([["ada", 3]]);
                console.log(JSON.stringify(scores));
                console.log(JSON.stringify(Object.fromEntries(scores)));
            """),
            output='{}\n{"ada":3}',
            why="JSON.stringify only writes an object's own enumerable properties, and a Map has none. Convert it first.",
        ),
    ],
)

# ── 12 ────────────────────────────────────────────────────────────────────

CLASSES = Subdeck(
    name="12 · Classes & this",
    summary=(
        "A class bundles state and methods; `#field` makes state truly private. `extends` "
        "inherits and `super(...)` runs the parent constructor. Inside a method `this` is "
        "whatever the method was called on, so pulling a method off its object, or using a "
        "`function` callback, loses it. Arrow functions and `bind` keep it."
    ),
    sources=[
        Source("MDN — Using classes", MDN_JS + "Guide/Using_classes"),
        Source("MDN — this", MDN_JS + "Reference/Operators/this"),
    ],
    cards=[
        CodeCard(
            key="js12-bank-account",
            title="class BankAccount",
            task=(
                "Finish `BankAccount`: keep the balance in a private `#balance` field starting "
                "at 0. `deposit(amount)` and `withdraw(amount)` return the new balance; "
                '`getBalance()` returns it. Throw `RangeError("deposit must be positive")` for a '
                'deposit of 0 or less and `RangeError("insufficient funds")` when withdrawing more '
                "than the balance. Don't change `run`."
            ),
            starter=c("""
                // Test driver: don't change. Runs each [method, ...args] and records the result.
                function run(actions) {
                  const account = new BankAccount("Ada");
                  return actions.map(([method, ...args]) => {
                    if (method === "publicBalance") return account.balance;
                    try {
                      return account[method](...args);
                    } catch (error) {
                      return `${error.name}: ${error.message}`;
                    }
                  });
                }

                class BankAccount {
                  constructor(owner) {
                    this.owner = owner;
                  }

                  // TODO: #balance, deposit(amount), withdraw(amount), getBalance()
                }
            """),
            solution=c("""
                // Test driver: don't change. Runs each [method, ...args] and records the result.
                function run(actions) {
                  const account = new BankAccount("Ada");
                  return actions.map(([method, ...args]) => {
                    if (method === "publicBalance") return account.balance;
                    try {
                      return account[method](...args);
                    } catch (error) {
                      return `${error.name}: ${error.message}`;
                    }
                  });
                }

                class BankAccount {
                  #balance = 0;

                  constructor(owner) {
                    this.owner = owner;
                  }

                  deposit(amount) {
                    if (amount <= 0) throw new RangeError("deposit must be positive");
                    this.#balance += amount;
                    return this.#balance;
                  }

                  withdraw(amount) {
                    if (amount > this.#balance) throw new RangeError("insufficient funds");
                    this.#balance -= amount;
                    return this.#balance;
                  }

                  getBalance() {
                    return this.#balance;
                  }
                }
            """),
            tests=[
                {
                    "input": [[["deposit", 50], ["withdraw", 20], ["getBalance"]]],
                    "expected": [50, 30, 30],
                },
                {"input": [[["withdraw", 1]]], "expected": ["RangeError: insufficient funds"]},
                {"input": [[["deposit", 10], ["withdraw", 10]]], "expected": [10, 0]},
                {
                    "input": [[["deposit", 0], ["deposit", -5]]],
                    "expected": ["RangeError: deposit must be positive"] * 2,
                },
                {"input": [[["deposit", 10], ["publicBalance"]]], "expected": [10, U]},
            ],
            wrong=[
                c("""
                    // Test driver: don't change. Runs each [method, ...args] and records the result.
                    function run(actions) {
                      const account = new BankAccount("Ada");
                      return actions.map(([method, ...args]) => {
                        if (method === "publicBalance") return account.balance;
                        try {
                          return account[method](...args);
                        } catch (error) {
                          return `${error.name}: ${error.message}`;
                        }
                      });
                    }

                    class BankAccount {
                      constructor(owner) {
                        this.owner = owner;
                        this.balance = 0;
                      }

                      deposit(amount) {
                        if (amount <= 0) throw new RangeError("deposit must be positive");
                        this.balance += amount;
                        return this.balance;
                      }

                      withdraw(amount) {
                        if (amount > this.balance) throw new RangeError("insufficient funds");
                        this.balance -= amount;
                        return this.balance;
                      }

                      getBalance() {
                        return this.balance;
                      }
                    }
                """),
                c("""
                    // Test driver: don't change. Runs each [method, ...args] and records the result.
                    function run(actions) {
                      const account = new BankAccount("Ada");
                      return actions.map(([method, ...args]) => {
                        if (method === "publicBalance") return account.balance;
                        try {
                          return account[method](...args);
                        } catch (error) {
                          return `${error.name}: ${error.message}`;
                        }
                      });
                    }

                    class BankAccount {
                      #balance = 0;

                      constructor(owner) {
                        this.owner = owner;
                      }

                      deposit(amount) {
                        if (amount <= 0) throw new RangeError("deposit must be positive");
                        this.#balance += amount;
                        return this.#balance;
                      }

                      withdraw(amount) {
                        if (amount >= this.#balance) throw new RangeError("insufficient funds");
                        this.#balance -= amount;
                        return this.#balance;
                      }

                      getBalance() {
                        return this.#balance;
                      }
                    }
                """),
            ],
            why=(
                "A # field can only be read inside the class: `account.balance` from outside is "
                "undefined. Validate before changing state so a failed call leaves it untouched."
            ),
            source=Source(
                "MDN — Using classes",
                MDN_JS + "Guide/Using_classes",
                "A private field is an identifier prefixed with # (the hash symbol).",
            ),
            difficulty="Medium",
        ),
        PredictCard(
            key="js12-lost-this",
            snippet=c("""
                class Greeter {
                  constructor(name) {
                    this.name = name;
                  }
                  greet() {
                    return `Hi, ${this.name}`;
                  }
                }
                const greeter = new Greeter("Ada");
                const { greet } = greeter;
                try {
                  console.log(greet());
                } catch (error) {
                  console.log(error.name);
                }
                console.log(greet.call(greeter));
                const bound = greeter.greet.bind(greeter);
                console.log(bound());
            """),
            output="TypeError\nHi, Ada\nHi, Ada",
            why=(
                "this is set by how a function is called, not where it was defined. Called on "
                "its own, greet gets this = undefined (class code is strict), so this.name throws. "
                "call() passes this for one call; bind() makes a copy with this fixed."
            ),
            source=Source("MDN — this", MDN_JS + "Reference/Operators/this"),
            difficulty="Medium",
        ),
        CodeCard(
            key="js12-this-in-callback",
            kind="fix",
            title="Fix Cart.total()",
            task=(
                "`total()` throws a TypeError: inside the `function` callback, `this` is not the "
                "cart. Fix it. Don't change `check`."
            ),
            starter=c("""
                // Test driver: don't change.
                function check(prices) {
                  return new Cart(prices).total();
                }

                class Cart {
                  constructor(prices) {
                    this.prices = prices;
                    this.sum = 0;
                  }

                  total() {
                    this.sum = 0;
                    this.prices.forEach(function (price) {
                      this.sum += price;
                    });
                    return this.sum;
                  }
                }
            """),
            solution=c("""
                // Test driver: don't change.
                function check(prices) {
                  return new Cart(prices).total();
                }

                class Cart {
                  constructor(prices) {
                    this.prices = prices;
                    this.sum = 0;
                  }

                  total() {
                    this.sum = 0;
                    this.prices.forEach((price) => {
                      this.sum += price;
                    });
                    return this.sum;
                  }
                }
            """),
            tests=[
                {"input": [[1, 2, 3]], "expected": 6},
                {"input": [[10]], "expected": 10},
                {"input": [[]], "expected": 0},
            ],
            why=(
                "A `function` callback gets its own `this` (undefined here). An arrow function "
                "has no `this` of its own, so it uses the method's."
            ),
            difficulty="Medium",
        ),
        CodeCard(
            key="js12-inheritance",
            title="Circle and Rectangle extend Shape",
            task=(
                'Write `Circle` (constructor `radius`, name `"circle"`, area πr²) and '
                '`Rectangle` (constructor `width, height`, name `"rectangle"`) so both extend '
                "`Shape`, call `super(name)`, and implement `area()`. Don't change `check` or `Shape`."
            ),
            starter=c("""
                // Test driver: don't change.
                function check(specs) {
                  return specs.map(([kind, ...dims]) => {
                    const shape = kind === "circle" ? new Circle(...dims) : new Rectangle(...dims);
                    return [shape instanceof Shape, shape.describe()];
                  });
                }

                class Shape {
                  constructor(name) {
                    this.name = name;
                  }
                  area() {
                    return 0;
                  }
                  describe() {
                    return `${this.name} with area ${this.area().toFixed(2)}`;
                  }
                }

                class Circle extends Shape {
                  // TODO
                }

                class Rectangle extends Shape {
                  // TODO
                }
            """),
            solution=c("""
                // Test driver: don't change.
                function check(specs) {
                  return specs.map(([kind, ...dims]) => {
                    const shape = kind === "circle" ? new Circle(...dims) : new Rectangle(...dims);
                    return [shape instanceof Shape, shape.describe()];
                  });
                }

                class Shape {
                  constructor(name) {
                    this.name = name;
                  }
                  area() {
                    return 0;
                  }
                  describe() {
                    return `${this.name} with area ${this.area().toFixed(2)}`;
                  }
                }

                class Circle extends Shape {
                  constructor(radius) {
                    super("circle");
                    this.radius = radius;
                  }
                  area() {
                    return Math.PI * this.radius ** 2;
                  }
                }

                class Rectangle extends Shape {
                  constructor(width, height) {
                    super("rectangle");
                    this.width = width;
                    this.height = height;
                  }
                  area() {
                    return this.width * this.height;
                  }
                }
            """),
            tests=[
                {
                    "input": [[["circle", 1], ["rectangle", 2, 3]]],
                    "expected": [
                        [True, "circle with area 3.14"],
                        [True, "rectangle with area 6.00"],
                    ],
                },
                {"input": [[["circle", 2]]], "expected": [[True, "circle with area 12.57"]]},
            ],
            wrong=[
                c("""
                    // Test driver: don't change.
                    function check(specs) {
                      return specs.map(([kind, ...dims]) => {
                        const shape = kind === "circle" ? new Circle(...dims) : new Rectangle(...dims);
                        return [shape instanceof Shape, shape.describe()];
                      });
                    }

                    class Shape {
                      constructor(name) {
                        this.name = name;
                      }
                      area() {
                        return 0;
                      }
                      describe() {
                        return `${this.name} with area ${this.area().toFixed(2)}`;
                      }
                    }

                    class Circle {
                      constructor(radius) {
                        this.name = "circle";
                        this.radius = radius;
                      }
                      area() {
                        return Math.PI * this.radius ** 2;
                      }
                      describe() {
                        return `${this.name} with area ${this.area().toFixed(2)}`;
                      }
                    }

                    class Rectangle {
                      constructor(width, height) {
                        this.name = "rectangle";
                        this.width = width;
                        this.height = height;
                      }
                      area() {
                        return this.width * this.height;
                      }
                      describe() {
                        return `${this.name} with area ${this.area().toFixed(2)}`;
                      }
                    }
                """),
            ],
            why=(
                "A subclass must call super() before it uses `this`. It inherits describe() and "
                "overrides area(), so Shape's describe() calls the right area for each shape."
            ),
            difficulty="Medium",
        ),
    ],
)

# ── 13 ────────────────────────────────────────────────────────────────────

ASYNC = Subdeck(
    name="13 · Asynchronous JavaScript",
    summary=(
        "Promise callbacks (microtasks) run as soon as the current code finishes, before "
        "timers. `await` pauses only the async function it is in. Work starts when you create "
        "the promises; `Promise.all` just waits for them all and rejects on the first failure. "
        "`fetch` rejects only on network failure — check `response.ok` yourself."
    ),
    sources=[
        Source("MDN — Using promises", MDN_JS + "Guide/Using_promises"),
        Source("MDN — Promise.all()", MDN_JS + "Reference/Global_Objects/Promise/all"),
        Source(
            "MDN — Window: fetch()", "https://developer.mozilla.org/en-US/docs/Web/API/Window/fetch"
        ),
    ],
    cards=[
        PredictCard(
            key="js13-event-loop",
            snippet=c("""
                console.log("A");
                setTimeout(() => console.log("B"), 0);
                Promise.resolve().then(() => console.log("C"));
                console.log("D");
            """),
            output="A\nD\nC\nB",
            why=(
                "Synchronous code runs first (A, D). Then the microtask queue — promise callbacks "
                "— is emptied (C). Timers run after that, even with a 0 ms delay (B)."
            ),
            source=Source("MDN — Using promises", MDN_JS + "Guide/Using_promises"),
            difficulty="Medium",
        ),
        CodeCard(
            key="js13-load-names",
            kind="fix",
            title="Make loadNames(ids) concurrent",
            task=(
                "`loadNames(ids)` returns the right names but fetches one user at a time. Make "
                "all the `getUser` calls run at once with `Promise.all`, keeping the names in "
                "the order of `ids`. Don't change `check` or `getUser`."
            ),
            starter=c("""
                // Test driver: don't change.
                async function check(ids) {
                  maxInFlight = 0;
                  const names = await loadNames(ids);
                  return { names, concurrent: ids.length < 2 || maxInFlight === ids.length };
                }

                async function loadNames(ids) {
                  const names = [];
                  for (const id of ids) {
                    const user = await getUser(id);
                    names.push(user.name);
                  }
                  return names;
                }

                // Fake API: don't change.
                let inFlight = 0;
                let maxInFlight = 0;
                function getUser(id) {
                  inFlight++;
                  maxInFlight = Math.max(maxInFlight, inFlight);
                  return new Promise((resolve) => {
                    setTimeout(() => {
                      inFlight--;
                      resolve({ id, name: `user${id}` });
                    }, 10);
                  });
                }
            """),
            solution=c("""
                // Test driver: don't change.
                async function check(ids) {
                  maxInFlight = 0;
                  const names = await loadNames(ids);
                  return { names, concurrent: ids.length < 2 || maxInFlight === ids.length };
                }

                async function loadNames(ids) {
                  const users = await Promise.all(ids.map((id) => getUser(id)));
                  return users.map((user) => user.name);
                }

                // Fake API: don't change.
                let inFlight = 0;
                let maxInFlight = 0;
                function getUser(id) {
                  inFlight++;
                  maxInFlight = Math.max(maxInFlight, inFlight);
                  return new Promise((resolve) => {
                    setTimeout(() => {
                      inFlight--;
                      resolve({ id, name: `user${id}` });
                    }, 10);
                  });
                }
            """),
            tests=[
                {
                    "input": [[1, 2, 3]],
                    "expected": {"names": ["user1", "user2", "user3"], "concurrent": True},
                },
                {"input": [[]], "expected": {"names": [], "concurrent": True}},
                {"input": [[5]], "expected": {"names": ["user5"], "concurrent": True}},
            ],
            why=(
                "`await` in a loop waits for each request before starting the next. Start them "
                "all with map, then await Promise.all, which keeps results in input order."
            ),
            source=Source(
                "MDN — Promise.all()",
                MDN_JS + "Reference/Global_Objects/Promise/all",
                "This returned promise fulfills when all of the input's promises fulfill "
                "(including when an empty iterable is passed), with an array of the fulfillment values.",
            ),
            difficulty="Medium",
        ),
        CodeCard(
            key="js13-fetch-ok",
            kind="fix",
            title="Fix getJson(url)",
            task=(
                "`getJson(url)` returns the error page's body when the server answers 404 or "
                '500. Throw `new Error(`HTTP ${status}`)` (e.g. `"HTTP 404"`) when the response '
                "isn't ok. Don't change the fake `fetch`."
            ),
            starter=c("""
                async function getJson(url) {
                  const response = await fetch(url);
                  return response.json();
                }

                // Fake server for the tests: don't change.
                async function fetch(url) {
                  const routes = {
                    "/users/1": { status: 200, body: { id: 1, name: "Ada" } },
                    "/down": { status: 500, body: { error: "server error" } },
                  };
                  const route = routes[url] ?? { status: 404, body: { error: "not found" } };
                  return {
                    ok: route.status >= 200 && route.status < 300,
                    status: route.status,
                    json: async () => route.body,
                  };
                }
            """),
            solution=c("""
                async function getJson(url) {
                  const response = await fetch(url);
                  if (!response.ok) throw new Error(`HTTP ${response.status}`);
                  return response.json();
                }

                // Fake server for the tests: don't change.
                async function fetch(url) {
                  const routes = {
                    "/users/1": { status: 200, body: { id: 1, name: "Ada" } },
                    "/down": { status: 500, body: { error: "server error" } },
                  };
                  const route = routes[url] ?? { status: 404, body: { error: "not found" } };
                  return {
                    ok: route.status >= 200 && route.status < 300,
                    status: route.status,
                    json: async () => route.body,
                  };
                }
            """),
            tests=[
                {"input": ["/users/1"], "expected": {"id": 1, "name": "Ada"}},
                {"input": ["/missing"], "expected": throws("HTTP 404")},
                {"input": ["/down"], "expected": throws("HTTP 500")},
            ],
            wrong=[
                c("""
                    async function getJson(url) {
                      const response = await fetch(url);
                      if (response.status === 404) throw new Error("HTTP 404");
                      return response.json();
                    }

                    // Fake server for the tests: don't change.
                    async function fetch(url) {
                      const routes = {
                        "/users/1": { status: 200, body: { id: 1, name: "Ada" } },
                        "/down": { status: 500, body: { error: "server error" } },
                      };
                      const route = routes[url] ?? { status: 404, body: { error: "not found" } };
                      return {
                        ok: route.status >= 200 && route.status < 300,
                        status: route.status,
                        json: async () => route.body,
                      };
                    }
                """),
            ],
            why=(
                "An HTTP error is still a successful fetch: the promise resolves with the "
                "response. `response.ok` is true only for 200–299, so check it before reading the body."
            ),
            source=Source(
                "MDN — Window: fetch()",
                "https://developer.mozilla.org/en-US/docs/Web/API/Window/fetch",
                "A fetch() promise only rejects when the request fails, for example, because of "
                "a badly-formed request URL or a network error. A fetch() promise does not reject "
                "if the server responds with HTTP status codes that indicate errors (404, 504, etc.).",
            ),
            difficulty="Medium",
        ),
        PredictCard(
            key="js13-all-vs-allsettled",
            snippet=c("""
                const ok = Promise.resolve("ok");
                const fail = Promise.reject(new Error("boom"));
                try {
                  await Promise.all([ok, fail]);
                } catch (error) {
                  console.log("all:", error.message);
                }
                const results = await Promise.allSettled([ok, fail]);
                console.log("allSettled:", results.map((r) => r.status).join(","));
            """),
            output="all: boom\nallSettled: fulfilled,rejected",
            why=(
                "Promise.all rejects with the first rejection. Promise.allSettled always "
                "fulfills, with a status for each promise. Neither one starts the work: the "
                "promises were already running when created."
            ),
            source=Source(
                "MDN — Promise.all()",
                MDN_JS + "Reference/Global_Objects/Promise/all",
                "It rejects when any of the input's promises rejects, with this first rejection reason.",
            ),
            difficulty="Medium",
        ),
    ],
)

# ── 14 ────────────────────────────────────────────────────────────────────

MODULES = Subdeck(
    name="14 · Modules",
    summary=(
        "Each file is a module with its own scope. `export` makes a name available; "
        "`import { name }` takes a named export (renamed with `as`), `import name` takes the "
        "default export. A module runs once, so every importer shares its state."
    ),
    sources=[Source("MDN — JavaScript modules", MDN_JS + "Guide/Modules")],
    cards=[
        PredictCard(
            key="js14-default-and-named",
            files={
                "math.js": c("""
                export default function add(a, b) {
                  return a + b;
                }
                export const PI = 3.14;
            """)
            },
            snippet=c("""
                import plus, { PI } from "./math.js";
                console.log(plus(2, 3), PI);
            """),
            output="5 3.14",
            why=(
                "The default export is imported without braces, under any name you choose. "
                "Named exports go in braces and must match the exported name."
            ),
            source=Source(
                "MDN — JavaScript modules",
                MDN_JS + "Guide/Modules",
                "Each module can have up to one default export.",
            ),
        ),
        PredictCard(
            key="js14-missing-named-export",
            files={
                "math.js": c("""
                export default function add(a, b) {
                  return a + b;
                }
            """)
            },
            snippet=c("""
                import { add } from "./math.js";
                console.log(add(2, 3));
            """),
            output="SyntaxError: The requested module './math.js' does not provide an export named 'add'",
            why=(
                "add is the default export, not a named one. Imports are checked before any code "
                'runs, so nothing is printed. Write `import add from "./math.js"`.'
            ),
            source=Source("MDN — JavaScript modules", MDN_JS + "Guide/Modules"),
            difficulty="Medium",
        ),
        PredictCard(
            key="js14-shared-state",
            files={
                "counter.js": c("""
                let count = 0;
                export function increment() {
                  count += 1;
                  return count;
                }
            """)
            },
            snippet=c("""
                import { increment as next } from "./counter.js";
                import { increment } from "./counter.js";
                next();
                next();
                console.log(increment());
            """),
            output="3",
            why="A module is evaluated once. Both imports are the same function, closing over the same count.",
            source=Source("MDN — JavaScript modules", MDN_JS + "Guide/Modules"),
            difficulty="Medium",
        ),
    ],
)


PART1 = Part(
    name="Part 1 · JavaScript Fundamentals",
    summary=(
        "Write and read real JavaScript: values and types, conditionals, loops, strings, "
        "functions and closures, arrays, objects, Map and Set, recursion, errors, JSON, "
        "classes, async code and modules."
    ),
    subdecks=[
        VALUES,
        OPERATORS,
        LOOPS,
        STRINGS,
        FUNCTIONS,
        ARRAYS,
        OBJECTS,
        COLLECTIONS,
        RECURSION,
        ERRORS,
        JSON_DECK,
        CLASSES,
        ASYNC,
        MODULES,
    ],
)

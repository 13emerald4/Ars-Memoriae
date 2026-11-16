"""Part 1 · JavaScript Fundamentals — guide configuration."""

from common import COMMON_DEVIATIONS, TODAY, c, note

FILENAME = "part1-javascript-fundamentals"
TITLE = "Part 1 · JavaScript Fundamentals"
SUBTITLE = "A Socratic study guide to the 64 cards of Part 1 of “JavaScript & TypeScript: Zero to Mastery”"
META_QUESTION = "What do you need to know to write JavaScript that does what you mean?"
META_DECOMPOSITION = (
    "Part A asks what a program is made of (values, names, comparisons); B, how code repeats and "
    "handles text; C, how logic is packaged into functions; D, how many values are held (arrays, "
    "objects, Map and Set); E, how nested problems are solved and failures survived (recursion, errors, "
    "JSON); F, how bigger programs fit together (classes, asynchronous code, modules). Every section "
    "heading is a question, answered in its first sentence. The Card-by-Card Solution Guide then works "
    "every card in the deck."
)

GROUPS = [
    ("A. What is a program made of?", "Values, the names that point at them, and how they are compared.", ["c01", "c02"]),
    ("B. How does code repeat, and how is text handled?", "Loops, and the string methods that loops often drive.", ["c03", "c04"]),
    ("C. How do you package logic?", "Functions, hoisting and closures.", ["c05"]),
    ("D. How do you hold many values?", "Arrays, objects, Maps and Sets.", ["c06", "c07", "c08"]),
    ("E. How do you solve nested problems and survive failure?", "Recursion, errors and JSON.", ["c09", "c10", "c11"]),
    ("F. How do bigger programs fit together?", "Classes, asynchronous code and modules.", ["c12", "c13", "c14"]),
]

SYNTHESIS = r"""
Writing JavaScript that does what you mean takes three kinds of knowledge, and the Parts supply them in order.

\textbf{What the values really are (A).} Most surprises in this Part come from a value being something other than you assumed: \code{typeof null} is \code{"object"}, \code{0 == ""} is true, \code{config.port || 3000} throws away a real \code{0}, and a \code{const} object can still change. Knowing the seven primitive types, references, truthiness and the three logical operators removes those surprises at the source.

\textbf{How control moves (B, C, E).} Loops decide how often code runs and when it stops (\code{<=} versus \code{<}, \code{return} at the first match). Functions decide what code can see: closures keep private state, and recursion turns nested data into the same small problem. Errors decide where control goes when something fails: throw early, catch only where you can act, and let \code{finally} clean up.

\textbf{How data and programs are shaped (D, F).} Arrays, objects, Maps and Sets each fit a different job, and each has one trap worth knowing: \code{sort} compares text, spread copies one level, plain objects inherit keys. Classes bundle data with behaviour but tie \code{this} to the call; promises let one task wait without stopping the rest; modules share code by name and run once.

\textbf{The strongest objection} is that you could learn all of this by running code and fixing the errors. The answer: the traps in this Part mostly raise \emph{no} error. \code{forEach} quietly returns \code{undefined}, \code{||} quietly replaces \code{0}, \code{fetch} quietly resolves on a 404, and \code{sort} quietly misorders numbers. Code that runs and gives a wrong answer is only caught by knowing what it should do---which is what the cards drill.
"""

TEST_QUESTIONS = [
    ("What does `typeof null` return, and how should you test for `null`?", "c01"),
    ("Why does `config.port || 3000` break for port 0, and what fixes it?", "c02"),
    ("A loop must add the numbers 1 to n. Which comparison belongs in its test, and what goes wrong with the other one?", "c03"),
    ('Why is `"5" + 3` equal to `"53"` while `"5" - 3` is `2`?', "c04"),
    ("How do two counters made by the same function keep separate counts?", "c05"),
    ("Why does `[10, 9, 100].sort()` give 10, 100, 9, and how do you sort numbers?", "c06"),
    ("When is a destructuring default not used?", "c07"),
    ('Why can `{}["constructor"]` break a grouping function, and what avoids it?', "c08"),
    ("Which two kinds of input must every recursive function handle?", "c09"),
    ("Why is catching an error and returning `{}` usually wrong?", "c10"),
    ("What happens to `undefined` when `JSON.stringify` meets it in an object? In an array?", "c11"),
    ("Why does a method pulled off its object lose `this`, and what restores it?", "c12"),
    ("Does `Promise.all` start the work it waits for? What does it return?", "c13"),
    ("What happens when a file imports a named export that does not exist?", "c14"),
]

SNIPPETS = {
    "c01-typeof": {"code": c("""
        console.log(typeof 3.5, typeof "hi", typeof true);
        console.log(typeof {}, typeof [], Array.isArray([]));
        console.log(typeof null, null === null);
    """), "out": "number string boolean\nobject object true\nobject true"},
    "c01-numbers": {"code": c("""
        console.log(Number("42"), Number("12abc"), Number(""));
        console.log(parseInt("12abc", 10), Number.isInteger(3.5));
    """), "out": "42 NaN 0\n12 false"},
    "c01-const": {"code": c("""
        const team = ["Ada"];
        team.push("Grace");
        console.log(team.length);
    """), "out": "2"},
    "c01-sharing": {"code": c("""
        function addTag(list) {
          list.push("new");
          list = ["other"];
        }
        const tags = ["old"];
        addTag(tags);
        console.log(tags.join(","));
    """), "out": "old,new"},
    "c02-equality": {"code": c("""
        console.log(1 == "1", 1 === "1");
        console.log(null == undefined, null == 0);
        console.log(NaN === NaN, Number.isNaN(NaN));
    """), "out": "true false\ntrue false\nfalse true"},
    "c02-branches": {"code": c("""
        function label(temp) {
          if (temp >= 30) return "hot";
          if (temp >= 15) return "mild";
          return "cold";
        }
        console.log(label(30), label(29), label(14));
    """), "out": "hot mild cold"},
    "c02-nullish": {"code": c("""
        const saved = 0;
        console.log(saved || 10, saved ?? 10, null ?? 10);
    """), "out": "10 0 10"},
    "c03-for": {"code": c("""
        let total = 0;
        for (let i = 1; i <= 4; i++) total += i;
        console.log(total, 9 % 3 === 0, 10 % 3);
    """), "out": "10 true 1"},
    "c03-forof": {"code": c("""
        for (const ch of "hey") console.log(ch.toUpperCase());
    """), "out": "H\nE\nY"},
    "c03-break": {"code": c("""
        for (const n of [3, 8, 1, 9]) {
          if (n > 5) {
            console.log("first big:", n);
            break;
          }
        }
    """), "out": "first big: 8"},
    "c03-let": {"code": c("""
        const fns = [];
        for (let i = 0; i < 3; i++) fns.push(() => i);
        console.log(fns.map((f) => f()).join(" "));
    """), "out": "0 1 2"},
    "c04-immutable": {"code": c("""
        const word = "hello";
        const shout = word.toUpperCase();
        console.log(word, shout, word.slice(1, 3));
    """), "out": "hello HELLO el"},
    "c04-split": {"code": c(r"""
        const parts = "  a   b ".trim().split(/\s+/);
        console.log(parts.length, parts.join("-"));
        console.log([..."abc"].reverse().join(""));
    """), "out": "2 a-b\ncba"},
    "c04-plus": {"code": c("""
        console.log("5" + 3, "5" - 3, 1 + 2 + "3");
    """), "out": "53 2 33"},
    "c05-hoisting": {"code": c("""
        console.log(double(4));
        function double(n) {
          return n * 2;
        }
    """), "out": "8"},
    "c05-closure": {"code": c("""
        function makeGreeter(greeting) {
          return (name) => `${greeting}, ${name}`;
        }
        const hi = makeGreeter("Hi");
        const yo = makeGreeter("Yo");
        console.log(hi("Ada"), yo("Ada"));
    """), "out": "Hi, Ada Yo, Ada"},
    "c05-rest": {"code": c("""
        function count(...items) {
          return items.length;
        }
        console.log(count(), count("a", "b"));
    """), "out": "0 2"},
    "c06-map": {"code": c("""
        const prices = [5, 20, 8];
        const big = prices.filter((p) => p > 6).map((p) => p * 2);
        console.log(big.join(" "), prices.join(" "));
    """), "out": "40 16 5 20 8"},
    "c06-reduce": {"code": c("""
        const add = (sum, n) => sum + n;
        console.log([4, 6].reduce(add, 0), [].reduce(add, 0));
        try {
          [].reduce(add);
        } catch (error) {
          console.log(error.name);
        }
    """), "out": "10 0\nTypeError"},
    "c06-foreach": {"code": c("""
        const result = [1, 2].forEach((n) => n * 2);
        console.log(result, [1, 2].map((n) => n * 2).join(","));
    """), "out": "undefined 2,4"},
    "c06-sort": {"code": c("""
        console.log([10, 9, 100].sort().join(" "));
        console.log([10, 9, 100].sort((a, b) => a - b).join(" "));
    """), "out": "10 100 9\n9 10 100"},
    "c06-copy": {"code": c("""
        const a = [1];
        const b = a;
        const copy = [...a];
        b.push(2);
        console.log(a.length, copy.length, a === b);
    """), "out": "2 1 true"},
    "c07-destructure": {"code": c("""
        const { name, role = "guest" } = { name: "Ada", role: null };
        const { title = "none" } = {};
        console.log(name, role, title);
    """), "out": "Ada null none"},
    "c07-spread": {"code": c("""
        const base = { theme: "light", tags: ["a"] };
        const mine = { ...base, theme: "dark" };
        mine.tags.push("b");
        console.log(mine.theme, base.theme, base.tags.join(""));
    """), "out": "dark light ab"},
    "c07-in": {"code": c("""
        const box = { count: 0 };
        console.log("count" in box, Boolean(box.count), "size" in box);
    """), "out": "true false false"},
    "c07-optional": {"code": c("""
        const user = { profile: null };
        console.log(user.profile?.email ?? "no email");
    """), "out": "no email"},
    "c08-set": {"code": c("""
        const tags = new Set(["js", "ts", "js"]);
        console.log(tags.size, [...tags].join(","));
    """), "out": "2 js,ts"},
    "c08-map": {"code": c("""
        const counts = new Map();
        for (const w of ["a", "b", "a"]) {
          counts.set(w, (counts.get(w) ?? 0) + 1);
        }
        console.log(counts.get("a"), counts.size);
    """), "out": "2 2"},
    "c08-inherited": {"code": c("""
        const groups = {};
        console.log(typeof groups["constructor"]);
        console.log(new Map().has("constructor"));
    """), "out": "function\nfalse"},
    "c09-base": {"code": c("""
        function forever(n) {
          return forever(n + 1);
        }
        try {
          forever(0);
        } catch (error) {
          console.log(error.name);
        }
    """), "out": "RangeError"},
    "c09-nested": {"code": c("""
        function depth(item) {
          if (!Array.isArray(item)) return 0;
          return 1 + Math.max(0, ...item.map(depth));
        }
        console.log(depth([1, [2, [3]]]), depth(7));
    """), "out": "3 0"},
    "c09-order": {"code": c("""
        function nest(n) {
          if (n === 0) return "core";
          const inner = nest(n - 1);
          console.log("back in", n);
          return `(${inner})`;
        }
        console.log(nest(2));
    """), "out": "back in 1\nback in 2\n((core))"},
    "c10-throw": {"code": c("""
        function checkAge(age) {
          if (age < 0) throw new RangeError("negative age");
          return age;
        }
        try {
          checkAge(-1);
        } catch (error) {
          console.log(`${error.name}: ${error.message}`);
        }
    """), "out": "RangeError: negative age"},
    "c10-catch": {"code": c("""
        try {
          JSON.parse("{oops");
        } catch (error) {
          console.log(error.name);
        }
    """), "out": "SyntaxError"},
    "c10-finally": {"code": c("""
        function f() {
          try {
            return "value";
          } finally {
            console.log("cleanup");
          }
        }
        console.log(f());
    """), "out": "cleanup\nvalue"},
    "c10-custom": {"code": c("""
        class NotFound extends Error {
          name = "NotFound";
        }
        console.log(String(new NotFound("no user")));
    """), "out": "NotFound: no user"},
    "c11-parse": {"code": c("""
        const data = JSON.parse('{"volume": 0}');
        console.log(data.volume ?? 50, data.muted ?? false);
    """), "out": "0 false"},
    "c11-stringify": {"code": c("""
        const value = { a: 1, b: undefined, c: [undefined], m: new Map() };
        console.log(JSON.stringify(value));
        console.log(JSON.stringify([1], null, 2).split("\\n").length);
    """), "out": '{"a":1,"c":[null],"m":{}}\n3'},
    "c12-class": {"code": c("""
        class Point {
          constructor(x, y) { this.x = x; this.y = y; }
          sum() { return this.x + this.y; }
        }
        console.log(new Point(2, 3).sum());
    """), "out": "5"},
    "c12-private": {"code": c("""
        class Safe {
          #code = 42;
          check(n) { return n === this.#code; }
        }
        const safe = new Safe();
        console.log(safe.check(42), safe.code);
    """), "out": "true undefined"},
    "c12-this": {"code": c("""
        const counter = { n: 1, get() { return this.n; } };
        const loose = counter.get;
        try {
          loose();
        } catch (error) {
          console.log(error.name);
        }
        console.log(loose.call(counter), loose.bind(counter)());
    """), "out": "TypeError\n1 1"},
    "c12-extends": {"code": c("""
        class Animal {
          constructor(name) { this.name = name; }
          describe() { return `${this.name}: ${this.sound()}`; }
          sound() { return "..."; }
        }
        class Dog extends Animal {
          sound() { return "woof"; }
        }
        console.log(new Dog("Rex").describe());
    """), "out": "Rex: woof"},
    "c13-await": {"code": c("""
        async function slowDouble(n) {
          await null;
          return n * 2;
        }
        slowDouble(4).then((v) => console.log("got", v));
        console.log("first");
    """), "out": "first\ngot 8"},
    "c13-order": {"code": c("""
        setTimeout(() => console.log("timer"), 0);
        Promise.resolve().then(() => console.log("promise"));
        console.log("sync");
    """), "out": "sync\npromise\ntimer"},
    "c13-all": {"code": c("""
        const wait = (ms, v) => new Promise((r) => setTimeout(() => r(v), ms));
        const start = Date.now();
        const both = await Promise.all([wait(100, "a"), wait(100, "b")]);
        console.log(both.join(""), Date.now() - start < 190);
    """), "out": "ab true"},
    "c13-fetch": {"code": c("""
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
    """), "run": False},
    "c14-import": {
        "files": {"shapes.js": "export const sides = { triangle: 3 };\nexport default function area(w, h) {\n  return w * h;\n}\n"},
        "code": c("""
            import area, { sides } from "./shapes.js";
            console.log(area(2, 3), sides.triangle);
        """),
        "display": c("""
            // shapes.js
            export const sides = { triangle: 3 };
            export default function area(w, h) {
              return w * h;
            }
            // main.js
            import area, { sides } from "./shapes.js";
            console.log(area(2, 3), sides.triangle);
        """),
        "out": "6 3",
    },
    "c14-once": {
        "files": {"log.js": "export const lines = [];\nexport function log(x) {\n  lines.push(x);\n}\n"},
        "code": c("""
            import { log, lines } from "./log.js";
            import { log as record } from "./log.js";
            log("a");
            record("b");
            console.log(lines.join(","));
        """),
        "display": c("""
            // log.js
            export const lines = [];
            export function log(x) {
              lines.push(x);
            }
            // main.js
            import { log, lines } from "./log.js";
            import { log as record } from "./log.js";
            log("a");
            record("b");
            console.log(lines.join(","));
        """),
        "out": "a,b",
    },
}

R = "Run it, then change one line and predict again."

CARDS = {
    # 01
    "js01-typeof": note(["c01"], ["c01-types"],
        "Evaluate each `typeof` on its own line, remembering the two exceptions.",
        "`typeof` always returns one of a few fixed type names, as a string.",
        "Nothing is stored; each value is made and thrown away.",
        "number, string, null, array (an object), undefined, bigint.",
        'Answering "null" for `typeof null` or "array" for `typeof []`.', R,
        '`typeof null` and `typeof []` are both "object".'),
    "js01-describe-type": note(["c01"], ["c01-types"],
        "Test `=== null` first, then `Array.isArray`, then fall back to `typeof`.",
        "Each special case returns before the next check sees the value.",
        "No state: one value in, one string out.",
        "Any value in; a string out.",
        'Using `!value` or `== null` also catches `0`, `""` or `undefined`.',
        '`null`, `[1, 2]`, `{}`, `""`, `0` and `undefined` must each keep their own answer.',
        "Testing for null with `!value` mislabels 0 and the empty string."),
    "js01-parse-count": note(["c01"], ["c01-numbers"],
        "Reject blank text, convert with `Number`, and accept the result only if `Number.isInteger` says so.",
        "Only text that is entirely a whole number is accepted.",
        "One local number `n`.",
        "string in; number or `null` out.",
        '`parseInt` accepts "12abc"; plain `Number` turns blank text into 0.',
        '"007", "-4", "", "   ", "3.5", "12abc".',
        '`Number("")` is 0, so blank input needs its own check.'),
    "js01-const": note(["c01"], ["c01-names"],
        "Line 2 changes a property (allowed); the reassignment inside `try` throws, so `catch` prints the error's name.",
        "A `const` name always points at the same object.",
        "One object, whose `theme` changes from dark to light.",
        "object, string, TypeError.",
        "Believing `const` freezes the object, or that the reassignment is a SyntaxError.", R,
        "`const` blocks reassignment, not changes inside the object."),
    "js01-pass-by-sharing": note(["c01"], ["c01-sharing"],
        "Follow the reference: the property change reaches the caller's object; the reassignment only moves the local name.",
        "The caller's `person` keeps pointing at the same object throughout.",
        "Two objects: the original (renamed Grace) and a new one (Linus) that nothing outside sees.",
        "objects holding strings.",
        "Answering Linus (the caller sees the reassignment) or Ada (nothing is shared).",
        "Run it, and log `user.name` inside the function after each line.",
        "Reassigning a parameter never reaches the caller; changing a property through it does."),
    "js01-tdz": note(["c01"], ["c01-names"],
        "`var hoisted` exists as `undefined` from the top; `early` is in its temporal dead zone until its line runs.",
        "A `let` name cannot be read before its declaration runs.",
        "Both names exist from the start; only the `var` has a value (`undefined`).",
        'string ("undefined"), ReferenceError.',
        'Expecting `typeof hoisted` to be "number", or `early` to print undefined.',
        "Run it, then move `let early = 1;` to the top and run again.",
        "Before its line, a `var` reads as undefined but a `let` throws."),
    # 02
    "js02-equality": note(["c02"], ["c02-equality"],
        "For each `==`, convert both sides first; for `===`, different types are never equal.",
        "`===` never converts; `NaN` is never equal to anything.",
        "Nothing stored.",
        'number, string ("" becomes 0), null, undefined, NaN.',
        "Assuming `null == 0` (it is false) or `NaN === NaN` (also false).", R,
        "`null == undefined` is true, but `null == 0` is false."),
    "js02-port-default": note(["c02"], ["c02-logical", "c02-truthy"],
        "Replace `||` with `??`, which falls back only for `null` or `undefined`.",
        "A port that is present, including 0, is returned unchanged.",
        "No state.",
        "object in; number out.",
        "`||` (and a truthiness ternary) replace 0 as if it were missing.",
        "8080, 0, a missing port, and `null`.",
        "`||` treats a real 0 as missing."),
    "js02-letter-grade": note(["c02"], ["c02-branches"],
        "Return early from the highest band down: 90, then 80, then 70, else F.",
        "Each later `if` only sees scores below the earlier thresholds.",
        "No state.",
        "number in; one-letter string out.",
        "`>` instead of `>=` moves 90, 80 and 70 down a band; checking low bands first catches everything.",
        "Every boundary: 90, 89, 80, 79, 70, 69, plus 0 and 95.",
        "Using `>` makes a score of exactly 90 a B."),
    "js02-logical-operands": note(["c02"], ["c02-logical"],
        "For each line apply the rule: `||` gives the first truthy value (or the last), `&&` the first falsy (or the last), `??` the right side only for null/undefined.",
        "These operators return an operand, never a fresh boolean.",
        "Nothing stored.",
        "strings, numbers, null.",
        "Answering true/false, or thinking `0 ?? \"zero\"` gives \"zero\".", R,
        '`0 ?? "zero"` is 0, because 0 is not null or undefined.'),
    "js02-count-truthy": note(["c02"], ["c02-truthy"],
        "`values.filter(Boolean).length` keeps exactly the truthy values.",
        "Only the eight falsy values are dropped.",
        "A filtered copy of the array.",
        "array of anything in; number out.",
        'Counting non-null values instead of truthy ones, or comparing with `!= false` (which drops `[]` and "0").',
        '`[]`, `{}`, "0" and "false" (truthy) next to 0, "", null and false.',
        '"0", "false", [] and {} are truthy.'),
    # 03
    "js03-sum-to": note(["c03"], ["c03-for"],
        "Loop `i` from 1 to n inclusive, adding each `i` to a running total.",
        "After each lap, `total` is the sum of 1..i.",
        "Two numbers: `i` and `total`.",
        "number in; number out.",
        "`i < n` stops one short (off by one).",
        "0, 1, 5 and 100.",
        "`<` instead of `<=` drops the last number."),
    "js03-count-vowels": note(["c03"], ["c03-forof", "c04-immutable"],
        "Lower-case the text once, walk it with `for...of`, and count characters found in \"aeiou\".",
        "`count` equals the vowels seen so far.",
        "One counter; the lower-cased copy of the text.",
        "string in; number out.",
        "Forgetting to lower-case, so capitals are missed.",
        '"AEIOU", "rhythm", "" and a sentence with capitals.',
        "Upper-case vowels are skipped unless you lower-case first."),
    "js03-fizzbuzz": note(["c03"], ["c03-for"],
        "Loop 1..n; test divisibility by 15 first, then 3, then 5, else push the number as a string.",
        "The output array has exactly n entries, in order.",
        "One array growing by one string per lap.",
        "number in; array of strings out.",
        'Testing 3 before 15 makes 15 "Fizz"; pushing the number itself gives the wrong type.',
        "5, 15 and 0.",
        "Check the both-divisible case before the single ones."),
    "js03-first-index-over": note(["c03"], ["c03-exit"],
        "Walk the indexes and `return i` at the first number greater than the limit; return -1 after the loop.",
        "Every index before `i` held a number that was not greater than the limit.",
        "Only the loop index.",
        "array of numbers and a number in; number out.",
        "Recording matches without returning gives the last match; `>=` accepts equal numbers.",
        "A match in the middle, none at all, an empty array, and a number equal to the limit.",
        "Without an early `return`, the loop finds the last match, not the first."),
    "js03-closure-in-loop": note(["c03"], ["c03-let"],
        "With `var` there is one `i`, which ends at 3; with `let` each lap gets its own `j`.",
        "Each arrow function reads the variable it closes over when it is finally called.",
        "One shared `i` versus three separate `j` variables.",
        "functions and numbers.",
        'Answering "0 1 2" for both loops.', R,
        "`var` in a loop gives every function the same, final value."),
    "js03-for-in-vs-of": note(["c03"], ["c03-forin", "c03-forof"],
        "`for...in` lists keys (as strings), including the extra `label` property; `for...of` lists values.",
        "`for...of` on an array yields only its items.",
        "One array with an extra named property.",
        "strings (keys) and numbers (values).",
        'Forgetting that `label` appears, or that the keys are the strings "0" and "1".', R,
        "`for...in` on an array also visits added and inherited properties."),
    # 04
    "js04-capitalize": note(["c04"], ["c04-immutable"],
        'Return "" for empty input; otherwise upper-case `word[0]` and lower-case `word.slice(1)`.',
        "The original string is never changed; a new one is returned.",
        "Two new strings joined together.",
        "string in; string out.",
        '`word[0]` is undefined for "", so calling `toUpperCase` on it throws.',
        '"hello", "wORLD", "a" and "".',
        "The empty string has no first character."),
    "js04-palindrome": note(["c04"], ["c04-split", "c04-immutable"],
        "Lower-case, strip everything but letters and digits, then compare with the reversed copy.",
        "Only letters and digits are compared, in one case.",
        "The cleaned string and its reversed copy.",
        "string in; boolean out.",
        "Skipping the lower-casing or the clean-up makes \"Race Car\" fail.",
        '"racecar", "Race Car", "A man, a plan, a canal: Panama", "hello" and "".',
        "Strings have no reverse(): spread to an array, reverse, join."),
    "js04-initials": note(["c04"], ["c04-split"],
        "Trim, split on `/\\s+/`, take each part's first letter upper-cased plus a dot, and join.",
        "Every part from the split is a non-empty word.",
        "An array of words, then an array of initials.",
        "string in; string out.",
        "`split(\" \")` leaves empty strings where spaces repeat, and `part[0]` is then undefined.",
        "Two names, three names, extra spaces, and a single name.",
        "Splitting on one space breaks on repeated spaces."),
    "js04-plus-coercion": note(["c04"], ["c04-plus"],
        "For each `+`, ask whether either side is a string; for `-` and `*`, convert to numbers. Go left to right.",
        "`+` joins as soon as one side is a string.",
        "Nothing stored.",
        "strings and numbers.",
        'Answering 8 for `"5" + 3`, or "123" mistaken for 6 or "33".', R,
        "`1 + 2 + \"3\"` adds first (3), then joins: \"33\"."),
    "js04-immutable": note(["c04"], ["c04-immutable"],
        "Each method returns a new string; `word` itself is unchanged.",
        "A string never changes after it is made.",
        "Three separate strings.",
        "strings.",
        "Thinking `toUpperCase` or `replace` changed `word`.", R,
        "String methods return new strings; the original stays."),
    # 05
    "js05-hoisting": note(["c05"], ["c05-define"],
        "The declaration is usable before its line; the `const` function is not, so calling it throws.",
        "A `const` name cannot be used before its line runs.",
        "Both names exist from the start; only the declaration has a function yet.",
        "string and ReferenceError.",
        "Expecting both calls to work, or the error to be a TypeError.", R,
        "Function declarations are hoisted; function expressions in `const` are not."),
    "js05-make-counter": note(["c05"], ["c05-closures"],
        "Declare `let count = start` inside `makeCounter` and return methods that update and read it.",
        "Each counter's `count` changes only through its own methods.",
        "One `count` variable per call to `makeCounter`.",
        "number in; object with two functions out.",
        "A `count` declared outside the function is shared by every counter.",
        "Two counters stepped in turn must not affect each other.",
        "Put the state inside the outer function, not beside it.", terms=["closure"]),
    "js05-once": note(["c05"], ["c05-closures"],
        "Keep a `done` flag and a `result` in the closure; call `fn` only while `done` is false.",
        "`fn` runs at most once; every call returns the first result.",
        "Two closed-over variables: `done` and `result`.",
        "function in; function out.",
        "Using `result === undefined` as the flag calls `fn` again when it returns undefined.",
        "Several calls; a function that returns undefined; no calls at all.",
        "A result of undefined is not \"not called yet\"."),
    "js05-sum-rest": note(["c05", "c06"], ["c05-rest", "c06-reduce"],
        "Collect the arguments with `...numbers` and `reduce` them from 0.",
        "The total starts at 0 and adds each argument once.",
        "One array of arguments.",
        "any number of numbers in; number out.",
        "Without the starting 0, `sum()` throws; a plain parameter receives only the first argument.",
        "`sum()`, one argument, several, and negatives.",
        "`reduce` needs a starting value for zero arguments."),
    # 06
    "js06-sort-default": note(["c06"], ["c06-sort"],
        "The first sort compares as text (\"100\" < \"9\"); the second compares numbers.",
        "`sort` changes the array in place each time.",
        "One array, re-ordered twice.",
        "numbers compared as strings, then as numbers.",
        'Expecting "1 9 10 100" from the first sort.', R,
        "`sort()` without a compare function sorts numbers as strings."),
    "js06-squares-of-evens": note(["c06"], ["c06-map"],
        "`filter` the even numbers (`n % 2 === 0`), then `map` each to `n * n`.",
        "The output keeps the input order.",
        "Two new arrays; the input is untouched.",
        "array of numbers in; array of numbers out.",
        "Testing `% 2 === 1` drops negatives and keeps odds; mapping without filtering squares everything.",
        "Mixed, empty, with 0 and a negative even number.",
        "`-3 % 2` is -1, not 1."),
    "js06-average": note(["c06"], ["c06-reduce"],
        "Return 0 for an empty array; otherwise `reduce` from 0 and divide by the length.",
        "The sum covers every number exactly once.",
        "One running sum.",
        "array of numbers in; number out.",
        "No starting value throws on []; no empty check gives 0 / 0 = NaN.",
        "[2, 4, 6], [], [5] and [1, 2].",
        "An empty array needs its own answer."),
    "js06-foreach-returns-undefined": note(["c06"], ["c06-foreach", "c06-map"],
        "Replace `forEach` with `map`, which returns the new array.",
        "The result has one doubled number per input number.",
        "One new array.",
        "array in; array out.",
        "`forEach` always returns undefined, whatever its callback returns.",
        "[1, 2, 3], [] and [-1].",
        "`forEach` is for side effects; it never builds an array."),
    "js06-group-by-category": note(["c06"], ["c06-reduce"],
        "`reduce` from `{}`: create the category's array the first time, push the name, return the accumulator.",
        "After each item, the accumulator holds every name seen so far, under its category.",
        "One object of arrays, built up item by item.",
        "array of objects in; object of string arrays out.",
        "Assigning `[item.name]` each time overwrites earlier names; pushing `item` stores the whole object.",
        "Two items in one category, an empty array, a single item.",
        "Return the accumulator from every call of the callback."),
    "js06-shared-reference": note(["c06"], ["c06-copy"],
        "`alias` is the same array as `original`; `copy` is a new one. Count each length after the pushes.",
        "`===` on arrays compares references, not contents.",
        "Two arrays: original/alias (4 items) and copy (5 items).",
        "arrays, numbers, booleans.",
        "Answering 3 for original (missing that alias is the same array).", R,
        "`const b = a` copies the reference, not the array."),
    # 07
    "js07-format-user": note(["c07"], ["c07-destructure"],
        'Destructure with `role = "GUEST"`, then build the string with a template literal and `toUpperCase`.',
        "A missing or undefined role becomes GUEST.",
        "Three local variables.",
        "object in; string out.",
        "No default makes `role.toUpperCase()` throw; swapping the names gives the wrong format.",
        "With a role, without one, with `role: undefined`, with mixed case.",
        "A destructuring default applies only to missing or undefined values."),
    "js07-shallow-spread": note(["c07"], ["c07-spread"],
        "Spread copied `name` (a string) and the reference to `skills` (shared array).",
        "Top-level properties are copied; nested objects are shared.",
        "Two objects, one shared array.",
        "objects, strings, arrays.",
        'Answering "math" (thinking the array was copied).', R,
        "Spread copies one level deep."),
    "js07-with-defaults": note(["c07"], ["c07-spread"],
        "Return `{ ...defaults, ...options }` so the options override the defaults.",
        "Every default key is present unless options sets it.",
        "One new object.",
        "object in; object out.",
        "Spreading options first lets the defaults overwrite the user's choices.",
        "Empty options, one override, several overrides including false.",
        "Later properties win, so spread the overrides last."),
    "js07-pick": note(["c07"], ["c07-in"],
        "For each key, copy it only `if (key in obj)`.",
        "The result has only keys that exist on `obj`, with their values, null included.",
        "One new object.",
        "object and array of strings in; object out.",
        "Copying blindly adds `undefined` keys; testing the value drops null, 0 and \"\".",
        "Existing keys, a missing key, no keys, and a key whose value is null.",
        "Ask whether the key exists, not whether its value is truthy."),
    "js07-optional-chaining": note(["c07"], ["c07-optional"],
        "`?.` stops at `null` (undefined); `?.` plus `??` gives the default; plain `.` on null throws.",
        "`?.` never throws on null or undefined.",
        "One object whose `profile` is null.",
        "undefined, string, TypeError.",
        "Expecting the third line to print undefined instead of TypeError.", R,
        "Only `?.` is safe; one plain dot after a null throws."),
    # 08
    "js08-unique": note(["c08"], ["c08-set"],
        "Return `[...new Set(values)]`.",
        "First-seen order is kept; each value appears once.",
        "One Set, then one array.",
        "array in; array out.",
        "Sorting the result changes the order.",
        'Repeats, empty, "a" vs "A", and 1 vs "1".',
        'A Set compares with ===, so 1 and "1" both stay.'),
    "js08-most-frequent-word": note(["c08"], ["c08-map"],
        "Count lower-cased words in a Map, then walk it keeping the first word with a strictly larger count.",
        "The Map iterates in insertion order, so ties keep the earliest word.",
        "A Map of word to count, plus the best word so far.",
        "string in; string out.",
        "`>=` picks the last word on a tie; not lower-casing splits \"Go\" and \"go\".",
        "A clear winner, mixed case, a tie, and empty text.",
        "Use `>` so a tie keeps the first word."),
    "js08-map-keys": note(["c08"], ["c08-map"],
        'The object turns 1 and "1" into one key; the Map keeps two.',
        "Map keys keep their type.",
        "An object with one key; a Map with two entries.",
        "numbers and strings as keys.",
        'Answering "2 2" or "string key".', R,
        "Object keys are strings; Map keys can be anything."),
    "js08-group-by-map": note(["c08"], ["c08-inherited", "c08-map"],
        "Group in a `Map` (`has`, `set`, `get(...).push`), then `Object.fromEntries(groups)`.",
        "Every category starts as an empty array the first time it is seen.",
        "A Map of category to names, then a plain object.",
        "array of objects in; object out.",
        '`{}["constructor"]` already exists (a function), so the plain-object version pushes onto it and throws.',
        '"constructor", "toString", a normal category, and an empty list.',
        "Plain objects inherit keys you never added."),
    # 09
    "js09-factorial": note(["c09"], ["c09-base"],
        "Return 1 when `n <= 1`; otherwise `n * factorial(n - 1)`.",
        "Every call is on a smaller n until the base case.",
        "One stack frame per pending call.",
        "number in; number out.",
        "A base case of `n === 1` never stops for 0.",
        "0, 1, 5 and 10.",
        "The base case must cover 0."),
    "js09-sum-nested": note(["c09"], ["c09-nested"],
        "For each item, add `sumNested(item)` if it is an array, else the item itself.",
        "Each call sums one array at one level, delegating deeper levels.",
        "One running total per pending call.",
        "nested array of numbers in; number out.",
        "`flat()` removes only one level, so deeper arrays end up as strings in the sum.",
        "Mixed depths, empty, nested empty, a single number.",
        "One level of flattening is not enough."),
    "js09-count-files": note(["c09"], ["c09-nested"],
        "Start with this folder's file count and add `countFiles(child)` for every sub-folder.",
        "A folder with no sub-folders just returns its own count.",
        "One running total per pending call.",
        "folder object in; number out.",
        "Adding only the children's own files misses deeper levels.",
        "A single folder, and a tree three levels deep with an empty folder.",
        "Recurse into children; don't just look at them."),
    "js09-trace": note(["c09"], ["c09-order"],
        "Expand: 3 + countdown(2) → 2 + countdown(1) → 1 + countdown(0) → \"liftoff\"; join on the way back.",
        "Each call returns a string that starts with its own number.",
        "Up to four calls waiting on the stack.",
        "numbers joined into a string.",
        'Reversing the order ("1 2 3 liftoff").', R,
        "Each call puts its number in front of the smaller call's result."),
    # 10
    "js10-parse-age": note(["c10"], ["c10-throw"],
        "Convert with `Number`; throw a `RangeError` for blank text, non-integers, below 0 or above 150.",
        "Only whole numbers from 0 to 150 are returned.",
        "One local number.",
        "string in; number out, or a RangeError.",
        "Throwing a plain `Error`; skipping the blank check (\"\" becomes 0).",
        '"42", "0", "150", "151", "-1", "4.5", "abc", "" and "   ".',
        "Blank text converts to 0 and passes unless checked."),
    "js10-finally": note(["c10"], ["c10-finally"],
        "\"try\" prints, the return is prepared, `finally` prints, then the caller prints the result.",
        "`finally` runs before control leaves the try statement.",
        "The pending return value waits while finally runs.",
        "strings.",
        "Putting \"result\" before \"finally\".", R,
        "A return inside try still runs finally first."),
    "js10-dont-swallow": note(["c10", "c11"], ["c10-catch", "c11-parse"],
        "Remove the try/catch; return `{}` only for blank text; let `JSON.parse` throw otherwise.",
        "Bad JSON always reaches the caller as a SyntaxError.",
        "No state.",
        "string in; object out, or a SyntaxError.",
        "Catching every error turns broken input into empty settings; removing the blank check makes \"\" throw.",
        "Valid JSON, \"\", \"   \" and \"{not json\".",
        "Handle the expected case; don't catch everything."),
    "js10-custom-error": note(["c10", "c12"], ["c10-custom", "c10-throw"],
        "Give `ValidationError` a constructor that calls `super(message)` and sets `this.name`; throw it for a missing name or email.",
        "Every error thrown is a ValidationError with the right message.",
        "No state.",
        "object in; true out, or a ValidationError.",
        "Without `this.name`, the error still reports itself as \"Error\".",
        "A valid user, a missing name, a missing email, an empty name.",
        "A subclass of Error keeps the name \"Error\" unless you set it."),
    # 11
    "js11-stringify-drops": note(["c11"], ["c11-stringify"],
        "Drop `nickname` and `greet` from the object, turn the `undefined` in the array into null, and write the Date as an ISO string.",
        "Only values JSON can hold are written.",
        "The original object is unchanged; a new string is made.",
        "object in; string out.",
        "Writing `\"nickname\":null` or including the function.", R,
        "undefined is dropped in objects but becomes null in arrays."),
    "js11-load-settings": note(["c11"], ["c11-parse", "c02-logical"],
        "Parse, then return `{ volume: data.volume ?? 50, muted: data.muted ?? false }`.",
        "The result has exactly two fields; saved 0 and false survive.",
        "One parsed object.",
        "string in; object out.",
        "`||` replaces a saved 0 or false; spreading the parsed data keeps unwanted fields.",
        'All fields, none, volume 0, and an extra field.',
        "`||` throws away a saved 0."),
    "js11-pretty": note(["c11"], ["c11-stringify", "c11-parse"],
        "`JSON.stringify(JSON.parse(text), null, 2)`.",
        "The output holds the same data as the input.",
        "One parsed value.",
        "string in; string out.",
        "Stringifying the text itself just adds quotes around it.",
        "An object with an array, an empty array, a plain string.",
        "Parse first, then stringify with indentation."),
    "js11-map-to-json": note(["c11", "c08"], ["c11-stringify", "c08-map"],
        "A Map has no own enumerable properties, so it becomes {}; converting it first keeps its entries.",
        "stringify writes only an object's own enumerable properties.",
        "One Map, one plain object.",
        "Map, object, strings.",
        'Expecting `{"ada":3}` on the first line.', R,
        "A Map stringifies to {}."),
    # 12
    "js12-bank-account": note(["c12"], ["c12-class", "c12-private"],
        "Declare `#balance = 0`; validate before changing it; return the new balance from each method.",
        "The balance never goes below 0 and is never reachable from outside.",
        "One private number per account.",
        "numbers in; numbers out, or RangeErrors.",
        "A public `balance` property is visible from outside; `>=` blocks withdrawing the exact balance.",
        "Deposit and withdraw, overdraw, withdraw everything, non-positive deposits, and the public property.",
        "Validate first, so a failed call leaves the balance unchanged."),
    "js12-lost-this": note(["c12"], ["c12-this"],
        "Called on its own, `greet` has `this` undefined and throws; `call` and `bind` supply `this`.",
        "`this` is set by the call, not by where the method was defined.",
        "One instance; a detached function; a bound copy.",
        "functions, strings, TypeError.",
        'Expecting "Hi, undefined" instead of a TypeError on the first line.', R,
        "A detached method loses `this`; in class code that throws."),
    "js12-this-in-callback": note(["c12"], ["c12-this"],
        "Change the `function (price)` callback to an arrow function.",
        "Inside the arrow function, `this` is the cart.",
        "The cart's `sum` field, updated once per price.",
        "array of numbers in; number out.",
        "A `function` callback gets its own `this` (undefined), so `this.sum` throws.",
        "Several prices, one price, none.",
        "Arrow functions use the surrounding `this`; `function` callbacks don't."),
    "js12-inheritance": note(["c12"], ["c12-extends", "c12-class"],
        "Write both classes with `extends Shape`, call `super(name)` first, store the dimensions, and implement `area()`.",
        "Every shape is a Shape and describes itself with its own area.",
        "One instance per shape with its dimensions.",
        "numbers in; Shape instances out.",
        "Standalone classes don't extend Shape (instanceof is false); using `this` before `super` throws.",
        "A circle of radius 1 and 2, and a 2 × 3 rectangle.",
        "Call super() before touching this."),
    # 13
    "js13-event-loop": note(["c13"], ["c13-order"],
        "Run the synchronous logs (A, D), then the promise callback (C), then the timer (B).",
        "Microtasks run before the next timer.",
        "One timer and one promise callback waiting.",
        "strings.",
        "Putting B before C because its delay is 0.", R,
        "A 0 ms timer still runs after promise callbacks."),
    "js13-load-names": note(["c13"], ["c13-all", "c13-promise"],
        "Start every request with `ids.map(getUser)` and `await Promise.all(...)`, then map users to names.",
        "Names come back in the order of `ids`.",
        "One array of pending promises, then one of users.",
        "array of numbers in; promise of array of strings out.",
        "`await` inside a loop runs the requests one at a time.",
        "Three ids (must overlap), none, one.",
        "await in a loop is sequential."),
    "js13-fetch-ok": note(["c13"], ["c13-fetch", "c10-throw"],
        "After `await fetch(url)`, throw `new Error(`HTTP ${response.status}`)` unless `response.ok`.",
        "Only 200–299 responses reach `json()`.",
        "One response object.",
        "string in; promise of the body out, or a rejection.",
        "Checking only for 404 lets 500 through.",
        "An OK URL, a missing one (404) and a failing one (500).",
        "fetch resolves on HTTP errors; check response.ok."),
    "js13-all-vs-allsettled": note(["c13"], ["c13-all"],
        "`Promise.all` rejects with the first rejection (\"boom\"); `allSettled` lists a status per promise.",
        "allSettled always fulfills.",
        "Two settled promises.",
        "promises, strings.",
        "Expecting `Promise.all` to return the successful value.", R,
        "Promise.all fails as a whole when one promise fails."),
    # 14
    "js14-default-and-named": note(["c14"], ["c14-import"],
        "`plus` is the default export (any name works); `PI` is a named export in braces.",
        "There is at most one default export per module.",
        "One module evaluated once.",
        "function and number.",
        "Thinking the default import must be called `add`.", R,
        "Default imports take any name; named imports must match."),
    "js14-missing-named-export": note(["c14"], ["c14-missing", "c14-import"],
        "`add` is a default export, so `{ add }` asks for a named export that does not exist: a SyntaxError before anything runs.",
        "Imports are checked before the module's code runs.",
        "Nothing runs.",
        "SyntaxError.",
        "Expecting it to print 5, or undefined.", R,
        "A default export is not a named export called add."),
    "js14-shared-state": note(["c14"], ["c14-once"],
        "Both imports are the same function with the same `count`: two calls make 2, the third returns 3.",
        "A module runs once; its variables are shared.",
        "One `count` variable in counter.js.",
        "number.",
        "Answering 1 (thinking each import gets its own copy).", R,
        "Renaming an import doesn't copy the module."),
}

SOURCES = [
    (r"Course deck: \path{backend/app/content/js_ts_course/part1.py}, \path{quotes.py}", "In full",
     "Cards, tests, solutions, quotes, deck summaries"),
    ("MDN JavaScript Guide (source text): Loops and iteration; Functions; Closures; Keyed collections; Using "
     "promises; JavaScript modules; Using classes; Control flow and error handling; Data types and structures",
     "Searched by keyword; relevant sections read", "Chapter facts; card quotes"),
    ("MDN reference pages (source text): typeof, const, let, if...else, strict equality, logical OR and AND, "
     "nullish coalescing, Number.isInteger, parseInt, Array.isArray, map, filter, reduce, forEach, sort, reverse, "
     "String slice, split, trim, toUpperCase, addition, remainder, for, for...of, for...in, return, rest parameters, "
     "spread, destructuring, optional chaining, in, Set, Map, Object.fromEntries, try...catch, throw, Error, "
     "RangeError, SyntaxError, JSON.parse, JSON.stringify, extends, super, arrow functions, bind, this, "
     "Promise.all, import, Window.fetch",
     "Opening paragraphs read; searched by keyword", "Chapter facts; card quotes"),
    ("MDN Glossary: Hoisting; Recursion", "In full", "Chapter facts; card quotes"),
]
NOT_READ = ("the ECMAScript specification; MDN pages beyond those listed (for example Expressions and "
            "operators, Iterators and generators, Working with objects); the TypeScript documentation "
            "(used in Parts 2--4, not here).")

FLAGS = [
    "Outside the material: how Node prints values (for example \\code{undefined} and error names) was "
    "established by running Node, not taken from the documentation.",
    "Conflicts: none found between the deck and the documentation.",
    "Simplification: Ch.~1 says a \\code{var} exists from the top of its function; at the top level of a "
    "script it belongs to the global scope instead. The material's examples are inside functions or modules.",
    "The js06-average quote is one item of MDN's list of exceptions (``Thrown if\\ldots''); its subject, "
    "TypeError, is named in the source title instead.",
    "Analogies are authored and simplify: a reference is not literally an address, and a closure keeps live "
    "variables that can still change, not a frozen snapshot as the snow-globe image suggests.",
    "Doubtful premise: the deck's name says ``Zero to Mastery''; this Part alone covers the fundamentals.",
]

DEVIATIONS = COMMON_DEVIATIONS + [
    "Chapter 14's snippets need two files; each listing shows both files, which were run as separate modules.",
    "One chapter snippet (Ch.~13, checking response.ok) was not run: it needs a live server. It is the "
    "same check as card js13-fetch-ok, which was run against a fake server.",
]
REVISIONS = [f"{TODAY}: first version."]

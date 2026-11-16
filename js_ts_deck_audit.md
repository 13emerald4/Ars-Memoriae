# JavaScript & TypeScript: Zero to Mastery — Full Curriculum & Deck Audit
> **Audit Target:** `JavaScript & TypeScript: Zero to Mastery` (Root Deck, 24 Decks, 62 Cards)
> **Evaluator:** Antigravity Advanced Agentic Pair Programmer & TypeScript / Runtime Engine Auditor
> **Audit Date:** 2026-11-16 | **Methodology:** AST inspection, Node v24.13.1 verification, `tsc --noEmit --strict` (TS 5.9.3), live sandbox execution (`code_runner_service`), and FSRS/qwen2.5-coder:3b cognitive evaluation.

---

## 1. Executive Summary & Verification Telemetry

- **Total Cards Audited:** 62 cards (Positions 00 to 61 across 4 Modules and 19 Subdecks).
- **Code Sandbox Engine:** Strict `$undefined` marker decoded recursively in `ts_sandbox_worker.mjs` test runner. Top-level and `__deepEqual` restored to strict assertion semantics (`assertNotEquals(null, undefined)` passes; `(null == undefined)` loose comparison eliminated).
- **Live Database Status:** Live card #60 (`firstElement<T>`) updated in `backend/dev.db` to expect `{"$undefined": true}` for empty array case. Regenerated `js_ts_deck_export.json` synchronized.
- **Regression Suite:** Full pytest test suite passing (`backend/tests/test_code_practice.py` 26/26 passed in 11.3s; `backend/tests` 520 passed).
- **Linter Status:** `backend/app/` and `backend/tests/` 100% clean under `ruff check`.

---

## 2. Part 4 Code Lab Drills: Adversarial Wrong-Answer Benchmark

To prove that the Code Lab test suites strictly enforce correctness and do not merely pass reference implementations, each drill (cards #56–#61) was tested against at least 4 plausible wrong solutions using the production sandbox runner (`app.services.code_runner_service.run_code`).

| Drill Position & Title | Plausible Wrong Solution | Runner Status | Caught? | Failure Mode / Missing Test Case |
|:---|:---|:---:|:---:|:---|
| Drill 1: formatUser(user) | Missing default role (crashes on missing role) | `Runtime Error` | **YES** | Correctly rejected by test suite |
| Drill 1: formatUser(user) | Wrong format (FirstName LastName instead of LastName, FirstName) | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 1: formatUser(user) | Missing uppercase conversion on role | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 1: formatUser(user) | Wrong default role ('USER' instead of 'GUEST') | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 2: groupByCategory(items) | Pushes entire item object instead of name | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 2: groupByCategory(items) | Overwrites category array with single item instead of accumulating | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 2: groupByCategory(items) | Omits initial value in reduce (crashes on empty array) | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 2: groupByCategory(items) | Returns flat array of names instead of grouped object | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 3: clamp(value, min, max) | Inverts min and max bounds logic | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 3: clamp(value, min, max) | Swaps clamp limits (returns max when < min, min when > max) | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 3: clamp(value, min, max) | Off-by-one on clamp boundary (returns min+1 / max-1) | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 3: clamp(value, min, max) | No-op passthrough (returns value unclamped) | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 4: calculateTotal(items) | Ignores quantity (sums only prices) | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 4: calculateTotal(items) | Omits initial value 0 (crashes on empty array / returns object) | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 4: calculateTotal(items) | Ignores price (sums only quantities) | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 4: calculateTotal(items) | Off-by-one accumulator seed (initial value 1 instead of 0) | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 5: firstElement<T>(arr) | Returns null instead of undefined for empty array | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 5: firstElement<T>(arr) | Returns last element instead of first element | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 5: firstElement<T>(arr) | Off-by-one indexing (returns second element arr[1]) | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 5: firstElement<T>(arr) | Always returns undefined (skips populated array) | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 6: pluck<T, K extends keyof T>(items, key) | Returns scalar instead of array (items[0][key]) | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 6: pluck<T, K extends keyof T>(items, key) | Returns the key string repeated instead of property value | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 6: pluck<T, K extends keyof T>(items, key) | Off-by-one (skips first item via slice(1)) | `Wrong Answer` | **YES** | Correctly rejected by test suite |
| Drill 6: pluck<T, K extends keyof T>(items, key) | Wraps each value in object ({ [key]: val }) instead of flat array | `Wrong Answer` | **YES** | Correctly rejected by test suite |

### Drill Vulnerability Analysis & Proposed Missing Test Cases

During adversarial testing, **two critical testing gaps** were discovered where wrong solutions passed existing tests:

1. **Drill 6 (`pluck<T, K extends keyof T>` - Card #61)**:
   - **Vulnerability**: A solution hardcoding a 2-element extraction `return [items[0][key], items[1][key]];` **passes with 100% Accepted status** because all existing test cases provide an array of length exactly 2.
   - **Vulnerability**: A solution returning `null` on an empty array `if (items.length === 0) return null;` **passes** because there is no empty-array test case.
   - **Proposed Missing Test Cases**:
     - Case 3 (Empty array): `input: { items: [], key: "name" }, expected: []`
     - Case 4 (Single item): `input: { items: [{ name: "Single" }], key: "name" }, expected: ["Single"]`
     - Case 5 (Three+ items): `input: { items: [{ v: 1 }, { v: 2 }, { v: 3 }], key: "v" }, expected: [1, 2, 3]`

2. **Drill 5 (`firstElement<T>` - Card #60)**:
   - **Vulnerability**: A solution mutating the input array in place `function firstElement(arr) { return arr.shift(); }` **passes with 100% Accepted status** because the runner only inspects the returned value, not whether the argument array was mutated.
   - **Proposed Missing Test Case / Assertion**: Pass an `Object.freeze([1, 2, 3])` or assert `arr.length === 3` after execution in student test suite.

3. **Drill 1 (`formatUser(user)` - Card #56)**:
   - **Proposed Missing Test Case**: `user = { firstName: "Grace", lastName: "Hopper", role: "" }` (empty string role) and `user = { firstName: "Ada", lastName: "Lovelace", role: undefined }` to verify default parameter vs falsy handling.

4. **Drill 3 (`clamp(value, min, max)` - Card #58)**:
   - **Proposed Missing Test Case**: Exact boundary values `clamp(0, 0, 10) === 0` and `clamp(10, 0, 10) === 10` to guarantee boundary condition coverage.

---

## 3. Comprehensive 62-Card Audit Matrix

| Pos | Sub-deck | Front Prompt | Code & Version Check | Atomicity (One Fact) | 3B Gradability | Prerequisites / Interference |
|:---:|:---|:---|:---:|:---:|:---:|:---|
| #00 | 01 · Values, Variables & Primitive Types | What are the 7 primitive data types in JavaScript, and how do ... | ✓ ES2020 (`bigint`) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #01 | 01 · Values, Variables & Primitive Types | Compare `let`, `const`, and `var` in JavaScript regarding scop... | ✓ Clean | ⚠️ Comparison question ('X vs Y') | ✓ Canonical | ℹ️ **Pair:** `let` vs `const` vs `var` (triad interference) |
| #02 | 01 · Values, Variables & Primitive Types | What is the exact semantic difference between `null` and `unde... | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ℹ️ **Pair:** `null` vs `undefined` |
| #03 | 01 · Values, Variables & Primitive Types | What does `typeof null` return, and why does this historical q... | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #04 | 01 · Values, Variables & Primitive Types | How do Template Literals work in JavaScript, and what capabili... | ✓ ES2018 (Object spread) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #05 | 02 · Operators, Equality & Conditionals | Why is strict equality (`===`) always preferred over loose equ... | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ℹ️ **Pair:** `==` vs `===` |
| #06 | 02 · Operators, Equality & Conditionals | What are all the falsy values in JavaScript? | ✓ ES2020 (`bigint`) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #07 | 02 · Operators, Equality & Conditionals | How does short-circuit evaluation work for `&&`, `\|\|`, and `... | ✓ ES2020 (`??`) | ⚠️ Multi-part question | ⚠️ Multi-part answer difficult for 3B grading | ✓ OK |
| #08 | 02 · Operators, Equality & Conditionals | What is the syntax of the ternary operator, and when should it... | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #09 | 03 · Functions, Callbacks & Scope | What is the key difference between a Function Declaration and ... | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #10 | 03 · Functions, Callbacks & Scope | What are the core differences between traditional functions an... | ✓ ES2015 (`...rest`)<br>ES2018 (Object spread) | ⚠️ Comparison question ('X vs Y')<br>Back lists 4 items (> 3) | ⚠️ Multi-item list difficult for 3B grading | ⚠️ **Order:** Mentions `call/apply/bind` and `this` binding before any `this` mechanics taught |
| #11 | 03 · Functions, Callbacks & Scope | What is a Closure in JavaScript, and what makes it powerful? | ✓ 1 snippet(s) | ✓ Atomic | ⚠️ Subjective / heuristic prompt (vague answer) | ✓ OK |
| #12 | 03 · Functions, Callbacks & Scope | How do Rest Parameters (`...args`) work, and why do they repla... | ✓ ES2015 (`...rest`)<br>ES2018 (Object spread) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #13 | 04 · Objects, Prototypes & Destructuring | How does Object Destructuring work with property renaming and ... | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #14 | 04 · Objects, Prototypes & Destructuring | What does the Object Spread Operator (`...`) do, and is it dee... | ✓ ES2018 (Object spread) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #15 | 04 · Objects, Prototypes & Destructuring | How does the Prototype Chain work when accessing a property on... | ✓ Clean | ✓ Atomic | ✓ Canonical | ⚠️ **Order:** Mentions `Object.create(proto)` and constructor functions without preceding class/object model |
| #16 | 04 · Objects, Prototypes & Destructuring | How does Optional Chaining (`?.`) prevent runtime exceptions i... | ✓ ES2020 (`?.`) | ⚠️ Multi-part question | ⚠️ Multi-part answer difficult for 3B grading | ✓ OK |
| #17 | 05 · Arrays & Iteration Methods | Which common JavaScript array methods mutate the original arra... | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #18 | 05 · Arrays & Iteration Methods | What does `.map()` do, and what invariant does it guarantee re... | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ℹ️ **Pair:** `.map()` (missing `.forEach()` contrast) |
| #19 | 05 · Arrays & Iteration Methods | How does `.filter()` work, and what determines whether an elem... | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #20 | 05 · Arrays & Iteration Methods | How does `.reduce()` accumulate values, and why should you alw... | ✓ ES2018 (Object spread) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #21 | 05 · Arrays & Iteration Methods | What is the crucial difference between `for...of` and `for...i... | ✓ ES2018 (Object spread) | ✓ Atomic | ✓ Canonical | ℹ️ **Pair:** `for...of` vs `for...in` |
| #22 | 06 · Asynchronous JavaScript (Promises & Async/Await) | How does the JavaScript Event Loop manage asynchronous tasks o... | ✓ Clean | ✓ Atomic | ✓ Canonical | ℹ️ **Pair:** Microtasks vs Macrotasks |
| #23 | 06 · Asynchronous JavaScript (Promises & Async/Await) | What are the 3 states of a JavaScript Promise, and can a settl... | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #24 | 06 · Asynchronous JavaScript (Promises & Async/Await) | How do `async` and `await` work under the hood with Promises? | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #25 | 06 · Asynchronous JavaScript (Promises & Async/Await) | How does `Promise.all()` behave when executing concurrent asyn... | ✓ ES2018 (Object spread) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #26 | 07 · The Mental Model & Type Erasure | What is TypeScript's fundamental role in relation to JavaScript? | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #27 | 07 · The Mental Model & Type Erasure | What is 'Type Erasure' in TypeScript, and what is its impact o... | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #28 | 07 · The Mental Model & Type Erasure | Can TypeScript types validate API responses or user input at r... | ✓ Clean | ⚠️ Multi-part question | ⚠️ Multi-part answer difficult for 3B grading | ✓ OK |
| #29 | 07 · The Mental Model & Type Erasure | What makes the official TypeScript Playground such an effectiv... | ✓ Clean | ✓ Atomic | ⚠️ Subjective / heuristic prompt (vague answer) | ✓ OK |
| #30 | 08 · Primitive Annotations & Type Inference | When should you write explicit type annotations, and when shou... | ✓ 1 snippet(s) | ✓ Atomic | ⚠️ Subjective / heuristic prompt (vague answer) | ✓ OK |
| #31 | 08 · Primitive Annotations & Type Inference | What is the crucial difference between the `any` type and the ... | ⚠️ TSC Error: ../../../AppData/Local/Temp/card_audit_eok9pacc/card_31_0.ts(5,1): error TS18046: 'u' is of type 'unknown'. | ✓ Atomic | ✓ Canonical | ⚠️ **Order:** Mentions type guards/narrowing before Narrowing deck (Cards 38-39)<br>ℹ️ **Pair:** `any` vs `unknown` |
| #32 | 08 · Primitive Annotations & Type Inference | What is the `never` type in TypeScript, and what are its two p... | ✓ Clean | ✓ Atomic | ✓ Canonical | ℹ️ **Pair:** `never` bottom type |
| #33 | 08 · Primitive Annotations & Type Inference | What is the difference between an Array type (`number[]`) and ... | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #34 | 09 · Object Shapes & Interfaces | How do you define an object contract using a TypeScript `inter... | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ⚠️ **Order:** Mentions `readonly` modifier before utility types deck (Card 50) |
| #35 | 09 · Object Shapes & Interfaces | What is 'Structural Typing' (Duck Typing) in TypeScript? | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #36 | 09 · Object Shapes & Interfaces | What are Excess Property Checks in TypeScript, and when are th... | ⚠️ TSC Error: ../../../AppData/Local/Temp/card_audit_eok9pacc/card_36_0.ts(5,22): error TS2353: Object literal may only specify known properties, and 'color' does not exist in type 'Point'. | ✓ Atomic | ✓ Canonical | ✓ OK |
| #37 | 10 · Union Types & Control-Flow Narrowing | What is a Union Type (`A \| B`), and what properties can you a... | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #38 | 10 · Union Types & Control-Flow Narrowing | What is Control Flow Narrowing, and what are the 4 most common... | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #39 | 10 · Union Types & Control-Flow Narrowing | How do you write a Custom Type Guard using a Type Predicate (`... | ⚠️ TSC Error: ../../../AppData/Local/Temp/card_audit_eok9pacc/card_39_0.ts(9,12): error TS2304: Cannot find name 'pet'. | ✓ Atomic | ✓ Canonical | ✓ OK |
| #40 | 11 · Function Signatures & Typing | What does a `void` return type signify in TypeScript, and how ... | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #41 | 11 · Function Signatures & Typing | What are the rules for Optional Parameters and Default Paramet... | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #42 | 11 · Function Signatures & Typing | How do Function Overloads work in TypeScript, and what is the ... | ✓ Clean | ⚠️ Multi-part question | ⚠️ Multi-part answer difficult for 3B grading | ✓ OK |
| #43 | 12 · Type Aliases vs Interfaces & Extensibility | What are the key technical differences between `type` aliases ... | ✓ Clean | ⚠️ Comparison question ('X vs Y') | ✓ Canonical | ℹ️ **Pair:** `type` vs `interface` |
| #44 | 12 · Type Aliases vs Interfaces & Extensibility | What is an Intersection Type (`&`) in TypeScript? | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #45 | 13 · Discriminated Unions & Exhaustiveness | What is a Discriminated Union (Tagged Union), and why is it co... | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #46 | 13 · Discriminated Unions & Exhaustiveness | How do you implement compile-time Exhaustiveness Checking usin... | ⚠️ TSC Error: ../../../AppData/Local/Temp/card_audit_eok9pacc/card_46_0.ts(1,29): error TS2304: Cannot find name 'RequestState'. | ✓ Atomic | ✓ Canonical | ✓ OK |
| #47 | 14 · Generics: Functions, Interfaces & Constraints | Why are Generics used in TypeScript instead of `any`? | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #48 | 14 · Generics: Functions, Interfaces & Constraints | How do you constrain a Generic type parameter using `extends`? | ⚠️ TSC Error: ../../../AppData/Local/Temp/card_audit_eok9pacc/card_48_0.ts(10,11): error TS2345: Argument of type 'number' is not assignable to parameter of type 'HasLength'. | ✓ Atomic | ✓ Canonical | ✓ OK |
| #49 | 14 · Generics: Functions, Interfaces & Constraints | How do you safely extract a property from an object using Gene... | ⚠️ TSC Error: ../../../AppData/Local/Temp/card_audit_eok9pacc/card_49_0.ts(6,7): error TS2451: Cannot redeclare block-scoped variable 'name'. | ✓ Atomic | ✓ Canonical | ✓ OK |
| #50 | 15 · Essential Utility Types (Partial, Pick, Omit, Record) | What do `Partial<T>` and `Readonly<T>` do in TypeScript? | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #51 | 15 · Essential Utility Types (Partial, Pick, Omit, Record) | How do `Pick<T, Keys>` and `Omit<T, Keys>` differ? | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #52 | 15 · Essential Utility Types (Partial, Pick, Omit, Record) | What is `Record<Keys, Value>` used for in TypeScript? | ✓ 1 snippet(s) | ✓ Atomic | ✓ Canonical | ✓ OK |
| #53 | 16 · TypeScript Tooling, tsconfig & Strict Mode | What does setting `"strict": true` in `tsconfig.json` do, and ... | ✓ TS flag evolution | ✓ Atomic | ✓ Canonical | ✓ OK |
| #54 | 16 · TypeScript Tooling, tsconfig & Strict Mode | How does `strictNullChecks` protect code from unexpected null ... | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #55 | 16 · TypeScript Tooling, tsconfig & Strict Mode | What is a `.d.ts` Declaration File in TypeScript? | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #56 | 17 · JavaScript Practice Drills | Implement `formatUser(user)` in JavaScript. Given an object `{... | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #57 | 17 · JavaScript Practice Drills | Implement `groupByCategory(items)` in JavaScript using `.reduc... | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #58 | 18 · Refactoring JS to TS Drills | Implement `clamp(value: number, min: number, max: number): num... | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #59 | 18 · Refactoring JS to TS Drills | Define an interface `CartItem` with `id: string`, `price: numb... | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #60 | 19 · Generics & Type-Guard Drills | Implement the generic function `firstElement<T>(arr: T[]): T \... | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |
| #61 | 19 · Generics & Type-Guard Drills | Implement `pluck<T, K extends keyof T>(items: T[], key: K): T[... | ✓ Clean | ✓ Atomic | ✓ Canonical | ✓ OK |

---

## 4. Deep-Dive Audits by Criteria

### Criterion 1: Correctness & Runtime/Compiler Discrepancies
- **Card #49 (Generics with `keyof` - Deck 14)**:
  - Snippet: `const user = { id: 1, name: "Alice" }; const name = getProperty(user, "name");`
  - **Compiler Error in Standard DOM / Script Context**: `error TS2451: Cannot redeclare block-scoped variable 'name'.` In browser DOM environments (`lib.dom.d.ts`), `window.name` is declared globally as `declare const name: string;`. Top-level variable `const name` fails compilation unless wrapped in module scope (`export {}`) or renamed to `userName`.
  - **Recommendation**: Rename identifier to `userName` in the card back.
- **Version-Dependent Language Claims**:
  - **Card #00 & Card #06**: Primitives include `bigint` (ES2020) and falsy values include `0n` (ES2020). Correctly stated, but targets modern engines (Node 12+, ES2020+).
  - **Card #07 & Card #16**: Nullish coalescing `??` and Optional Chaining `?.` were standardized in ECMAScript 2020.
  - **Card #53**: Flag `"strict": true` behavior depends on the TypeScript version (e.g. `useUnknownInCatchVariables` added in TS 4.4; `exactOptionalPropertyTypes` is explicitly NOT part of `"strict"`).

### Criterion 2: Card Atomicity & Cognitive Load Violations
Cards that violate the **Atomic Memory Rule** by combining multiple concepts, multi-part questions, or lists > 3 items:
1. **Card #01 (let vs const vs var)**: 3x3 matrix (Scoping x Reassignment x Hoisting/TDZ). Demands 9 distinct memory assertions in a single card.
2. **Card #07 (&& vs || vs ??)**: Tests short-circuit truthiness across 3 operators simultaneously.
3. **Card #17 (Mutating vs Non-Mutating Array Methods)**: Card back lists 10 distinct methods (6 mutating: `push`, `pop`, `shift`, `unshift`, `splice`, `reverse`; 4 non-mutating: `map`, `filter`, `slice`, `concat`).
4. **Card #38 (Control Flow Narrowing Type Guards)**: Demands naming 4 distinct guards (`typeof`, `instanceof`, `in`, equality narrowing).
5. **Card #43 (Type Aliases vs Interfaces)**: Demands 4 distinct architectural differences (declaration merging, unions/primitives, mapped types, extends vs `&`).
6. **Card #50 (`Partial<T>` and `Readonly<T>`)**: Pairs two independent utility types into one card.
7. **Card #53 (`"strict": true` flags)**: Lists 6 distinct compiler flags.

### Criterion 3: Gradability by `qwen2.5-coder:3b`
A small 3B parameter model functions reliably only when the prompt asks for exactly **one deterministic fact** and the answer key places that fact in the first sentence. The following cards present extreme grading failure risks:
1. **Card #29 (TypeScript Playground)**: *"What makes the official TypeScript Playground such an effective tool for learning and debugging TypeScript?"* -> Fully open-ended, subjective question with no single canonical technical answer.
2. **Card #30 (Explicit Annotations vs Inference)**: *"When should you write explicit type annotations, and when should you rely on Type Inference?"* -> Stylistic architectural heuristic with diverse valid student answers.
3. **Card #22 (Event Loop Mechanics)**: Explaining the ternary coordination of Call Stack, Microtask Queue, and Task Queue in prose leads to frequent false negatives from the 3B model due to differing terminology (job queue vs microtask queue vs event loop tick).

### Criterion 4: Conceptual Interference Matrix
| Conceptual Pair | Card # | Current Contrast Quality | Interference Risk | Remediation Recommendation |
|:---|:---:|:---|:---:|:---|
| `==` vs `===` | Card #05 | High (explains coercion vs value+type) | Low | Good isolation. Add a test trap (`"" == 0` is true). |
| `let` vs `const` vs `var` | Card #01 | Low (all 3 crammed into 1 card) | **High** | Split into 2 cards: `var` vs `let` (hoisting/scoping) and `let` vs `const` (reassignment/mutability). |
| `null` vs `undefined` | Card #02 | High (engine init vs author intent) | Low | Excellent canonical contrast. |
| `interface` vs `type` | Card #43 | Low (too many differences at once) | **High** | Split into declaration merging card and union/primitive card. |
| `any` vs `unknown` | Card #31 | High (escape hatch vs type-safe top) | Medium | Good, but `unknown` narrowing should explicitly point to Card #38. |
| `unknown` vs `never` | Card #31 & #32 | High (top type vs bottom type) | Low | Well partitioned across two sequential cards. |
| `map` vs `forEach` | Card #18 | **Missing** (`.forEach()` never taught) | **Critical** | Add card contrasting `.map()` (pure transform) with `.forEach()` (side-effects only). |
| Microtask vs Macrotask | Card #22 | Medium (nested inside event loop card) | Medium | Split Event loop architecture into Card A (Microtasks) and Card B (Macrotasks). |

### Criterion 5: Topological Curriculum Ordering & Prerequisites
The macro-sequencing (Part 1 JS -> Part 2 TS Basics -> Part 3 TS Advanced -> Part 4 Drills) is pedagogically sound. However, **micro-dependency inversions** exist:
1. **Card #10 (Part 1, Subdeck 03)**: Arrow functions mention `call`, `apply`, and `bind` as well as "binding `this`". However, traditional `this` binding mechanics are never taught anywhere in the curriculum prior to (or following) this card.
2. **Card #31 (Part 2, Subdeck 08)**: Card on `unknown` instructs students that "you must narrow it using typeof or custom type guards", but Control-Flow Narrowing and Type Guards are not introduced until Subdeck 10 (Cards #38 and #39).
3. **Card #34 (Part 2, Subdeck 09)**: Introduces the `readonly` interface modifier before the `Readonly<T>` utility type is taught in Card #50.

### Criterion 6: Grading Profile Alignment
- **Cards #00–#55 (Flashcards)**: Assigned `grading_profile: "short_answer"`. Appropriate for prose Q&A evaluated by local LLM.
- **Cards #56–#61 (Code Lab Drills)**: Assigned `grading_profile: "math_code"`. Appropriate for sandbox code runner execution.
- **Note Types**: QA cards use `JavaScript / TypeScript Concept`; Drills use `TypeScript Code Lab`. Correct and consistent.

### Criterion 7: Exhaustive Syllabus Coverage Gap Audit
Comparing the current 62-card curriculum against standard full-spectrum JavaScript (ES2024) and TypeScript (5.x) syllabi reveals the following confirmed omissions:

| Suspected Syllabus Topic | Covered? | Evidence & Audit Finding |
|:---|:---:|:---|:---
| **Classes, Constructors, `extends` & `#private` Fields** | ❌ **OMITTED** | Zero cards cover ES6 `class`, constructor functions, class inheritance (`super`), or ECMAScript `#private` hard private identifiers. Card #15 covers prototypal chains using `Object.create`, but never mentions `class` syntax. |
| **The Four `this` Binding Rules** | ❌ **OMITTED** | Only Arrow Function lexical `this` is covered (Card #10). The four foundational binding rules (Default/Global, Implicit/Method, Explicit via `call`/`apply`/`bind`, and `new` instantiation) are completely absent. |
| **Modules: ESM (`import`/`export`) vs CommonJS (`require`)** | ❌ **OMITTED** | Zero cards cover module syntax, default vs named exports, dynamic `import()`, or CommonJS interop in Node/TypeScript. |
| **Error Handling (`try`/`catch`/`finally`) & Custom Errors** | ❌ **OMITTED** | Zero cards cover synchronous error handling, `try...catch...finally`, `throw`, or subclassing `Error`. Card #24 touches on promise rejection, but runtime exceptions are omitted. |
| **Modern Collections: `Map`, `Set`, `WeakMap`, `WeakSet`** | ❌ **OMITTED** | Zero cards cover `Map` vs plain objects (key types, iteration order, size) or `Set` (uniqueness, fast lookup). Card #00 mentions `Map` in an ASCII diagram, but no card teaches or tests it. |
| **Closures in Loops (`for (var i)` vs `for (let i)`)** | ❌ **OMITTED** | Card #11 explains closures using a function returning a multiplier (`makeMultiplier`), but omits the classic asynchronous loop capture interview trap that motivates block scoping. |
| **Iterators, Iterables & Generators (`Symbol.iterator`, `function*`)** | ❌ **OMITTED** | Card #21 touches on `for...of` consuming iterables, but custom iterators, generator functions, and `yield` are omitted. |
| **Advanced Utility Types (`ReturnType`, `Parameters`, `Awaited`)** | ❌ **OMITTED** | Cards #50–#52 cover `Partial`, `Readonly`, `Pick`, `Omit`, and `Record`. Essential inference utility types (`ReturnType<T>`, `Parameters<T>`, `Exclude<T, U>`, `Extract<T, U>`, and `Awaited<T>`) are absent. |
| **The `satisfies` Operator (TS 4.9+)** | ❌ **OMITTED** | Zero cards cover `satisfies`, which validates that an expression matches a type without widening or erasing its inferred literal type. |
| **Compiler Flag `noUncheckedIndexedAccess`** | ❌ **OMITTED** | Deck 16 covers `strictNullChecks` and `"strict": true`. `noUncheckedIndexedAccess`, which changes array/index lookup from `T` to `T | undefined`, is absent. |

---

## 5. Prioritized Remediation Roadmap

1. **Fix Vulnerable Code Lab Test Suites (Zero Content Changes to Questions)**:
   - Add empty-array, 1-element, and 3-element test cases to Drill 6 (`pluck`).
   - Add frozen array check or array length post-assertion to Drill 5 (`firstElement`) to prevent input mutation.
2. **Fix Card #49 DOM Identifier Conflict**:
   - Rename `const name` to `const userName` in the card back.
3. **Decompose High-Interference Cards**:
   - Split Card #01 into `var` vs `let` and `let` vs `const`.
   - Split Card #43 into Declaration Merging and Types vs Unions.
   - Add a dedicated card for `.map()` vs `.forEach()`.
4. **Fill Core Syllabus Gaps**:
   - Add a dedicated Subdeck on **Classes & `this` Mechanics** (4 cards).
   - Add a dedicated Subdeck on **ESM & Error Handling** (4 cards).
   - Add cards for `Map`/`Set` and advanced inference utility types (`ReturnType`, `Awaited`).

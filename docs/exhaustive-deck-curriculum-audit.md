# Ars Memoriae — Exhaustive Card Deck & Subtree Curriculum Audit Dossier

> **Auditor Notice**: This dossier contains the complete architectural, topological, pedagogical, and card-level inventory of the Ars Memoriae JavaScript & TypeScript Curriculum. It is formatted for direct evaluation by an external Large Language Model auditor.

## LLM Auditor Prompt Template
```text
You are an expert curriculum auditor specializing in computer science education, cognitive science, and spaced repetition flashcard design.
Please review the following complete curriculum architecture, subtree topology, and card inventories for Ars Memoriae's 'JavaScript & TypeScript: Zero to Mastery' collection.

Evaluate the curriculum across the following dimensions:
1. Topological Dependency Order: Do prerequisites flow strictly from dynamic JavaScript runtime mechanics to static TypeScript analysis to advanced type calculus?
2. Atomicity & Cognitive Load: Does each card test a single atomic concept without cognitive interleaving or compound confusion?
3. Factual Accuracy: Are definitions strictly aligned with ECMAScript 2024 and TypeScript 5.x standards?
4. Pre-Answer Priming & Active Recall: Do the primers provide sufficient contextual framing without leaking the answer?
5. Gap Analysis: Are there any critical omissions in runtime JavaScript or core TypeScript that should be added?
```

---

# JavaScript & TypeScript: Zero to Mastery — Curriculum Master Architecture

## 1. Executive Summary & Curriculum Scope
This curriculum provides a mathematically sound, pedagogically sequenced path from ECMAScript runtime mechanics through intermediate TypeScript type calculus and hands-on system design. 

The core thesis of this curriculum is **Runtime Primacy Followed by Compile-Time Static Typing**:
- **Phase 1 (JavaScript Runtime)**: Memory model, value taxonomy, variable scoping & hoisting (TDZ), prototypal inheritance, closure lexical environments, and the single-threaded asynchronous Event Loop.
- **Phase 2 (TypeScript Static Safety Layer)**: Type erasure, top (`unknown`, `any`) vs bottom (`never`) set-theoretic types, inference rules, control-flow narrowing, and function signature contracts.
- **Phase 3 (Intermediate Type System & System Design)**: Object modeling (`interface` vs `type`), algebraic data types (discriminated unions with compile-time exhaustiveness), generic abstraction with `extends` and `keyof` constraints, built-in utility transformations, and `tsconfig` strict-mode hardening.
- **Phase 4 (Interactive Code Lab Synthesis)**: Test-driven drills validating algorithmic fluency in pure JavaScript and static type refactoring in TypeScript.

---

## 2. Complete Subtree Topology & Priority Hierarchy

```text
JavaScript & TypeScript: Zero to Mastery (Root Deck | Priority: 90 | Pos: 0 | 62 Cards)
│
├── Part 1: JavaScript Fundamentals (Runtime & Core Syntax) (Module Deck | Priority: 90 | Pos: 0 | 26 Cards)
│   ├── 01 - Values, Variables & Primitive Types (Subdeck | Priority: 90 | Pos: 0 | Cards: #00–#04)
│   ├── 02 - Operators, Equality & Conditionals (Subdeck | Priority: 90 | Pos: 1 | Cards: #05–#08)
│   ├── 03 - Functions, Callbacks & Scope (Subdeck | Priority: 90 | Pos: 2 | Cards: #09–#12)
│   ├── 04 - Objects, Prototypes & Destructuring (Subdeck | Priority: 90 | Pos: 3 | Cards: #13–#16)
│   ├── 05 - Arrays & Iteration Methods (Subdeck | Priority: 90 | Pos: 4 | Cards: #17–#21)
│   └── 06 - Asynchronous JavaScript (Promises & Async/Await) (Subdeck | Priority: 90 | Pos: 5 | Cards: #22–#25)
│
├── Part 2: TypeScript Core (Static Types as a Safety Layer) (Module Deck | Priority: 80 | Pos: 1 | 17 Cards)
│   ├── 07 - The Mental Model & Type Erasure (Subdeck | Priority: 80 | Pos: 0 | Cards: #26–#29)
│   ├── 08 - Primitive Annotations & Type Inference (Subdeck | Priority: 80 | Pos: 1 | Cards: #30–#33)
│   ├── 09 - Object Shapes & Interfaces (Subdeck | Priority: 80 | Pos: 2 | Cards: #34–#36)
│   ├── 10 - Union Types & Control-Flow Narrowing (Subdeck | Priority: 80 | Pos: 3 | Cards: #37–#39)
│   └── 11 - Function Signatures & Typing (Subdeck | Priority: 80 | Pos: 4 | Cards: #40–#42)
│
├── Part 3: Intermediate TypeScript & System Design (Module Deck | Priority: 70 | Pos: 2 | 13 Cards)
│   ├── 12 - Type Aliases vs Interfaces & Extensibility (Subdeck | Priority: 70 | Pos: 0 | Cards: #43–#44)
│   ├── 13 - Discriminated Unions & Exhaustiveness (Subdeck | Priority: 70 | Pos: 1 | Cards: #45–#46)
│   ├── 14 - Generics: Functions, Interfaces & Constraints (Subdeck | Priority: 70 | Pos: 2 | Cards: #47–#49)
│   ├── 15 - Essential Utility Types (Partial, Pick, Omit, Record) (Subdeck | Priority: 70 | Pos: 3 | Cards: #50–#52)
│   └── 16 - TypeScript Tooling, tsconfig & Strict Mode (Subdeck | Priority: 70 | Pos: 4 | Cards: #53–#55)
│
└── Part 4: Hands-On Code Lab Drills (Module Deck | Priority: 60 | Pos: 3 | 6 Cards)
    ├── 17 - JavaScript Practice Drills (Subdeck | Priority: 60 | Pos: 0 | Cards: #56–#57)
    ├── 18 - Refactoring JS to TS Drills (Subdeck | Priority: 60 | Pos: 1 | Cards: #58–#59)
    └── 19 - Generics & Type-Guard Drills (Subdeck | Priority: 60 | Pos: 2 | Cards: #60–#61)
```

---

## 3. Pedagogical Principles & Spaced Repetition Design
1. **Strict Progressive Ordering**: Cards are indexed globally (`position: 0..61`) across subdecks. When studying the Root Deck or any Module, cards appear in strict curriculum sequence, never interleaving disjoint topics.
2. **Atomic Answer Rule**: Every flashcard isolates exactly one concept (e.g. `typeof null`, Temporal Dead Zone, `never` bottom type, Excess Property Checking). Questions avoid multi-part cognitive overload.
3. **Pre-Answer Primer & Citations**: Every card links to verified official sources (TypeScript Handbook v2, ECMAScript 2024 Specification, MDN Web Docs) and includes a context hook anchoring the memory before the answer prompt.
4. **FSRS Scheduling Parameters**: Desired retention default is set to 0.90 with module priority cascading (Part 1 = 90, Part 2 = 80, Part 3 = 70, Part 4 = 60).

---

## 4. LLM Auditor Instruction & Evaluation Criteria
If you are an external LLM auditing this curriculum:
- **Audit Objective 1: Topological Dependency Correctness**. Verify that no card references concepts introduced in a later card (e.g. no TypeScript types are referenced in Part 1; no Generics are assumed in Part 2).
- **Audit Objective 2: Factual Accuracy against Modern Standards**. Verify that explanations conform to ECMAScript 2024 and TypeScript 5.x (e.g. `bigint` included in primitives; `exactOptionalPropertyTypes` awareness; correct distinction between `void` and `undefined`).
- **Audit Objective 3: Card Atomicity & Testability**. Ensure every card prompt can be answered concisely and deterministically without ambiguity.
- **Audit Objective 4: Code Lab Test Robustness**. Verify that the Code Lab test suites in Part 4 thoroughly validate edge cases (empty arrays, boundary numbers, negative values).

---

# Part 1: JavaScript Fundamentals (Runtime & Core Syntax) — Module Architecture

## 1. Module Rationale & Scope
TypeScript does not alter runtime JavaScript semantics. Every syntactic and semantic rule of ECMAScript executes identically after TypeScript type erasure. Developers who skip JavaScript fundamentals inevitably struggle with TypeScript because type errors often disguise underlying misunderstandings of JavaScript's memory model, truthiness, or asynchronous event loop.

## 2. Learning Outcomes
Upon mastering Part 1, the learner will be able to:
1. Differentiate the 7 primitive types from heap-allocated reference objects.
2. Explain the execution phases of JavaScript engines: Lexical Environment creation, Variable Hoisting, Temporal Dead Zone (TDZ), and block scope.
3. Predict type coercion outcomes across `==` vs `===` and master all 8 falsy values.
4. Explain Lexical Closures, arrow function `this` binding, and execution contexts.
5. Model prototypal inheritance chains (`[[Prototype]]`) up to `Object.prototype`.
6. Predict microtask vs macrotask execution order in the single-threaded Event Loop.

## 3. Subtree Inventory
- **01 - Values, Variables & Primitive Types** (Cards #00–#04): Primitives, `let`/`const`/`var`, `null` vs `undefined`, `typeof null` bug, template literals.
- **02 - Operators, Equality & Conditionals** (Cards #05–#08): Strict equality, complete falsy value set, short-circuit `&&`, `||`, `??`, ternary expressions.
- **03 - Functions, Callbacks & Scope** (Cards #09–#12): Declarations vs expressions, arrow functions (`this` immutability), closures, rest parameters.
- **04 - Objects, Prototypes & Destructuring** (Cards #13–#16): Object destructuring & defaults, spread cloning (`...`), prototype chain lookup, optional chaining (`?.`).
- **05 - Arrays & Iteration Methods** (Cards #17–#21): Mutating vs non-mutating methods, `.map()` invariant, `.filter()`, `.reduce()` accumulator rules, `for...of` vs `for...in`.
- **06 - Asynchronous JavaScript (Promises & Async/Await)** (Cards #22–#25): Event loop queues, Promise states & immutability, `async`/`await` desugaring, `Promise.all()` failure semantics.

## 4. LLM Audit Checklist for Part 1
- Verify that `null` vs `undefined` accurately describes engine initialization vs author intent.
- Verify that the 8 falsy values list is complete: `false`, `0`, `-0`, `0n`, `""`, `null`, `undefined`, `NaN`.
- Verify that the Closure explanation explicitly mentions the retention of the outer Lexical Environment via heap allocation.

---

# 01 - Values, Variables & Primitive Types — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 0 in Part 1 (Global Card Range: #00 to #04)
- **Priority**: 90 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `javascript.fundamentals.primitives_and_variables`
- **Primary References**: 
  - MDN Web Docs: *JavaScript data types and data structures*
  - ECMAScript Specification: *The Lexical Environment and Lexical Declarations*

## 2. Core Theorems & Mechanics
1. **Value Taxonomy**: JavaScript has exactly 7 primitive types (`string`, `number`, `boolean`, `null`, `undefined`, `symbol`, `bigint`). Primitives are immutable and compared by value. All other values are reference `Objects` stored on the heap and compared by memory reference.
2. **Variable Scoping Matrix**:
   - `var`: Function-scoped, hoisted and initialized to `undefined`, re-declarable.
   - `let`: Block-scoped, hoisted but uninitialized (inhabits Temporal Dead Zone until declaration line), re-assignable.
   - `const`: Block-scoped, hoisted but uninitialized (TDZ), requires immediate initialization, immutable binding (reference cannot be reassigned; interior properties of objects remain mutable).
3. **`null` vs `undefined`**:
   - `undefined`: The default value assigned by the JS engine to uninitialized variables, missing arguments, or non-existent properties.
   - `null`: An intentional assignment signifying the deliberate absence of any object value.
4. **The `typeof null === "object"` Quirk**: In JS 1995, values were represented with type tags in their lower bits (`000` designated an object). `null` was represented as the NULL pointer (`0x00`), causing `typeof` to mistakenly read the `000` tag as object.
5. **Template Literals**: Enclosed by backticks (`` ` ``); support `${expression}` interpolation, multiline formatting, and tagged template parsing.

## 3. Detailed Card Inventory
- **Card #00 (Global #0)**: *What are the 7 primitive data types in JavaScript, and how do they fundamentally differ from objects?*
  - Answer: 7 primitives (`string`, `number`, `boolean`, `null`, `undefined`, `symbol`, `bigint`). Primitives are immutable & value-compared; objects are mutable & reference-compared.
- **Card #01 (Global #1)**: *Compare `let`, `const`, and `var` in JavaScript regarding scoping, reassignment, and hoisting.*
  - Answer: `var` is function-scoped & initialized to `undefined`; `let`/`const` are block-scoped and enter TDZ until declared. `const` requires assignment and cannot be rebound.
- **Card #02 (Global #2)**: *What is the exact semantic difference between `null` and `undefined` in JavaScript?*
  - Answer: `undefined` = engine absence (unassigned variable, missing param); `null` = programmer-assigned intentional emptiness.
- **Card #03 (Global #3)**: *What does `typeof null` return, and why does this historical quirk exist?*
  - Answer: Returns `"object"`. Caused by 1995 C-level representation using `000` bit-tag for objects and `0x00` pointer for null.
- **Card #04 (Global #4)**: *How do Template Literals work in JavaScript, and what capabilities do they provide over traditional strings?*
  - Answer: Uses backticks; enables `${}` interpolation, multiline without `\n`, and tagged template functions.

## 4. LLM Auditor Rubric
- Check that `bigint` is explicitly listed among the 7 primitives.
- Verify that `const` explanation clarifies that internal object mutations (e.g. `obj.prop = 1`) are permitted while reassignment (`obj = {}`) is forbidden.

---

# 02 - Operators, Equality & Conditionals — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 1 in Part 1 (Global Card Range: #05 to #08)
- **Priority**: 90 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `javascript.fundamentals.operators_and_control_flow`
- **Primary References**: 
  - MDN Web Docs: *Expressions and operators — Equality comparisons and sameness*

## 2. Core Theorems & Mechanics
1. **Strict (`===`) vs Loose (`==`) Equality**:
   - `===` checks both value AND type without coercion.
   - `==` performs implicit type coercion via the abstract `IsLooselyEqual` algorithm (converting strings to numbers, booleans to numbers, and objects to primitives via `[Symbol.toPrimitive]`/`valueOf`/`toString`). This creates unintuitive results like `"" == 0` (true) or `[] == ![]` (true).
2. **Exhaustive Falsy Set**:
   In JavaScript, exactly 8 values coerce to `false` in a boolean context:
   `false`, `0`, `-0`, `0n` (BigInt zero), `""` (empty string), `null`, `undefined`, `NaN`.
   *Everything else* is truthy (including empty arrays `[]`, empty objects `{}`, and `"false"`).
3. **Short-Circuit Logical Operators**:
   - `a && b`: Returns `a` if `a` is falsy; otherwise evaluates and returns `b`.
   - `a || b`: Returns `a` if `a` is truthy; otherwise evaluates and returns `b`.
   - `a ?? b` (Nullish Coalescing): Returns `b` ONLY if `a` is `null` or `undefined`. If `a` is `0`, `""`, or `false`, it returns `a` (unlike `||`).
4. **Conditional (Ternary) Operator**:
   - `condition ? exprIfTrue : exprIfFalse`: A concise expression returning a value, ideal for inline variable initialization without mutable `let`.

## 3. Detailed Card Inventory
- **Card #05 (Global #5)**: *Why is strict equality (`===`) always preferred over loose equality (`==`) in JavaScript?*
  - Answer: `===` prevents implicit type coercion bugs and compares both type and value.
- **Card #06 (Global #6)**: *What are all the falsy values in JavaScript?*
  - Answer: Exactly 8: `false`, `0`, `-0`, `0n`, `""`, `null`, `undefined`, `NaN`.
- **Card #07 (Global #7)**: *How does short-circuit evaluation work for `&&`, `||`, and `??` (Nullish Coalescing)?*
  - Answer: `&&` returns first falsy; `||` returns first truthy; `??` returns right side only on `null` or `undefined`.
- **Card #08 (Global #8)**: *What is the syntax of the ternary operator, and when should it be used?*
  - Answer: `cond ? exprT : exprF`. Use for concise inline assignments; avoid nested chains.

## 4. LLM Auditor Rubric
- Confirm that `-0` and `0n` are documented in the falsy values list.
- Confirm the distinction between `||` (fails on `0` and `""`) and `??` (retains `0` and `""`).

---

# 03 - Functions, Callbacks & Scope — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 2 in Part 1 (Global Card Range: #09 to #12)
- **Priority**: 90 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `javascript.fundamentals.functions_and_closures`
- **Primary References**: 
  - MDN Web Docs: *Functions & Closures*
  - ECMAScript Specification: *Function Definitions & Arrow Function Definitions*

## 2. Core Theorems & Mechanics
1. **Function Declarations vs Function Expressions**:
   - *Declarations* (`function foo() {}`): Hoisted with both identifier and full body. Can be called before their syntactic declaration line.
   - *Expressions* (`const foo = function() {}`): Variable identifier hoisted according to `const`/`let` (TDZ) or `var` (`undefined`); function body assigned only at runtime evaluation line.
2. **Arrow Functions (`() => {}`) vs Traditional Functions**:
   - Arrow functions have **lexical `this`** bound to enclosing lexical scope at creation time. They cannot be rebound using `.bind()`, `.call()`, or `.apply()`.
   - Arrow functions lack their own `arguments` object, `super`, and `new.target`, and **cannot be used as constructors** (calling `new Arrow()` throws TypeError).
3. **Lexical Closures**:
   - A closure is the combination of a function bundled together with references to its surrounding lexical state (`LexicalEnvironment`).
   - Enables a function to access variables in an outer scope even after the outer function has returned and exited the call stack. The engine preserves the lexical environment on the heap.
4. **Rest Parameters (`...args`)**:
   - Standardized syntax collecting indefinite remaining arguments into a true JavaScript `Array`. Replaces the legacy, array-like `arguments` object. Must be the final parameter.

## 3. Detailed Card Inventory
- **Card #09 (Global #9)**: *What is the key difference between a Function Declaration and a Function Expression regarding hoisting?*
  - Answer: Declarations are fully hoisted (callable prior to definition); expressions are bound to variables subject to TDZ.
- **Card #10 (Global #10)**: *What are the core differences between traditional functions and Arrow Functions?*
  - Answer: Arrow functions have lexical `this`, lack `arguments`, and cannot be invoked with `new`.
- **Card #11 (Global #11)**: *What is a Closure in JavaScript, and what makes it powerful?*
  - Answer: A function retaining access to its parent lexical environment after the parent returns, enabling state encapsulation.
- **Card #12 (Global #12)**: *How do Rest Parameters (`...args`) work, and why do they replace the legacy `arguments` object?*
  - Answer: Collects remaining parameters into a true `Array` instance with array methods, unlike array-like `arguments`.

## 4. LLM Auditor Rubric
- Verify that arrow function `this` binding is accurately identified as immutable and lexically scoped.
- Verify closure explanation references lexical scope persistence on the heap.

---

# 04 - Objects, Prototypes & Destructuring — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 3 in Part 1 (Global Card Range: #13 to #16)
- **Priority**: 90 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `javascript.fundamentals.objects_and_prototypes`
- **Primary References**: 
  - MDN Web Docs: *Working with objects & Inheritance and the prototype chain*

## 2. Core Theorems & Mechanics
1. **Object Destructuring & Aliasing**:
   - Syntax: `const { prop: aliasName = defaultValue } = obj;`. Extracts property `prop`, renames it to local variable `aliasName`, and defaults to `defaultValue` if `obj.prop === undefined`.
2. **Object Spread (`{ ...obj }`)**:
   - Creates a **shallow clone** of enumerable own properties. Nested objects retain identical reference pointers.
   - Does not preserve prototype linkage (the clone inherits from `Object.prototype`, not `obj`'s prototype).
3. **Prototypal Inheritance Chain**:
   - Every object has an internal `[[Prototype]]` link (accessible via `Object.getPrototypeOf(obj)` or legacy `__proto__`).
   - When accessing `obj.prop`, if `prop` is not an own property, the engine traverses the prototype chain up to `Object.prototype`, and finally `null`. If not found, returns `undefined`.
4. **Optional Chaining (`?.`)**:
   - Short-circuits property access (`a?.b`), method invocation (`a?.b()`), and dynamic property access (`a?.[b]`). If the target is `null` or `undefined`, the expression immediately evaluates to `undefined` without throwing `TypeError`.

## 3. Detailed Card Inventory
- **Card #13 (Global #13)**: *How does Object Destructuring work with property renaming and default values?*
  - Answer: `const { key: alias = defaultVal } = obj;` renames `key` to `alias` and falls back if `undefined`.
- **Card #14 (Global #14)**: *What does the Object Spread Operator (`...`) do, and is it deep or shallow?*
  - Answer: Copies enumerable own properties shallowly. Nested reference objects remain shared.
- **Card #15 (Global #15)**: *How does the Prototype Chain work when accessing a property on a JavaScript object?*
  - Answer: Engine searches own properties, then traverses `[[Prototype]]` upwards until `Object.prototype` and `null`.
- **Card #16 (Global #16)**: *How does Optional Chaining (`?.`) prevent runtime exceptions in JavaScript?*
  - Answer: Evaluates to `undefined` if reference is `null` or `undefined`, halting navigation safely.

## 4. LLM Auditor Rubric
- Check that Object Spread is explicitly verified as shallow.
- Check that default destructuring triggers only on `undefined` (not on `null`).

---

# 05 - Arrays & Iteration Methods — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 4 in Part 1 (Global Card Range: #17 to #21)
- **Priority**: 90 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `javascript.fundamentals.arrays_and_iteration`
- **Primary References**: 
  - MDN Web Docs: *Array methods & Iteration protocols*

## 2. Core Theorems & Mechanics
1. **Mutating vs Non-Mutating Array Operations**:
   - *Mutating (In-place)*: `push`, `pop`, `shift`, `unshift`, `splice`, `sort`, `reverse`, `fill`.
   - *Non-Mutating (Pure/Immutable)*: `map`, `filter`, `reduce`, `slice`, `concat`, `flat`, `toSorted`, `toReversed`, `toSpliced`.
2. **The `.map()` Invariant**:
   - Always returns a new array of the **exact same length** as the original array, applying the transformer callback to every element.
3. **The `.filter()` Invariant**:
   - Returns a new array containing only elements for which the predicate callback returns a truthy value. Length is always $\le$ source length.
4. **The `.reduce()` Accumulator Invariant**:
   - Iteratively folds an array into a single accumulated result: `arr.reduce((acc, curr, index, arr) => nextAcc, initialValue)`.
   - *Mandatory Practice*: Always supply `initialValue`. Omitting it causes empty array to throw `TypeError: Reduce of empty array with no initial value` and skips index 0.
5. **`for...of` vs `for...in`**:
   - `for...of`: Iterates over the **values** of an iterable object (`Array`, `Map`, `Set`, `String`) conforming to `[Symbol.iterator]`.
   - `for...in`: Enumerates all enumerable **property keys** (strings) of an object, including inherited properties on the prototype chain.

## 3. Detailed Card Inventory
- **Card #17 (Global #17)**: *Which common JavaScript array methods mutate the original array, and which return a new array?*
  - Answer: Mutating: `push`, `pop`, `splice`, `sort`. Non-mutating: `map`, `filter`, `slice`, `concat`, `toSorted`.
- **Card #18 (Global #18)**: *What does `.map()` do, and what invariant does it guarantee regarding array length?*
  - Answer: Returns new array applying callback to each item; guaranteed exact same length as source array.
- **Card #19 (Global #19)**: *How does `.filter()` work, and what determines whether an element is included in the output?*
  - Answer: Returns subset where predicate returns truthy value.
- **Card #20 (Global #20)**: *How does `.reduce()` accumulate values, and why should you always supply an initial value?*
  - Answer: Accumulates collection into single value; initial value prevents empty array `TypeError`.
- **Card #21 (Global #21)**: *What is the crucial difference between `for...of` and `for...in` loops in JavaScript?*
  - Answer: `for...of` iterates iterable values; `for...in` enumerates object keys including prototype chain.

## 4. LLM Auditor Rubric
- Verify that modern non-mutating methods (`toSorted`, `toReversed`) are acknowledged.
- Verify warning about omitting `initialValue` in `.reduce()`.

---

# 06 - Asynchronous JavaScript (Promises & Async/Await) — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 5 in Part 1 (Global Card Range: #22 to #25)
- **Priority**: 90 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `javascript.fundamentals.async_event_loop`
- **Primary References**: 
  - MDN Web Docs: *Asynchronous JavaScript & Event loop*
  - ECMAScript Specification: *Promise Objects & AsyncFunction Definitions*

## 2. Core Theorems & Mechanics
1. **The Single-Threaded Event Loop**:
   - JavaScript execution runs on a single main thread with a synchronous Call Stack.
   - Asynchronous operations are delegated to runtime APIs (browser Web APIs or Node.js libuv thread pool).
   - When operations complete, their callbacks enter queues:
     - **Microtask Queue**: Promise handlers (`.then`, `.catch`, `.finally`), `queueMicrotask`, `process.nextTick`. Drain to completion after every stack frame, BEFORE the next macrotask.
     - **Macrotask (Task) Queue**: `setTimeout`, `setInterval`, I/O, UI rendering events.
2. **Promise State Lifecycle & Immutability**:
   - A Promise has 3 mutually exclusive states: `pending`, `fulfilled`, or `rejected`.
   - Once a Promise transitions to `fulfilled` or `rejected`, it is **settled** and its state and resolved value become permanently immutable. Further resolve/reject calls are silently ignored.
3. **`async` / `await` Under the Hood**:
   - Syntactic sugar over Promises and Generators. An `async` function always returns a Promise (wrapping non-promise returns via `Promise.resolve()`).
   - The `await` keyword suspends function execution non-blockingly, yielding control back to the event loop, and resumes execution as a microtask when the awaited promise settles.
4. **`Promise.all()` Short-Circuit Failure**:
   - Takes an iterable of Promises and returns a single Promise resolving to an array of results.
   - **Fast-fails**: If any promise rejects, `Promise.all()` immediately rejects with that reason, abandoning waiting on remaining unresolved promises (though remaining operations still execute in background).
   - Use `Promise.allSettled()` when you need all outcomes regardless of rejection.

## 3. Detailed Card Inventory
- **Card #22 (Global #22)**: *How does the JavaScript Event Loop manage asynchronous tasks on a single thread?*
  - Answer: Single thread with Call Stack; drains Microtask Queue (Promises) completely before executing Macrotask Queue (`setTimeout`).
- **Card #23 (Global #23)**: *What are the 3 states of a JavaScript Promise, and can a settled Promise change state?*
  - Answer: `pending`, `fulfilled`, `rejected`. Once settled, state and value are immutable.
- **Card #24 (Global #24)**: *How do `async` and `await` work under the hood with Promises?*
  - Answer: Desugars to Promises; `async` wraps returns in Promise; `await` pauses execution non-blockingly until microtask resumes.
- **Card #25 (Global #25)**: *How does `Promise.all()` behave when executing concurrent asynchronous operations, and what is its failure mode?*
  - Answer: Runs concurrently; resolves when all fulfill; immediately fast-fails on first rejection.

## 4. LLM Auditor Rubric
- Check that microtask priority over macrotasks is correctly articulated.
- Check that `Promise.all` failure behavior is contrasted with `Promise.allSettled`.

---

# Part 2: TypeScript Core (Static Types as a Safety Layer) — Module Architecture

## 1. Module Rationale & Scope
Part 2 introduces TypeScript's static type checker (`tsc`) as a purely compile-time analytical layer. The overarching goal is mastering the mental model: **Types exist exclusively at compile-time to prove structural invariants, after which type erasure eliminates them entirely.**

## 2. Learning Outcomes
Upon completing Part 2, the learner will be able to:
1. Explain Type Erasure and why TypeScript cannot perform runtime data validation.
2. Formulate correct type annotations vs relying on contextual type inference.
3. Employ set-theoretic Top types (`unknown`, `any`) and Bottom type (`never`) safely.
4. Leverage structural subtyping ("duck typing") and understand excess property checks.
5. Apply control-flow narrowing using `typeof`, `instanceof`, `in`, and custom type predicates (`val is Type`).
6. Model function types, optional/default parameters, and understand `void` vs `undefined`.

## 3. Subtree Inventory
- **07 - The Mental Model & Type Erasure** (Cards #26–#29): TS role, type erasure, runtime boundary limitations (API data), Playground tool.
- **08 - Primitive Annotations & Type Inference** (Cards #30–#33): When to annotate vs infer, `any` vs `unknown`, `never` applications, Arrays vs Tuples.
- **09 - Object Shapes & Interfaces** (Cards #34–#36): `interface` contracts, structural typing semantics, excess property checks on fresh object literals.
- **10 - Union Types & Control-Flow Narrowing** (Cards #37–#39): Union types (`A | B`), built-in narrowing guards, custom type predicates.
- **11 - Function Signatures & Typing** (Cards #40–#42): `void` return semantics, optional/default parameters, function overload signatures.

## 4. LLM Audit Checklist for Part 2
- Verify that `unknown` is presented as the type-safe alternative to `any`.
- Verify that structural typing emphasizes compatibility by member shape rather than nominal declaration.
- Verify that `void` allows returning non-undefined values in callback positions for compatibility.

---

# 07 - The Mental Model & Type Erasure — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 0 in Part 2 (Global Card Range: #26 to #29)
- **Priority**: 80 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `typescript.core.mental_model_and_type_erasure`
- **Primary References**: 
  - TypeScript Handbook: *TypeScript for the New Programmer* & *TypeScript for JavaScript Programmers*

## 2. Core Theorems & Mechanics
1. **TypeScript's Fundamental Role**:
   - TypeScript is a static type checker that analyzes JavaScript code at authoring and build time. It issues compiler diagnostics without modifying how the code executes.
2. **Type Erasure**:
   - The TypeScript compiler strips all type annotations, interfaces, type aliases, and type parameters during transpilation, emitting standard JavaScript.
   - Result: Types have **zero runtime overhead** and **zero runtime footprint**. You cannot inspect a TypeScript type at runtime via `typeof` or reflection.
3. **The Runtime Safety Boundary**:
   - Because types are erased, TypeScript **cannot validate untrusted runtime inputs** (e.g. `fetch()` JSON payloads, `localStorage`, form inputs).
   - If an API returns malformed JSON, TypeScript types will not throw an error at the boundary; code will fail at runtime unless validated using runtime validators (Zod, Valibot) or type guards.
4. **TypeScript Playground**:
   - Interactive REPL exposing compiler flags, side-by-side JS emitted code, and generated `.d.ts` declaration files. Essential for verifying how static types transpile to JavaScript.

## 3. Detailed Card Inventory
- **Card #26 (Global #26)**: *What is TypeScript's fundamental role in relation to JavaScript?*
  - Answer: Static type checker operating at compile-time to detect errors before runtime without changing JS behavior.
- **Card #27 (Global #27)**: *What is 'Type Erasure' in TypeScript, and what is its impact on runtime performance and bundle size?*
  - Answer: Transpiler completely removes all type syntax; results in zero runtime overhead and zero added runtime bundle size.
- **Card #28 (Global #28)**: *Can TypeScript types validate API responses or user input at runtime? Why or why not?*
  - Answer: No; types are erased. Runtime data requires explicit type guards or schema validation libraries (Zod).
- **Card #29 (Global #29)**: *What makes the official TypeScript Playground such an effective tool for understanding type behavior?*
  - Answer: Shows live TS-to-JS compilation, `.d.ts` output, and allows testing compiler flags (`strict`, `target`).

## 4. LLM Auditor Rubric
- Check that type erasure is explicitly highlighted as the reason runtime validation libraries are necessary.

---

# 08 - Primitive Annotations & Type Inference — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 1 in Part 2 (Global Card Range: #30 to #33)
- **Priority**: 80 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `typescript.core.annotations_and_inference`
- **Primary References**: 
  - TypeScript Handbook: *Everyday Types* & *Type Inference*

## 2. Core Theorems & Mechanics
1. **Annotation vs Inference Best Practice**:
   - TypeScript automatically infers types from literal initializers (`let x = 10` -> `number`).
   - *Best Practice*: Rely on inference for local variables initialized immediately. Annotate function parameters, complex return types, and uninitialized variables.
2. **Top Types: `any` vs `unknown`**:
   - `any`: Disables all type-checking. Allows arbitrary property access and invocation. Propagates unchecked ("type contagion").
   - `unknown`: Safe top type. Represents any value, but **forbids any property access, method calls, or operations** until narrowed using type guards.
3. **Bottom Type: `never`**:
   - The empty set ($\emptyset$) containing no values. Represents values that can never occur:
     - Return type of functions that never return (infinite loops or functions that always throw).
     - Exhaustive check in `switch`/`if-else` blocks (assigning an unhandled branch to `never` produces compile-time error).
4. **Arrays vs Tuples**:
   - `T[]` (or `Array<T>`): Variable-length homogeneous list of elements of type `T`.
   - `[T1, T2, ...Tn]`: Fixed-length sequence with strict types at specific index positions (e.g. `[string, number]`).

## 3. Detailed Card Inventory
- **Card #30 (Global #30)**: *When should you write explicit type annotations, and when should you rely on TypeScript's Type Inference?*
  - Answer: Infer initialized local variables; annotate function parameters, exported API returns, and uninitialized variables.
- **Card #31 (Global #31)**: *What is the crucial difference between the `any` type and the `unknown` type in TypeScript?*
  - Answer: `any` disables type-checking; `unknown` is type-safe and requires narrowing before usage.
- **Card #32 (Global #32)**: *What is the `never` type in TypeScript, and what are its two primary use cases?*
  - Answer: Bottom type representing impossible values. Used for functions that throw/loop forever and exhaustive switch checks.
- **Card #33 (Global #33)**: *What is the difference between an Array type (`number[]`) and a Tuple (`[string, number]`) in TypeScript?*
  - Answer: Array is variable-length homogeneous; Tuple is fixed-length with specific types per index.

## 4. LLM Auditor Rubric
- Confirm set-theoretic framing: `unknown` = universal set, `never` = empty set.

---

# 09 - Object Shapes & Interfaces — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 2 in Part 2 (Global Card Range: #34 to #36)
- **Priority**: 80 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `typescript.core.interfaces_and_structural_typing`
- **Primary References**: 
  - TypeScript Handbook: *Everyday Types — Interfaces* & *Object Types*

## 2. Core Theorems & Mechanics
1. **Defining Object Contracts with `interface`**:
   - Declares the required shape of an object: property names, types, optional properties (`?`), and immutable properties (`readonly`).
2. **Structural Typing (Duck Typing)**:
   - TypeScript compares types based solely on their **shape/members**, not their nominal declaration or class name.
   - If object $B$ possesses all properties required by type $A$ (with compatible types), $B$ is assignable to $A$, even if $B$ has extra properties:
     $$B 	ext{ extends } A \iff B \subseteq A 	ext{ in value space (has at least all keys of } A)$$
3. **Excess Property Checks**:
   - When assigning a **fresh object literal** directly to an annotated location (`const u: User = { name: "A", extra: 1 }`), TypeScript applies strict excess property checks and flags unexpected keys as errors.
   - Passing an existing object reference (`const tmp = { name: "A", extra: 1 }; const u: User = tmp;`) bypasses excess property checks due to structural compatibility.

## 3. Detailed Card Inventory
- **Card #34 (Global #34)**: *How do you define an object contract using a TypeScript `interface`?*
  - Answer: `interface User { id: string; name: string; age?: number; readonly createdAt: Date; }`
- **Card #35 (Global #35)**: *What is 'Structural Typing' (Duck Typing) in TypeScript?*
  - Answer: Type compatibility is based on property shape rather than explicit nominal declarations.
- **Card #36 (Global #36)**: *What are Excess Property Checks in TypeScript, and when are they triggered?*
  - Answer: Strict checks flagging unknown properties when assigning fresh object literals directly.

## 4. LLM Auditor Rubric
- Check that excess property checks are clearly differentiated from general structural subtyping.

---

# 10 - Union Types & Control-Flow Narrowing — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 3 in Part 2 (Global Card Range: #37 to #39)
- **Priority**: 80 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `typescript.core.unions_and_narrowing`
- **Primary References**: 
  - TypeScript Handbook: *Narrowing*

## 2. Core Theorems & Mechanics
1. **Union Types (`A | B`)**:
   - Represents a value that can be *either* type `A` or type `B`.
   - Before narrowing, TypeScript only permits accessing properties common to **all** members of the union ($A \cap B$ in property space).
2. **Control-Flow Narrowing**:
   - The compiler analyzes branching paths (`if`, `switch`, ternaries) and refines broad types into more specific types.
   - Built-in type guards:
     - `typeof x === "string"`: Narrows primitive types.
     - `x instanceof Date`: Narrows constructor/class instances.
     - `"prop" in x`: Narrows object shapes containing property `"prop"`.
     - Strict equality checks (`x === null`, `x === undefined`, `x === "literal"`).
3. **Custom Type Predicates (`val is Type`)**:
   - A function returning a boolean whose return type annotation is `parameterName is TargetType`.
   - When the function returns `true`, TypeScript narrows `parameterName` to `TargetType` inside the conditional block:
     ```typescript
     function isFish(pet: Fish | Bird): pet is Fish {
       return (pet as Fish).swim !== undefined;
     }
     ```

## 3. Detailed Card Inventory
- **Card #37 (Global #37)**: *What is a Union Type (`A | B`), and what properties can you access on an un-narrowed union?*
  - Answer: Represents values of either type; only properties shared by all union constituents are accessible prior to narrowing.
- **Card #38 (Global #38)**: *What is Control Flow Narrowing, and what are the 4 most common built-in type guards?*
  - Answer: Compiler path analysis refining broad types. 4 guards: `typeof`, `instanceof`, `in`, equality checks.
- **Card #39 (Global #39)**: *How do you write a Custom Type Guard using a Type Predicate (`val is Type`)?*
  - Answer: Return boolean with signature `param is TargetType`; compiler narrows on truthy branch.

## 4. LLM Auditor Rubric
- Check that custom type predicate syntax is explicitly demonstrated with `val is Type`.

---

# 11 - Function Signatures & Typing — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 4 in Part 2 (Global Card Range: #40 to #42)
- **Priority**: 80 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `typescript.core.function_signatures`
- **Primary References**: 
  - TypeScript Handbook: *More on Functions*

## 2. Core Theorems & Mechanics
1. **The `void` Return Type**:
   - Signifies that a function does not return a meaningful value for the caller to observe.
   - *Key distinction from `undefined`*: A function typed to return `undefined` must explicitly return `undefined` or have an empty `return;`. A callback typed with `() => void` can return any value (e.g. `Array.prototype.push`), but callers are warned not to use that returned value.
2. **Optional and Default Parameters**:
   - Optional parameters use `?` (e.g. `x?: number`) and receive the type `number | undefined`. Must appear after required parameters.
   - Default parameters (e.g. `x = 10`) infer their type and are automatically optional for callers.
3. **Function Overloads**:
   - Provide multiple call signatures followed by a single implementation signature.
   - Only the overload signatures are visible to external callers; the implementation signature is internal and must be broad enough to handle all overloads.

## 3. Detailed Card Inventory
- **Card #40 (Global #40)**: *What does a `void` return type signify in TypeScript, and how does it differ from returning `undefined`?*
  - Answer: `void` means return value is ignored by callers; `undefined` requires explicit return of undefined.
- **Card #41 (Global #41)**: *What are the rules for Optional Parameters and Default Parameters in TypeScript functions?*
  - Answer: Optional parameters (`param?: type`) must follow required params; default values infer type and become optional.
- **Card #42 (Global #42)**: *How do Function Overloads work in TypeScript, and what is the relationship between overload signatures and implementation?*
  - Answer: Declare multiple public callable signatures followed by one private compatible implementation.

## 4. LLM Auditor Rubric
- Confirm that callback `void` assignability (why `forEach` callback can return a number) is correctly distinguished from direct `undefined` returns.

---

# Part 3: Intermediate TypeScript & System Design — Module Architecture

## 1. Module Rationale & Scope
Part 3 transitions from basic syntax annotations to intermediate type calculus and architectural system design. It teaches developers how to construct robust, type-safe domain models that make illegal program states unrepresentable.

## 2. Learning Outcomes
Upon completing Part 3, the learner will be able to:
1. Choose judiciously between `interface` (OOP contracts, declaration merging) and `type` aliases (unions, primitives, tuples).
2. Model domain entities using Discriminated (Tagged) Unions and enforce compile-time exhaustiveness with `never`.
3. Author generic functions and interfaces with strict `extends` and `keyof` constraints.
4. Utilize TypeScript's built-in utility transformations (`Partial`, `Pick`, `Omit`, `Record`).
5. Configure `tsconfig.json` in strict mode (`strictNullChecks`, `noImplicitAny`).

## 3. Subtree Inventory
- **12 - Type Aliases vs Interfaces & Extensibility** (Cards #43–#44): `type` vs `interface`, declaration merging, intersection types (`&`).
- **13 - Discriminated Unions & Exhaustiveness** (Cards #45–#46): Tagged union state modeling, exhaustiveness check with `never`.
- **14 - Generics: Functions, Interfaces & Constraints** (Cards #47–#49): Parameterized types (`<T>`), constraints with `extends`, `keyof` indexed lookup.
- **15 - Essential Utility Types (Partial, Pick, Omit, Record)** (Cards #50–#52): `Partial`/`Readonly`, `Pick`/`Omit`, `Record<K, V>`.
- **16 - TypeScript Tooling, tsconfig & Strict Mode** (Cards #53–#55): `"strict": true` suite, `strictNullChecks` protection, `.d.ts` declaration files.

## 4. LLM Audit Checklist for Part 3
- Verify that `interface` declaration merging is explicitly explained.
- Verify that the Discriminated Union pattern demonstrates making impossible states unrepresentable (avoiding multiple optional booleans).
- Verify generic property extraction uses `<T, K extends keyof T>(obj: T, key: K): T[K]`.

---

# 12 - Type Aliases vs Interfaces & Extensibility — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 0 in Part 3 (Global Card Range: #43 to #44)
- **Priority**: 70 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `typescript.intermediate.types_vs_interfaces`
- **Primary References**: 
  - TypeScript Handbook: *Everyday Types — Differences Between Type Aliases and Interfaces*

## 2. Core Theorems & Mechanics
1. **`interface` vs `type` Aliases**:
   - `interface`: Open for extension via **Declaration Merging** (multiple declarations of the same interface name merge their fields). Extends other interfaces via `extends`. Best for object contracts, library APIs, and public OOP models.
   - `type`: Closed (cannot declaration-merge). Can define unions (`A | B`), intersections (`A & B`), primitives, tuples, and mapped types.
2. **Intersection Types (`A & B`)**:
   - Combines multiple object shapes into a single type containing all fields from all constituent types.
   - If properties have conflicting primitive types (e.g. `{ id: string } & { id: number }`), the resulting property type collapses to `never`.

## 3. Detailed Card Inventory
- **Card #43 (Global #43)**: *What are the key technical differences between `type` aliases and `interface` in TypeScript?*
  - Answer: Interfaces support declaration merging and `extends`; type aliases can represent unions, primitives, tuples, and cannot re-open.
- **Card #44 (Global #44)**: *What is an Intersection Type (`&`) in TypeScript, and what happens when properties conflict?*
  - Answer: Combines all properties of constituents; conflicting primitive types collapse to `never`.

## 4. LLM Auditor Rubric
- Check that declaration merging is clearly identified as unique to `interface`.

---

# 13 - Discriminated Unions & Exhaustiveness — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 1 in Part 3 (Global Card Range: #45 to #46)
- **Priority**: 70 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `typescript.intermediate.discriminated_unions`
- **Primary References**: 
  - TypeScript Handbook: *Narrowing — Discriminated unions*

## 2. Core Theorems & Mechanics
1. **Discriminated (Tagged) Unions**:
   - A union of object types where every member contains a shared, common property with a unique literal singleton value (the "discriminant", e.g. `status: "idle" | "loading" | "success" | "error"`).
   - Prevents invalid state combinations (e.g. `{ isLoading: true, isSuccess: true, data: null, error: Error }`).
2. **Exhaustiveness Checking with `never`**:
   - By asserting that the `default` case of a `switch` statement has type `never`, the compiler will report an error if a developer adds a new variant to the union without handling it:
     ```typescript
     function handleState(s: State) {
       switch (s.status) {
         case "idle": return;
         case "success": return s.data;
         default: {
           const _exhaustiveCheck: never = s; // Compile error if variant missed!
           throw new Error(`Unhandled state: ${_exhaustiveCheck}`);
         }
       }
     }
     ```

## 3. Detailed Card Inventory
- **Card #45 (Global #45)**: *What is a Discriminated Union (Tagged Union), and why is it considered the gold standard for state modeling in TypeScript?*
  - Answer: Objects sharing a literal discriminant key. Makes impossible states unrepresentable.
- **Card #46 (Global #46)**: *How do you implement compile-time Exhaustiveness Checking using the `never` type?*
  - Answer: Assign unhandled case to `never` variable; compiler raises error if any variant is unhandled.

## 4. LLM Auditor Rubric
- Verify that the `const _exhaustive: never = s;` pattern is accurately detailed.

---

# 14 - Generics: Functions, Interfaces & Constraints — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 2 in Part 3 (Global Card Range: #47 to #49)
- **Priority**: 70 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `typescript.intermediate.generics`
- **Primary References**: 
  - TypeScript Handbook: *Generics*

## 2. Core Theorems & Mechanics
1. **Why Generics over `any`?**:
   - `any` loses all type relationships between inputs and outputs.
   - Generics introduce type variables (`<T>`) that capture the caller's specific type, preserving type safety throughout function execution and return values.
2. **Generic Constraints (`extends`)**:
   - Prevents arbitrary types from being passed when specific capabilities are required:
     ```typescript
     function logLength<T extends { length: number }>(item: T): number {
       return item.length;
     }
     ```
3. **The `keyof` Operator & Indexed Access**:
   - `keyof T` produces a union of all property name literals of type `T`.
   - Constraining `<K extends keyof T>` ensures that `key` is a valid property name on `obj: T`, allowing TypeScript to infer the exact return type as `T[K]`.

## 3. Detailed Card Inventory
- **Card #47 (Global #47)**: *Why are Generics used in TypeScript instead of `any`?*
  - Answer: Captures and preserves type identity between inputs and outputs without losing type checking.
- **Card #48 (Global #48)**: *How do you constrain a Generic type parameter using `extends`?*
  - Answer: Use `<T extends Constraint>` to restrict `T` to types satisfying the constraint interface.
- **Card #49 (Global #49)**: *How do you safely extract a property from an object using Generics and the `keyof` operator?*
  - Answer: `function getProp<T, K extends keyof T>(obj: T, key: K): T[K] { return obj[key]; }`

## 4. LLM Auditor Rubric
- Check that the `keyof` indexed access signature `<T, K extends keyof T>(obj: T, key: K): T[K]` is mathematically accurate.

---

# 15 - Essential Utility Types (Partial, Pick, Omit, Record) — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 3 in Part 3 (Global Card Range: #50 to #52)
- **Priority**: 70 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `typescript.intermediate.utility_types`
- **Primary References**: 
  - TypeScript Handbook: *Utility Types*

## 2. Core Theorems & Mechanics
1. **`Partial<T>` & `Readonly<T>`**:
   - `Partial<T>`: Constructs a type with all properties of `T` set to optional (`?`). Ideal for patch/update payloads.
   - `Readonly<T>`: Constructs a type with all properties set to `readonly`, preventing property reassignment.
2. **`Pick<T, Keys>` vs `Omit<T, Keys>`**:
   - `Pick<T, Keys>`: Constructs a type by picking a subset of keys (`Keys extends keyof T`) from `T`.
   - `Omit<T, Keys>`: Constructs a type by removing a subset of keys from `T`.
3. **`Record<Keys, Value>`**:
   - Constructs an object type whose property keys are `Keys` and values are `Value`:
     `Record<"admin" | "user", Permissions>`

## 3. Detailed Card Inventory
- **Card #50 (Global #50)**: *What do `Partial<T>` and `Readonly<T>` do in TypeScript?*
  - Answer: `Partial` makes all properties optional; `Readonly` prevents reassigning properties.
- **Card #51 (Global #51)**: *How do `Pick<T, Keys>` and `Omit<T, Keys>` differ in transforming object types?*
  - Answer: `Pick` selects specified keys; `Omit` excludes specified keys.
- **Card #52 (Global #52)**: *What is `Record<Keys, Value>` used for in TypeScript?*
  - Answer: Creates dictionary type mapping a set of union keys to a specific value type.

## 4. LLM Auditor Rubric
- Check that `Record` is explained with union string keys.

---

# 16 - TypeScript Tooling, tsconfig & Strict Mode — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 4 in Part 3 (Global Card Range: #53 to #55)
- **Priority**: 70 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `typescript.intermediate.tooling_and_strict_mode`
- **Primary References**: 
  - TypeScript Handbook: *The tsconfig.json & Compiler Options*

## 2. Core Theorems & Mechanics
1. **`"strict": true` Master Setting**:
   - Enables all strict type-checking compiler flags: `strictNullChecks`, `noImplicitAny`, `strictFunctionTypes`, `strictBindCallApply`, `strictPropertyInitialization`, `noImplicitThis`, `alwaysStrict`, and `useUnknownInCatchVariables`.
2. **`strictNullChecks`**:
   - Without this flag, `null` and `undefined` are assignable to every type (`let s: string = null` succeeds), causing widespread runtime null pointer bugs.
   - With `strictNullChecks`, `null` and `undefined` become distinct types and must be explicitly handled via unions (`string | null`).
3. **Declaration Files (`.d.ts`)**:
   - Type definition files describing the API shape of JavaScript libraries without providing executable code.

## 3. Detailed Card Inventory
- **Card #53 (Global #53)**: *What does setting `"strict": true` in `tsconfig.json` do, and why is it recommended for all modern projects?*
  - Answer: Turns on entire suite of strict compiler checks, eliminating silent `any` and unhandled nulls.
- **Card #54 (Global #54)**: *How does `strictNullChecks` protect code from unexpected null pointer errors?*
  - Answer: Disallows assigning `null`/`undefined` to primitive types; forces explicit union modeling.
- **Card #55 (Global #55)**: *What is a `.d.ts` Declaration File in TypeScript?*
  - Answer: Type-only file providing TypeScript shapes for plain JavaScript libraries without emitting code.

## 4. LLM Auditor Rubric
- Check that `strictNullChecks` is cited as the guard against "Billion Dollar Mistake" null pointers.

---

# Part 4: Hands-On Code Lab Drills — Module Architecture

## 1. Module Rationale & Scope
Knowledge retention requires procedural synthesis. Part 4 provides interactive, executable Code Lab flashcards featuring embedded unit tests. Learners write code in the embedded editor and run test suites to verify runtime mechanics and TypeScript type safety.

## 2. Learning Outcomes
Upon completing Part 4, the learner will be able to:
1. Write pure JavaScript data transformation utilities using object destructuring and higher-order `.reduce()`.
2. Refactor loose JavaScript utilities into robust TypeScript with typed arguments and interfaces.
3. Author generic algorithms with bounded `extends keyof` constraints.

## 3. Subtree Inventory
- **17 - JavaScript Practice Drills** (Cards #56–#57):
  - Card #56: `formatUser({ firstName, lastName, age })` with fallback default age.
  - Card #57: `groupByCategory(items)` grouping array into dictionary via `.reduce()`.
- **18 - Refactoring JS to TS Drills** (Cards #58–#59):
  - Card #58: `clamp(value: number, min: number, max: number): number`.
  - Card #59: `CartItem` interface and `calculateTotal(items: CartItem[]): number`.
- **19 - Generics & Type-Guard Drills** (Cards #60–#61):
  - Card #60: `firstElement<T>(arr: T[]): T | undefined`.
  - Card #61: `pluck<T, K extends keyof T>(items: T[], key: K): T[K][]`.

## 4. LLM Audit Checklist for Part 4
- Verify that every Code Lab card contains test cases with assertions for valid data, empty collections, and boundary conditions.

---

# 17 - JavaScript Practice Drills — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 0 in Part 4 (Global Card Range: #56 to #57)
- **Priority**: 60 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `javascript.drills.practical_functions`
- **Primary References**: 
  - MDN Web Docs: *Array.prototype.reduce() & Destructuring assignment*

## 2. Interactive Code Lab Drills
### Drill 1 (Card #56): `formatUser`
- **Task**: Write `formatUser(user)` accepting `{ firstName, lastName, age }` and returning `"FirstName LastName (Age)"`. If `age` is missing or undefined, default to `"Unknown"`.
- **Test Suite**:
  - `formatUser({ firstName: "Ada", lastName: "Lovelace", age: 36 })` === `"Ada Lovelace (36)"`
  - `formatUser({ firstName: "Alan", lastName: "Turing" })` === `"Alan Turing (Unknown)"`

### Drill 2 (Card #57): `groupByCategory`
- **Task**: Write `groupByCategory(items)` using `.reduce()` to group an array of objects `{ id, category }` into an object mapping each category to an array of items.
- **Test Suite**:
  - Groups items into categories; handles empty array returning `{}`; handles single-item array.

## 3. LLM Auditor Rubric
- Check that destructuring defaults and empty `.reduce()` accumulator are properly tested.

---

# 18 - Refactoring JS to TS Drills — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 1 in Part 4 (Global Card Range: #58 to #59)
- **Priority**: 60 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `typescript.drills.refactoring_js_to_ts`
- **Primary References**: 
  - TypeScript Handbook: *Everyday Types & TypeScript in 5 Minutes*

## 2. Interactive Code Lab Drills
### Drill 1 (Card #58): `clamp`
- **Task**: Implement `clamp(value: number, min: number, max: number): number`. Restricts `value` between `min` and `max`.
- **Test Suite**:
  - `clamp(5, 0, 10)` === `5`
  - `clamp(-5, 0, 10)` === `0`
  - `clamp(15, 0, 10)` === `10`

### Drill 2 (Card #59): `CartItem` and `calculateTotal`
- **Task**: Define interface `CartItem` (`id: string; price: number; quantity: number`) and implement `calculateTotal(items: CartItem[]): number`.
- **Test Suite**:
  - Correctly sums `price * quantity`; handles empty array returning `0`.

## 3. LLM Auditor Rubric
- Verify that types are strictly enforced and edge case of empty cart returns 0.

---

# 19 - Generics & Type-Guard Drills — Subdeck Documentation

## 1. Domain Specification
- **Subdeck Position**: 2 in Part 4 (Global Card Range: #60 to #61)
- **Priority**: 60 | **Desired Retention**: 0.90
- **KnowledgeNode Path**: `typescript.drills.generics_and_type_guards`
- **Primary References**: 
  - TypeScript Handbook: *Generics & Narrowing*

## 2. Interactive Code Lab Drills
### Drill 1 (Card #60): `firstElement<T>`
- **Task**: Implement `firstElement<T>(arr: T[]): T | undefined`.
- **Test Suite**:
  - `firstElement([1, 2, 3])` === `1` (inferred return: `number | undefined`)
  - `firstElement(["a", "b"])` === `"a"` (inferred return: `string | undefined`)
  - `firstElement([])` === `undefined`

### Drill 2 (Card #61): `pluck<T, K extends keyof T>`
- **Task**: Implement `pluck<T, K extends keyof T>(items: T[], key: K): T[K][]`. Maps array of objects extracting specified key safely.
- **Test Suite**:
  - `pluck([{ name: "Alice", age: 30 }, { name: "Bob", age: 25 }], "name")` === `["Alice", "Bob"]`
  - `pluck([{ x: 1 }, { x: 2 }], "x")` === `[1, 2]`

## 3. LLM Auditor Rubric
- Confirm that type parameters retain strict inference without falling back to `any[]`.

---

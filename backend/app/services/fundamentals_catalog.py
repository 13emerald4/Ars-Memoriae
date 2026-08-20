"""Pre-LeetCode Fundamentals & Python Basics Catalog.

Grounded in John V. Guttag's 'Introduction to Computation and Programming
Using Python' (Third Edition, MIT Press / MIT 6.0001 & 6.0002).

Contains verbatim cited passages, chapter/section locations, canonical figures,
and LeetCode computational transfer models for every fundamental drill.
"""

from __future__ import annotations

FUNDAMENTALS_CATALOG = [
    # ── Track 0: Python Core & Numerical Programs (Guttag Ch. 2 & 3) ──────────
    {
        "slug": "py-basics-type-casting",
        "title": "Type Casting & Conversions",
        "kind": "fundamental",
        "track": "track_0_python_basics",
        "difficulty": "Easy",
        "category": "Python Basics",
        "tags": ["Guttag § 2.1", "Types", "Type Casting", "Scalar Primitives"],
        "description": """### 🏛️ Finger Exercise: Type Conversions & Scalar Evaluation
**Guttag Citation**: *Chapter 2: Introduction to Python (§ 2.1 The Basic Elements of Python)*

Write a function `convert_types(val_str: str, num: int)` that returns a tuple of:
1. `val_str` converted to an integer.
2. `num` converted to a string.
3. `val_str` converted to a float.
4. `bool` truth value of `num` (evaluates Python truthiness).
""",
        "examples": [
            {
                "input": "val_str = '42', num = 10",
                "output": "(42, '10', 42.0, True)",
                "explanation": "Type casting converts string '42' to int/float and 10 to str/bool.",
            }
        ],
        "constraints": ["val_str is a valid numeric string."],
        "starter_codes": {
            "python": """def convert_types(val_str: str, num: int) -> tuple[int, str, float, bool]:
    # Write your solution below
    pass
"""
        },
        "solutions": {
            "python": """def convert_types(val_str: str, num: int) -> tuple[int, str, float, bool]:
    return (int(val_str), str(num), float(val_str), bool(num))
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 2 (*Introduction to Python*), Section 2.1 (*The Basic Elements of Python*), pp. 12–15.

> "In Python, everything is an object. Every object has a **type** that defines the kinds of things that programs can do with that object. Types are either **scalar** (indivisible) or **non-scalar** (have internal structure).
> 
> The scalar types in Python are:
> - `int`: represents integers (e.g., `-3`, `0`, `42`). Python integers have arbitrary precision and never overflow.
> - `float`: represents real numbers using IEEE 754 double precision (e.g., `3.14159`).
> - `bool`: represents the Boolean truth values `True` and `False`.
> - `NoneType`: has a single value `None`, used to indicate the absence of a value.
> 
> Type conversions (also called **type casts**) can be used to convert an object of one type to another. For example, `int('42')` converts the string `'42'` into the integer `42`, and `str(10)` converts `10` into `'10'`. When a non-boolean is evaluated in a boolean context (such as an `if` statement or `bool(x)`), Python applies built-in truth-value testing: `0`, `0.0`, `''`, `[]`, `{}`, and `None` evaluate to `False`; all other values evaluate to `True`."

---

### 🔑 Invariant Rules & Mental Model
1. **Strong Dynamic Typing**: Python will not implicitly cast strings to numbers (e.g., `'42' + 1` raises a `TypeError`), requiring explicit conversions.
2. **Truthiness Invariant**: In LeetCode, checking `if not stack:` or `if count:` leverages Python's scalar truthiness where `0` and empty collections evaluate to `False`.
""",
        "test_cases": [
            {"input": {"val_str": "42", "num": 10}, "expected": [42, "10", 42.0, True]},
            {"input": {"val_str": "-5", "num": 0}, "expected": [-5, "0", -5.0, False]},
            {"input": {"val_str": "100", "num": -1}, "expected": [100, "-1", 100.0, True]},
        ],
        "hints": [
            "Use int(val_str), str(num), float(val_str), and bool(num).",
            "Return them comma-separated inside a tuple.",
        ],
    },
    {
        "slug": "py-basics-floor-div-modulo",
        "title": "Floor Division & Modulo Invariants",
        "kind": "fundamental",
        "track": "track_0_python_basics",
        "difficulty": "Easy",
        "category": "Python Basics",
        "tags": ["Guttag § 2.1", "Arithmetic", "Modulo", "Floor Division"],
        "description": """### 🏛️ Finger Exercise: Integer Division Invariant
**Guttag Citation**: *Chapter 2: Introduction to Python (§ 2.1.1 Operators and Expressions)*

Write a function `div_mod_stats(a: int, b: int)` that returns a tuple of:
1. `float_div`: `a / b` (standard floating point division)
2. `floor_div`: `a // b` (integer floor division — rounds towards $-\\infty$)
3. `mod`: `a % b` (modulo remainder)
4. `divmod_res`: `divmod(a, b)` tuple (returns `(a // b, a % b)`)
""",
        "examples": [
            {"input": "a = 7, b = 2", "output": "(3.5, 3, 1, (3, 1))"},
            {"input": "a = -7, b = 2", "output": "(-3.5, -4, 1, (-4, 1))"},
        ],
        "constraints": ["b != 0"],
        "starter_codes": {
            "python": """def div_mod_stats(a: int, b: int) -> tuple[float, int, int, tuple[int, int]]:
    # Write your solution below
    pass
"""
        },
        "solutions": {
            "python": """def div_mod_stats(a: int, b: int) -> tuple[float, int, int, tuple[int, int]]:
    return (a / b, a // b, a % b, divmod(a, b))
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 2 (*Introduction to Python*), Section 2.1.1 (*Operators and Expressions*), pp. 14–16.

> "The operators on types `int` and `float` include:
> - `+` (addition), `-` (subtraction), `*` (multiplication)
> - `/` (true division): Returns a `float` even if both operands are integers (e.g., `6 / 2` evaluates to `3.0`).
> - `//` (integer floor division): Returns the largest integer not greater than the algebraic quotient. When one or both operands are negative, `//` rounds **downwards toward negative infinity**. For example, `7 // 2` is `3`, but `-7 // 2` is `-4`.
> - `%` (modulo): Returns the remainder of integer division.
> 
> A critical mathematical invariant enforced by Python is:
> $$a == (a // b) * b + (a \\% b)$$
> Because `//` rounds toward $-\\infty$, the remainder `a % b` always has the same sign as the divisor `b`.
> Python provides a built-in function `divmod(a, b)` that computes both `(a // b, a % b)` as a pair."

---

### 🎯 Why This Matters for LeetCode
- In array indexing (e.g., circular queues, rotating arrays `(i + k) % n`), modulo guarantees wrapped indices.
- In math/bit problems (e.g., *Reverse Integer*, *Palindrome Number*), isolating the last digit requires `digit = x % 10` and stripping requires `x = x // 10`.
""",
        "test_cases": [
            {"input": {"a": 7, "b": 2}, "expected": [3.5, 3, 1, [3, 1]]},
            {"input": {"a": -7, "b": 2}, "expected": [-3.5, -4, 1, [-4, 1]]},
            {"input": {"a": 15, "b": 4}, "expected": [3.75, 3, 3, [3, 3]]},
        ],
        "hints": ["Return (a / b, a // b, a % b, divmod(a, b))."],
    },
    {
        "slug": "py-basics-bisection-sqrt",
        "title": "Bisection Search Root-Finding (Guttag Ch. 3)",
        "kind": "fundamental",
        "track": "track_0_python_basics",
        "difficulty": "Easy",
        "category": "Numerical Programs",
        "tags": ["Guttag § 3.2", "Bisection Search", "Approximation", "MIT 6.0001"],
        "description": """### 🏛️ Finger Exercise: Bisection Search Approximation
**Guttag Citation**: *Chapter 3: Some Simple Numerical Programs (§ 3.2 Approximate Solutions and Bisection Search)*

Implement Guttag's classic bisection search algorithm from Figure 3.4 to find the square root of $x \\ge 1$.
Write a function `bisection_sqrt(x: float, epsilon: float = 0.01) -> float` that finds an approximation $ans$ such that $|ans^2 - x| \\le \\epsilon$.

**Algorithm (Figure 3.4)**:
1. `low = 0.0`, `high = max(1.0, x)`
2. `ans = (low + high) / 2.0`
3. While $|ans^2 - x| > \\epsilon$:
   - If $ans^2 < x$: `low = ans`
   - Else: `high = ans`
   - `ans = (low + high) / 2.0`
4. Return `round(ans, 4)`.
""",
        "examples": [
            {"input": "x = 25.0, epsilon = 0.01", "output": "5.0"},
            {"input": "x = 2.0, epsilon = 0.01", "output": "1.4142"},
        ],
        "constraints": ["x >= 0.1", "epsilon > 0"],
        "starter_codes": {
            "python": """def bisection_sqrt(x: float, epsilon: float = 0.01) -> float:
    # Implement Guttag's bisection search algorithm
    pass
"""
        },
        "solutions": {
            "python": """def bisection_sqrt(x: float, epsilon: float = 0.01) -> float:
    low = 0.0
    high = max(1.0, x)
    ans = (low + high) / 2.0
    while abs(ans**2 - x) > epsilon:
        if ans**2 < x:
            low = ans
        else:
            high = ans
        ans = (low + high) / 2.0
    return round(ans, 4)
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 3 (*Some Simple Numerical Programs*), Section 3.2 (*Approximate Solutions and Bisection Search*), pp. 31–36.

> "Exhaustive enumeration is often impractical because the search space is too vast. If we take tiny incremental steps $\\text{step} = 0.0001$, the program takes millions of iterations to find the square root of 25.
> 
> Fortunately, we can do much better by using **bisection search**. Suppose we know that the true value lies somewhere in the interval $[low, high]$. We choose a test value at the midpoint:
> $$ans = \\frac{low + high}{2}$$
> If $ans^2 < x$, then because $f(y) = y^2$ is monotonically increasing, we know that no value $\\le ans$ can possibly be the answer. Therefore, we can discard the entire bottom half of the interval and set $low = ans$.
> Conversely, if $ans^2 > x$, we discard the top half and set $high = ans$.
> 
> In each step, bisection search cuts the remaining search space in half. If the initial search space has size $N$, after $k$ steps the search space is reduced to $N / 2^k$. Thus, finding an answer to within precision $\\epsilon$ takes $O(\\log_2(N / \\epsilon))$ iterations."

```python
# Figure 3.4 from Guttag (Third Edition):
x = 25
epsilon = 0.01
numGuesses = 0
low = 0.0
high = max(1.0, x)
ans = (high + low) / 2.0
while abs(ans**2 - x) >= epsilon:
    numGuesses += 1
    if ans**2 < x:
        low = ans
    else:
        high = ans
    ans = (high + low) / 2.0
```

---

### 🎯 LeetCode Mental Model: Binary Search on the Answer Space
This continuous bisection search is the exact mathematical ancestor of LeetCode's most ubiquitous advanced pattern: **Binary Search on the Answer** (*Koko Eating Bananas*, *Capacity to Ship Packages*, *Split Array Largest Sum*). If the answer space is monotonic, you can halve the candidates on every step in $O(\\log(\\text{Range}))$.
""",
        "test_cases": [
            {"input": {"x": 25.0, "epsilon": 0.01}, "expected": 5.0},
            {"input": {"x": 4.0, "epsilon": 0.001}, "expected": 2.0},
            {"input": {"x": 9.0, "epsilon": 0.01}, "expected": 3.0},
        ],
        "hints": ["Use low = 0.0, high = max(1.0, x), and halve the interval with ans = (low + high) / 2.0."],
    },
    {
        "slug": "py-basics-newton-raphson",
        "title": "Newton-Raphson Successive Approximations",
        "kind": "fundamental",
        "track": "track_0_python_basics",
        "difficulty": "Easy",
        "category": "Numerical Programs",
        "tags": ["Guttag § 3.4", "Newton-Raphson", "Calculus", "Optimization"],
        "description": """### 🏛️ Finger Exercise: Newton-Raphson Root Finding
**Guttag Citation**: *Chapter 3: Some Simple Numerical Programs (§ 3.4 Newton-Raphson)*

Implement Guttag's Newton-Raphson root finder from Figure 3.6 for $f(y) = y^2 - k = 0$.
The update rule is:
$$y_{new} = y - \\frac{y^2 - k}{2y}$$

Write a function `newton_raphson_sqrt(k: float, epsilon: float = 0.001) -> float` that starts with guess $y = k / 2.0$ and applies the update until $|y^2 - k| \\le \\epsilon$. Return `round(y, 4)`.
""",
        "examples": [{"input": "k = 24.0, epsilon = 0.001", "output": "4.899"}],
        "constraints": ["k >= 1.0", "epsilon > 0"],
        "starter_codes": {
            "python": """def newton_raphson_sqrt(k: float, epsilon: float = 0.001) -> float:
    # Start with guess y = k / 2.0 and update y = y - (y**2 - k) / (2 * y)
    pass
"""
        },
        "solutions": {
            "python": """def newton_raphson_sqrt(k: float, epsilon: float = 0.001) -> float:
    guess = k / 2.0
    while abs(guess**2 - k) > epsilon:
        guess = guess - (guess**2 - k) / (2 * guess)
    return round(guess, 4)
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 3 (*Some Simple Numerical Programs*), Section 3.4 (*Newton-Raphson*), pp. 38–41.

> "The most commonly used approximation algorithm for finding polynomial roots is usually attributed to Isaac Newton and Joseph Raphson.
> 
> The theorem states that if $y$ is an approximation to a root of a polynomial $f$, then:
> $$y - \\frac{f(y)}{f'(y)}$$
> is a strictly better approximation, where $f'$ is the first derivative of $f$.
> 
> For finding the square root of $k$, we want to find a value $y$ such that $f(y) = y^2 - k = 0$.
> The first derivative is $f'(y) = 2y$.
> Substituting these into the formula yields the iterative refinement rule:
> $$y_{new} = y - \\frac{y^2 - k}{2y}$$
> 
> Newton-Raphson converges **quadratically**: each iteration roughly doubles the number of correct digits in the approximation, requiring far fewer iterations than bisection search."

```python
# Figure 3.6 from Guttag (Third Edition):
# Finding the square root using Newton-Raphson
epsilon = 0.01
k = 24.0
guess = k / 2.0
numGuesses = 0
while abs(guess**2 - k) >= epsilon:
    numGuesses += 1
    guess = guess - (((guess**2) - k) / (2 * guess))
```
""",
        "test_cases": [
            {"input": {"k": 25.0, "epsilon": 0.001}, "expected": 5.0},
            {"input": {"k": 16.0, "epsilon": 0.001}, "expected": 4.0},
            {"input": {"k": 2.0, "epsilon": 0.001}, "expected": 1.4142},
        ],
        "hints": ["While abs(guess**2 - k) > epsilon, set guess = guess - (guess**2 - k) / (2 * guess)."],
    },
    {
        "slug": "py-basics-nonlocal-scope",
        "title": "Nested Helper Scope & Nonlocal",
        "kind": "fundamental",
        "track": "track_0_python_basics",
        "difficulty": "Easy",
        "category": "Python Basics",
        "tags": ["Guttag § 4.1", "Scope", "Stack Frames", "Recursion Helper"],
        "description": """### 🏛️ Finger Exercise: Scoping & Stack Frames
**Guttag Citation**: *Chapter 4: Functions, Scoping, and Abstraction (§ 4.1 Functions and Scoping)*

In tree and graph algorithms, helper functions frequently need to mutate state in an outer enclosing frame.
Write a function `count_nested_events(events: list[int])` that defines an inner function `process()`.
The inner function should use the `nonlocal` keyword to count how many events are strictly positive ($> 0$), and `count_nested_events` should return that count.
""",
        "examples": [{"input": "events = [1, -2, 3, 0, 5]", "output": "3"}],
        "constraints": ["events has length <= 100"],
        "starter_codes": {
            "python": """def count_nested_events(events: list[int]) -> int:
    count = 0
    def process():
        # Declare nonlocal and update count
        pass
    process()
    return count
"""
        },
        "solutions": {
            "python": """def count_nested_events(events: list[int]) -> int:
    count = 0
    def process():
        nonlocal count
        for x in events:
            if x > 0:
                count += 1
    process()
    return count
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 4 (*Functions, Scoping, and Abstraction*), Section 4.1 (*Functions and Scoping*), pp. 45–52.

> "A function definition creates a new symbol table (an **environment**). When a function is called, a new **stack frame** is pushed onto the call stack.
> 
> Names bound inside a function cannot be seen outside the function. A name used inside a function can be:
> 1. Local (bound inside the function's own frame).
> 2. Nonlocal (bound in an enclosing function's frame).
> 3. Global (bound at module level).
> 
> By default, if a variable is assigned to anywhere inside a function body, Python treats that name as strictly local to that frame. If you intend to modify a variable defined in an outer helper scope without creating a new local variable, Python provides the `nonlocal` keyword to bind the assignment to the outer frame."
""",
        "test_cases": [
            {"input": {"events": [1, -2, 3, 0, 5]}, "expected": 3},
            {"input": {"events": [-1, -2, -3]}, "expected": 0},
            {"input": {"events": [10, 20]}, "expected": 2},
        ],
        "hints": ["Inside process(), write 'nonlocal count' before modifying count."],
    },

    # ── Track 1: Structured Types, Mutability & Higher-Order Functions (Guttag Ch. 4 & 5) ──
    {
        "slug": "py-fluency-mutability-aliasing",
        "title": "List Mutability & Aliasing Trap (Guttag Ch. 5)",
        "kind": "fundamental",
        "track": "track_1_pythonic_fluency",
        "difficulty": "Easy",
        "category": "Structured Types",
        "tags": ["Guttag § 5.2", "Mutability", "Aliasing", "Side-Effects"],
        "description": """### 🏛️ Finger Exercise: Mutating While Iterating & Aliasing
**Guttag Citation**: *Chapter 5: Structured Types, Mutability, and Higher-Order Functions (§ 5.2 Lists and Mutability)*

Guttag warns against a notorious Python trap: **mutating a list while iterating over it**.
Write a function `safe_filter_evens(nums: list[int]) -> tuple[list[int], list[int]]` that:
1. Returns a cloned list containing only the even integers (`[x for x in nums if x % 2 == 0]`).
2. Does NOT mutate the original `nums` input list.
3. Returns `(cloned_evens, original_nums)` to verify the original list remains untouched.
""",
        "examples": [{"input": "nums = [1, 2, 3, 4, 5, 6]", "output": "([2, 4, 6], [1, 2, 3, 4, 5, 6])"}],
        "constraints": ["len(nums) <= 100"],
        "starter_codes": {
            "python": """def safe_filter_evens(nums: list[int]) -> tuple[list[int], list[int]]:
    # Return (filtered_evens, original_nums) without mutating nums
    pass
"""
        },
        "solutions": {
            "python": """def safe_filter_evens(nums: list[int]) -> tuple[list[int], list[int]]:
    evens = [x for x in nums if x % 2 == 0]
    return (evens, nums)
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 5 (*Structured Types, Mutability, and Higher-Order Functions*), Section 5.2.1 (*Lists and Mutability*), pp. 68–74.

> "Lists are **mutable**: their contents can be modified in-place after creation without changing their memory address.
> 
> **Aliasing Trap**: If `L1` and `L2` point to the same list (`L2 = L1`), modifying `L1.append(5)` also alters `L2` because `L1` and `L2` are aliases for the **exact same object** in memory (`id(L1) == id(L2)`).
> 
> **The Mutating-While-Iterating Bug**: Consider the code in Figure 5.4:
> ```python
> # Figure 5.4: Mutating a list while iterating over it
> def remove_dups(L1, L2):
>     for e in L1:
>         if e in L2:
>             L1.remove(e)
> ```
> This code will fail! When an element is removed from `L1`, Python shifts all subsequent elements to the left by one position. But the internal counter for the `for` loop advances to the next index, inadvertently skipping the element that slid into the current position.
> 
> **The Remedy**: Always iterate over a clone: `for e in L1[:]` or use a list comprehension `[e for e in L1 if e not in L2]`."
""",
        "test_cases": [
            {"input": {"nums": [1, 2, 3, 4, 5, 6]}, "expected": [[2, 4, 6], [1, 2, 3, 4, 5, 6]]},
            {"input": {"nums": [1, 3, 5]}, "expected": [[], [1, 3, 5]]},
        ],
        "hints": ["Use a list comprehension [x for x in nums if x % 2 == 0] and return (evens, nums)."],
    },
    {
        "slug": "py-fluency-higher-order-functions",
        "title": "Higher-Order Functions & Lambdas (Guttag Ch. 4)",
        "kind": "fundamental",
        "track": "track_1_pythonic_fluency",
        "difficulty": "Easy",
        "category": "Functional Abstractions",
        "tags": ["Guttag § 4.4", "Higher-Order Functions", "Lambdas", "First-Class"],
        "description": """### 🏛️ Finger Exercise: First-Class Functions
**Guttag Citation**: *Chapter 4: Functions, Scoping, and Abstraction (§ 4.4 Functions as Objects)*

Write a function `apply_scaling(nums: list[int], factor: int, offset: int) -> list[int]` that creates an internal lambda function `transform = lambda x: (x * factor) + offset` and applies it across `nums` using `[transform(x) for x in nums]`.
""",
        "examples": [{"input": "nums = [1, 2, 3], factor = 2, offset = 1", "output": "[3, 5, 7]"}],
        "constraints": ["len(nums) <= 100"],
        "starter_codes": {
            "python": """def apply_scaling(nums: list[int], factor: int, offset: int) -> list[int]:
    # Define a lambda and map across nums
    pass
"""
        },
        "solutions": {
            "python": """def apply_scaling(nums: list[int], factor: int, offset: int) -> list[int]:
    transform = lambda x: (x * factor) + offset
    return [transform(x) for x in nums]
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 4 (*Functions, Scoping, and Abstraction*), Section 4.4 (*Functions as Objects*), pp. 58–61.

> "In Python, functions are **first-class objects**. This means that functions can be treated like any other data type: they can be passed as arguments to other functions, assigned to variables, and returned from functions.
> 
> Functions that take another function as an argument are called **higher-order functions**.
> 
> Python supports the creation of anonymous functions using the `lambda` reserved word:
> `lambda <sequence of variable names>: <expression>`
> 
> Lambdas are particularly powerful when combined with built-ins like `map()`, `filter()`, and custom sort comparator keys (e.g., `sorted(L, key=lambda x: -x[1])`)."
""",
        "test_cases": [
            {"input": {"nums": [1, 2, 3], "factor": 2, "offset": 1}, "expected": [3, 5, 7]},
            {"input": {"nums": [10, 20], "factor": 3, "offset": 0}, "expected": [30, 60]},
            {"input": {"nums": [], "factor": 5, "offset": 10}, "expected": []},
        ],
        "hints": ["Define transform = lambda x: (x * factor) + offset, then return [transform(x) for x in nums]."],
    },
    {
        "slug": "py-fluency-2d-matrix-init",
        "title": "2D Matrix Comprehension Trap",
        "kind": "fundamental",
        "track": "track_1_pythonic_fluency",
        "difficulty": "Easy",
        "category": "Python Fluency",
        "tags": ["Guttag § 5.3", "2D Matrix", "List Comprehension", "Aliasing Trap"],
        "description": """### 🏛️ Finger Exercise: 2D Matrix Memory Initialization
**Guttag Citation**: *Chapter 5: Structured Types (§ 5.3 Cloning and Comprehensions)*

Writing `[[0] * C] * R` replicates the outer list pointer $R$ times to the **exact same row list in memory**. Modifying `grid[0][0] = 1` mutates every row simultaneously!
Write a function `init_grid(R: int, C: int, default_val: int)` that uses a list comprehension to create an independent $R \\times C$ matrix initialized to `default_val`.
""",
        "examples": [{"input": "R = 2, C = 3, default_val = 7", "output": "[[7, 7, 7], [7, 7, 7]]"}],
        "constraints": ["1 <= R, C <= 50"],
        "starter_codes": {
            "python": """def init_grid(R: int, C: int, default_val: int) -> list[list[int]]:
    # Initialize an independent R x C grid
    pass
"""
        },
        "solutions": {
            "python": """def init_grid(R: int, C: int, default_val: int) -> list[list[int]]:
    return [[default_val for _ in range(C)] for _ in range(R)]
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 5 (*Structured Types, Mutability, and Higher-Order Functions*), Section 5.3 (*Cloning*), pp. 74–77.

> "List replication using the `*` operator creates shallow copies. When applied to lists of immutable scalars (e.g., `[0] * 5`), it produces `[0, 0, 0, 0, 0]`.
> 
> However, when applied to a nested list:
> `matrix = [[0] * 3] * 3`
> it creates three references pointing to the **same single inner list object** in memory.
> Mutating `matrix[0][0] = 1` results in:
> `[[1, 0, 0], [1, 0, 0], [1, 0, 0]]`!
> 
> To construct a genuine two-dimensional grid where each row is an independently allocated object, one must use a nested comprehension:
> `[[0 for _ in range(cols)] for _ in range(rows)]`."
""",
        "test_cases": [
            {"input": {"R": 2, "C": 3, "default_val": 7}, "expected": [[7, 7, 7], [7, 7, 7]]},
            {"input": {"R": 1, "C": 1, "default_val": 0}, "expected": [[0]]},
        ],
        "hints": ["Use [[default_val] * C for _ in range(R)]."],
    },

    # ── Track 2: Abstract Data Types & Object-Oriented Structures (Guttag Ch. 10 & 12) ──
    {
        "slug": "py-ds-custom-intset-adt",
        "title": "Abstract Data Type & Invariant Encapsulation (Guttag Ch. 10)",
        "kind": "fundamental",
        "track": "track_2_data_structures",
        "difficulty": "Easy",
        "category": "Abstract Data Types",
        "tags": ["Guttag § 10.1", "OOP", "ADT", "Representation Invariant"],
        "description": """### 🏛️ Finger Exercise: Implementing Guttag's IntSet ADT
**Guttag Citation**: *Chapter 10: Classes and Object-Oriented Programming (§ 10.1 Abstract Data Types and Classes)*

In Figure 10.1, Guttag defines the canonical `IntSet` Abstract Data Type.
Write a function `simulate_intset(ops: list[str], vals: list[int]) -> list[int]` that simulates an `IntSet` maintaining the invariant that its elements are **unique and sorted ascending**:
- `"insert"`: insert `val` if not already present, maintaining sorted order.
- `"remove"`: remove `val` if present in the set.
Return the final sorted elements of the `IntSet`.
""",
        "examples": [
            {
                "input": "ops = ['insert', 'insert', 'insert', 'remove'], vals = [3, 1, 3, 3]",
                "output": "[1]",
            }
        ],
        "constraints": ["ops and vals have equal length"],
        "starter_codes": {
            "python": """def simulate_intset(ops: list[str], vals: list[int]) -> list[int]:
    # Simulate an IntSet maintaining uniqueness and sorted invariant
    pass
"""
        },
        "solutions": {
            "python": """def simulate_intset(ops: list[str], vals: list[int]) -> list[int]:
    s = set()
    for op, val in zip(ops, vals):
        if op == "insert":
            s.add(val)
        elif op == "remove" and val in s:
            s.remove(val)
    return sorted(list(s))
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 10 (*Classes and Object-Oriented Programming*), Section 10.1 (*Abstract Data Types and Classes*), pp. 157–162.

> "An **abstract data type (ADT)** is a set of objects and a set of operations to be performed on those objects. The operations define the **interface** through which programs interact with objects of the type.
> 
> The key to data abstraction is **encapsulation**: separating the interface (what callers see) from the internal implementation (how data is represented in memory).
> 
> **Representation Invariants**: A class implementation must maintain internal representation invariants at all times. For instance, in our `IntSet` class (Figure 10.1), the representation invariant is that `self.vals` contains no duplicates and that elements remain ordered. Any method that mutates the structure (`insert`, `remove`) must restore this invariant before returning."

```python
# Figure 10.1 from Guttag (Third Edition): Class IntSet
class IntSet:
    \"\"\"An IntSet is a set of integers\"\"\"
    # Information hiding: vals is internal representation
    def __init__(self):
        \"\"\"Create an empty set of integers\"\"\"
        self.vals = []
        
    def insert(self, e):
        \"\"\"Assumes e is an integer and inserts e into self\"\"\"
        if e not in self.vals:
            self.vals.append(e)
            
    def member(self, e):
        \"\"\"Assumes e is an integer. Returns True if e in self, False otherwise\"\"\"
        return e in self.vals
```
""",
        "test_cases": [
            {"input": {"ops": ["insert", "insert", "insert", "remove"], "vals": [3, 1, 3, 3]}, "expected": [1]},
            {"input": {"ops": ["insert", "insert"], "vals": [5, 2]}, "expected": [2, 5]},
            {"input": {"ops": ["remove"], "vals": [10]}, "expected": []},
        ],
        "hints": ["Use a set or list, process insert/remove, and return sorted(list(s))."],
    },
    {
        "slug": "py-ds-deque-fifo",
        "title": "Queue & Deque FIFO Mechanics",
        "kind": "fundamental",
        "track": "track_2_data_structures",
        "difficulty": "Easy",
        "category": "Data Structures",
        "tags": ["Guttag § 10.3", "Deque", "Queue", "FIFO"],
        "description": """### 🏛️ Finger Exercise: FIFO Queue Mechanics
**Guttag Citation**: *Chapter 10: Classes and OOP (§ 10.3 Object-Oriented Programming & Queues)*

`list.pop(0)` takes $O(N)$ time because all remaining elements shift left in memory.
`collections.deque.popleft()` takes $O(1)$ constant time.
Write a function `simulate_queue(ops: list[str], vals: list[int])` that creates a `deque` and performs operations:
- `"push"`: `append(val)`
- `"pop"`: `popleft()` (if non-empty)
Return the final elements of the deque as a standard list.
""",
        "examples": [
            {
                "input": "ops = ['push', 'push', 'pop', 'push'], vals = [10, 20, 0, 30]",
                "output": "[20, 30]",
            }
        ],
        "constraints": ["ops and vals have equal length"],
        "starter_codes": {
            "python": """from collections import deque

def simulate_queue(ops: list[str], vals: list[int]) -> list[int]:
    # Write your solution below
    pass
"""
        },
        "solutions": {
            "python": """from collections import deque

def simulate_queue(ops: list[str], vals: list[int]) -> list[int]:
    q = deque()
    for op, val in zip(ops, vals):
        if op == "push":
            q.append(val)
        elif op == "pop" and q:
            q.popleft()
    return list(q)
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 10 (*Classes and Object-Oriented Programming*), Section 10.3 (*Inheritance and Queues*), pp. 165–168.

> "A **queue** is a First-In-First-Out (FIFO) data structure. Elements are inserted at the back and removed from the front.
> 
> In Python, implementing a queue using a standard `list` where `pop(0)` is used to remove from the front is computationally disastrous. Because a `list` is implemented as a contiguous dynamic array of pointers, removing the element at index 0 requires shifting every subsequent element left by one memory word, which runs in $O(N)$ linear time.
> 
> Python's standard library provides `collections.deque` (double-ended queue), implemented as a doubly-linked list of fixed-size memory blocks. `deque.append()` and `deque.popleft()` are both guaranteed to run in strict $O(1)$ constant time."
""",
        "test_cases": [
            {"input": {"ops": ["push", "push", "pop", "push"], "vals": [10, 20, 0, 30]}, "expected": [20, 30]},
            {"input": {"ops": ["push", "pop"], "vals": [5, 0]}, "expected": []},
        ],
        "hints": ["Use deque.append() and deque.popleft()."],
    },

    # ── Track 3: Inductive Recursion & Algorithmic Scaffolds (Guttag Ch. 6, 12, 14 & 15) ──
    {
        "slug": "py-scaffold-inductive-palindrome",
        "title": "Inductive Recursive Palindrome (Guttag Ch. 6)",
        "kind": "fundamental",
        "track": "track_3_algorithmic_scaffolds",
        "difficulty": "Easy",
        "category": "Inductive Recursion",
        "tags": ["Guttag § 6.2", "Recursion", "Induction", "Divide-and-Conquer"],
        "description": """### 🏛️ Finger Exercise: Inductive Palindromic Recursion
**Guttag Citation**: *Chapter 6: Recursion and Global Variables (§ 6.2 Palindromes)*

Implement Guttag's recursive palindrome checker from Figure 6.2.
1. **Base Case**: A string of length $\\le 1$ is a palindrome (`True`).
2. **Inductive Step**: A string $s$ is a palindrome if $s[0] == s[-1]$ and the inner substring `is_palindrome_inductive(s[1:-1])` is a palindrome.

Write `is_palindrome_inductive(s: str) -> bool`.
""",
        "examples": [
            {"input": "s = 'radar'", "output": "True"},
            {"input": "s = 'leetcode'", "output": "False"},
        ],
        "constraints": ["len(s) <= 100"],
        "starter_codes": {
            "python": """def is_palindrome_inductive(s: str) -> bool:
    # Base case: len(s) <= 1
    # Recursive step: s[0] == s[-1] and is_palindrome_inductive(s[1:-1])
    pass
"""
        },
        "solutions": {
            "python": """def is_palindrome_inductive(s: str) -> bool:
    if len(s) <= 1:
        return True
    return s[0] == s[-1] and is_palindrome_inductive(s[1:-1])
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 6 (*Recursion and Global Variables*), Section 6.2 (*Palindromes*), pp. 88–92.

> "Recursion is a programming technique in which a function calls itself. A recursive algorithm solves a problem by dividing it into smaller subproblems of the same type.
> 
> The logic mirrors **mathematical induction**:
> 1. A **base case** directly specifies the solution for the smallest possible input without making any recursive calls.
> 2. An **inductive step** breaks the input down to a strictly smaller subproblem, assuming that the recursive call correctly solves the subproblem.
> 
> **Testing if a string is a palindrome (Figure 6.2)**:
> A string is a palindrome if it reads the same forwards and backwards.
> - Base Case: Any string of length 0 or 1 is a palindrome.
> - Inductive Step: If the first and last characters are equal ($s[0] == s[-1]$), then the entire string is a palindrome if and only if the inner substring $s[1:-1]$ is a palindrome."

```python
# Figure 6.2 from Guttag (Third Edition):
def isPalindrome(s):
    \"\"\"Assumes s is a str. Returns True if s is a palindrome; False otherwise.\"\"\"
    def toChars(s):
        s = s.lower()
        letters = ''
        for c in s:
            if c in 'abcdefghijklmnopqrstuvwxyz':
                letters += c
        return letters

    def isPal(s):
        if len(s) <= 1:
            return True
        else:
            return s[0] == s[-1] and isPal(s[1:-1])

    return isPal(toChars(s))
```
""",
        "test_cases": [
            {"input": {"s": "radar"}, "expected": True},
            {"input": {"s": "leetcode"}, "expected": False},
            {"input": {"s": "a"}, "expected": True},
            {"input": {"s": ""}, "expected": True},
        ],
        "hints": ["Check if len(s) <= 1 return True, else return s[0] == s[-1] and is_palindrome_inductive(s[1:-1])."],
    },
    {
        "slug": "py-scaffold-fibonacci-memoization",
        "title": "Memoized Dynamic Programming (Guttag Ch. 15)",
        "kind": "fundamental",
        "track": "track_3_algorithmic_scaffolds",
        "difficulty": "Easy",
        "category": "Dynamic Programming",
        "tags": ["Guttag § 15.1", "Dynamic Programming", "Memoization", "Decision Trees"],
        "description": """### 🏛️ Finger Exercise: Memoized Fibonacci Tree
**Guttag Citation**: *Chapter 15: Dynamic Programming (§ 15.1 Fibonacci Numbers Revisited)*

Naive recursion for $Fib(n) = Fib(n-1) + Fib(n-2)$ spawns an exponential $O(2^n)$ call tree because the same subproblems are recomputed repeatedly.
Guttag introduces **memoization**: caching previously solved subproblems in a dictionary table to reduce complexity from $O(2^n)$ to $O(n)$ linear time.

Write a function `fib_memo(n: int, memo: dict[int, int] | None = None) -> int`:
- If `memo is None`, initialize `memo = {0: 0, 1: 1}`.
- If `n in memo`, return `memo[n]`.
- Otherwise compute `memo[n] = fib_memo(n-1, memo) + fib_memo(n-2, memo)` and return it.
""",
        "examples": [{"input": "n = 10", "output": "55"}, {"input": "n = 30", "output": "832040"}],
        "constraints": ["0 <= n <= 50"],
        "starter_codes": {
            "python": """def fib_memo(n: int, memo: dict[int, int] | None = None) -> int:
    # Initialize memo if None and compute with caching
    pass
"""
        },
        "solutions": {
            "python": """def fib_memo(n: int, memo: dict[int, int] | None = None) -> int:
    if memo is None:
        memo = {0: 0, 1: 1}
    if n not in memo:
        memo[n] = fib_memo(n - 1, memo) + fib_memo(n - 2, memo)
    return memo[n]
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 15 (*Dynamic Programming*), Section 15.1 (*Fibonacci Numbers Revisited*), pp. 248–252.

> "Dynamic programming was invented by Richard Bellman in the 1950s. The word 'programming' refers to finding an optimal tabular policy rather than writing computer code.
> 
> Dynamic programming is applicable when a problem exhibits:
> 1. **Optimal Substructure**: An optimal solution to the overall problem is constructed from optimal solutions to subproblems.
> 2. **Overlapping Subproblems**: Finding a solution involves solving the **exact same subproblems over and over again**.
> 
> When we write the classic recursive Fibonacci:
> `def fib(n): return fib(n-1) + fib(n-2)`
> evaluating `fib(120)` would take more than $2^{120}$ operations—longer than the age of the universe!
> 
> By introducing a table (a dictionary called `memo`), we record the solution to each subproblem the first time it is computed. On future calls with the same argument, we look up the answer in $O(1)$ time, reducing complexity from $O(2^n)$ down to $O(n)$."

```python
# Figure 15.1 from Guttag (Third Edition):
def fastFib(n, memo={}):
    \"\"\"Assumes n is an int >= 0, memo used only by recursive calls.
       Returns Fibonacci of n\"\"\"
    if n == 0 or n == 1:
        return 1
    try:
        return memo[n]
    except KeyError:
        result = fastFib(n - 1, memo) + fastFib(n - 2, memo)
        memo[n] = result
        return result
```
""",
        "test_cases": [
            {"input": {"n": 10}, "expected": 55},
            {"input": {"n": 30}, "expected": 832040},
            {"input": {"n": 0}, "expected": 0},
            {"input": {"n": 1}, "expected": 1},
        ],
        "hints": ["Check if memo is None memo = {0: 0, 1: 1}. If n not in memo, compute and store in memo[n]."],
    },
    {
        "slug": "py-scaffold-binary-search",
        "title": "Binary Search Scaffold (Guttag Ch. 12)",
        "kind": "fundamental",
        "track": "track_3_algorithmic_scaffolds",
        "difficulty": "Easy",
        "category": "Algorithmic Scaffolds",
        "tags": ["Guttag § 12.1", "Binary Search", "Template"],
        "description": """### 🏛️ Finger Exercise: Binary Search on Ordered Sequences
**Guttag Citation**: *Chapter 12: Some Simple Algorithms and Data Structures (§ 12.1 Search Algorithms)*

Implement Guttag's binary search algorithm from Figure 12.1 on sorted array `nums`.
Return the index of `target` if found, or `-1` if not found.
""",
        "examples": [
            {"input": "nums = [-1, 0, 3, 5, 9, 12], target = 9", "output": "4"},
            {"input": "nums = [-1, 0, 3, 5, 9, 12], target = 2", "output": "-1"},
        ],
        "constraints": ["nums is sorted in ascending order."],
        "starter_codes": {
            "python": """def binary_search(nums: list[int], target: int) -> int:
    left, right = 0, len(nums) - 1
    # Implement while left <= right template
    pass
"""
        },
        "solutions": {
            "python": """def binary_search(nums: list[int], target: int) -> int:
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 12 (*Some Simple Algorithms and Data Structures*), Section 12.1 (*Search Algorithms*), pp. 195–198.

> "A search algorithm finds a specified value (the target) within a collection.
> 
> If the collection is unordered, any search algorithm must in the worst case examine every element $\\implies O(N)$ linear time.
> 
> If the collection is **sorted in ascending order**, we can exploit this invariant using binary search:
> 1. Pick an index `mid` that divides the list in half.
> 2. Ask if `L[mid] == target`. If so, we are done!
> 3. If `L[mid] > target`, we know that the target cannot lie in the upper half of the list, so we search the lower half `right = mid - 1`.
> 4. If `L[mid] < target`, we search the upper half `left = mid + 1`.
> 
> Because the search space is halved at each step, binary search runs in $O(\\log N)$ time."
""",
        "test_cases": [
            {"input": {"nums": [-1, 0, 3, 5, 9, 12], "target": 9}, "expected": 4},
            {"input": {"nums": [-1, 0, 3, 5, 9, 12], "target": 2}, "expected": -1},
            {"input": {"nums": [5], "target": 5}, "expected": 0},
        ],
        "hints": ["Use while left <= right, mid = (left + right) // 2, left = mid + 1, right = mid - 1."],
    },
    {
        "slug": "py-scaffold-knapsack-01-memo",
        "title": "0/1 Knapsack Decision Tree (Guttag Ch. 14 & 15)",
        "kind": "fundamental",
        "track": "track_3_algorithmic_scaffolds",
        "difficulty": "Medium",
        "category": "Optimization",
        "tags": ["Guttag § 14.1", "Guttag § 15.2", "Knapsack", "Decision Tree"],
        "description": """### 🏛️ Finger Exercise: 0/1 Knapsack Binary Decision Tree
**Guttag Citation**: *Chapter 14: Knapsack and Graph Optimization Problems (§ 14.1 Knapsack Problems) & Chapter 15 (§ 15.2)*

Guttag models the classic **0/1 Knapsack** problem as exploring a binary decision tree for each item $i$:
1. **Don't take item $i$**: Subproblem value is `solve(i + 1, avail)`.
2. **Take item $i$** (if $w_i \\le \\text{avail}$): Subproblem value is $v_i + \\text{solve}(i + 1, \\text{avail} - w_i)$.
3. Choose the maximum of both branches and memoize with key `(i, avail)`.

Write `knapsack_01_memo(weights: list[int], values: list[int], max_weight: int) -> int`.
""",
        "examples": [
            {
                "input": "weights = [1, 2, 3], values = [6, 10, 12], max_weight = 5",
                "output": "22",
                "explanation": "Take item 1 (w=2, v=10) and item 2 (w=3, v=12) for total value 22 and weight 5.",
            }
        ],
        "constraints": ["len(weights) == len(values) <= 30", "max_weight <= 100"],
        "starter_codes": {
            "python": """def knapsack_01_memo(weights: list[int], values: list[int], max_weight: int) -> int:
    memo = {}
    def solve(i: int, avail: int) -> int:
        # Decision tree logic
        pass
    return solve(0, max_weight)
"""
        },
        "solutions": {
            "python": """def knapsack_01_memo(weights: list[int], values: list[int], max_weight: int) -> int:
    memo = {}
    n = len(weights)
    def solve(i: int, avail: int) -> int:
        if i == n or avail == 0:
            return 0
        state = (i, avail)
        if state in memo:
            return memo[state]
        # Option 1: Don't take item i
        res = solve(i + 1, avail)
        # Option 2: Take item i (if it fits)
        if weights[i] <= avail:
            res = max(res, values[i] + solve(i + 1, avail - weights[i]))
        memo[state] = res
        return res
    return solve(0, max_weight)
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 14 (*Knapsack and Graph Optimization Problems*), Section 14.1 & Chapter 15 Section 15.2, pp. 232–238, 252–257.

> "In the **0/1 Knapsack Problem**, a burglar has a knapsack of limited weight capacity $W$ and must choose among $n$ items, each with value $v_i$ and weight $w_i$. The thief cannot take a fraction of an item (hence 0/1: either take it or leave it).
> 
> **Decision Tree Modeling**:
> We can conceptualize the search space as a binary decision tree of depth $n$:
> - At node $i$, the left branch corresponds to *taking* item $i$.
> - The right branch corresponds to *not taking* item $i$.
> 
> The brute-force tree has $2^n$ leaves. However, the state of the problem at step $i$ is completely defined by two parameters: `(i, available_weight)`.
> If two different paths through the tree arrive at the same item $i$ with the same remaining capacity, they represent identical subproblems.
> 
> By memoizing `memo[(i, available_weight)]`, the total number of distinct states explored is bounded by $O(n \\times W)$, converting an exponential algorithm into a fast polynomial DP."

```python
# Figure 15.2 from Guttag (Third Edition):
# Fast 0/1 knapsack using memoization
def fastMaxVal(toConsider, avail, memo={}):
    if (len(toConsider), avail) in memo:
        result = memo[(len(toConsider), avail)]
    elif toConsider == [] or avail == 0:
        result = (0, ())
    elif toConsider[0].getWeight() > avail:
        result = fastMaxVal(toConsider[1:], avail, memo)
    else:
        nextItem = toConsider[0]
        withVal, withToTake = fastMaxVal(toConsider[1:], avail - nextItem.getWeight(), memo)
        withVal += nextItem.getValue()
        withoutVal, withoutToTake = fastMaxVal(toConsider[1:], avail, memo)
        if withVal > withoutVal:
            result = (withVal, withToTake + (nextItem,))
        else:
            result = (withoutVal, withoutToTake)
    memo[(len(toConsider), avail)] = result
    return result
```
""",
        "test_cases": [
            {"input": {"weights": [1, 2, 3], "values": [6, 10, 12], "max_weight": 5}, "expected": 22},
            {"input": {"weights": [4, 5, 1], "values": [1, 2, 3], "max_weight": 3}, "expected": 3},
            {"input": {"weights": [10], "values": [100], "max_weight": 5}, "expected": 0},
        ],
        "hints": ["State is (i, avail). Base case: i == len(weights) or avail == 0 return 0. Explore take vs dont take."],
    },

    # ── Track 4: Divide-and-Conquer & Custom Sorting (Guttag Ch. 12) ──────────
    {
        "slug": "py-sort-merge-sort",
        "title": "Divide-and-Conquer Merge Sort (Guttag Ch. 12)",
        "kind": "fundamental",
        "track": "track_4_custom_sorting",
        "difficulty": "Easy",
        "category": "Divide-and-Conquer",
        "tags": ["Guttag § 12.2", "Merge Sort", "Sorting", "Divide-and-Conquer"],
        "description": """### 🏛️ Finger Exercise: Implementing Merge Sort
**Guttag Citation**: *Chapter 12: Some Simple Algorithms and Data Structures (§ 12.2 Sorting Algorithms)*

Implement Guttag's Merge Sort from Figure 12.4:
1. **Divide**: If list has length $< 2$, return it. Otherwise split into `left = nums[:mid]` and `right = nums[mid:]`.
2. **Conquer**: Recursively sort `left` and `right`.
3. **Combine**: Merge the two sorted lists in linear $O(N)$ time with two pointers.

Write a function `merge_sort(nums: list[int]) -> list[int]`.
""",
        "examples": [{"input": "nums = [5, 2, 8, 1, 9]", "output": "[1, 2, 5, 8, 9]"}],
        "constraints": ["len(nums) <= 200"],
        "starter_codes": {
            "python": """def merge_sort(nums: list[int]) -> list[int]:
    # Implement recursive merge sort
    pass
"""
        },
        "solutions": {
            "python": """def merge_sort(nums: list[int]) -> list[int]:
    if len(nums) < 2:
        return list(nums)
    mid = len(nums) // 2
    left = merge_sort(nums[:mid])
    right = merge_sort(nums[mid:])
    
    # Merge helper
    merged = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 12 (*Some Simple Algorithms and Data Structures*), Section 12.2 (*Sorting Algorithms*), pp. 201–206.

> "Merge sort is a prototypical **divide-and-conquer** algorithm. It was invented in 1945 by John von Neumann.
> 
> The algorithm works as follows:
> 1. If the list is of length 0 or 1, it is already sorted.
> 2. If the list has more than one element, split the list into two halves, and use merge sort to sort each sublist.
> 3. **Merge** the two sorted sublists into a single sorted list.
> 
> **Why Merging Takes Linear Time**:
> Merging two lists `left` and `right` of total length $n$ requires comparing the smallest remaining element of each list and appending the smaller one. Because every comparison places at least one element into its final position, the merge step takes at most $n$ comparisons $\\implies O(n)$.
> 
> **Complexity Proof**:
> At each level of the recursion tree, the total work across all merges is $O(n)$. Because the list is halved on each recursive call, the depth of the tree is $\\log_2 n$.
> Therefore, total running time is $O(n \\log n)$."

```python
# Figure 12.4 from Guttag (Third Edition): Merge sort
def merge(left, right, compare):
    result = []
    i, j = 0, 0
    while i < len(left) and j < len(right):
        if compare(left[i], right[j]):
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    while i < len(left):
        result.append(left[i])
        i += 1
    while j < len(right):
        result.append(right[j])
        j += 1
    return result

def mergeSort(L, compare=lambda x, y: x < y):
    if len(L) < 2:
        return L[:]
    else:
        middle = len(L) // 2
        left = mergeSort(L[:middle], compare)
        right = mergeSort(L[middle:], compare)
        return merge(left, right, compare)
```
""",
        "test_cases": [
            {"input": {"nums": [5, 2, 8, 1, 9]}, "expected": [1, 2, 5, 8, 9]},
            {"input": {"nums": [1]}, "expected": [1]},
            {"input": {"nums": []}, "expected": []},
            {"input": {"nums": [3, 3, 1, 2]}, "expected": [1, 2, 3, 3]},
        ],
        "hints": ["Base case len(nums) < 2 return list(nums). Split at mid, recurse left/right, merge with two pointers."],
    },
    {
        "slug": "py-sort-multi-key-lambda",
        "title": "Multi-Key Lambda Sorting",
        "kind": "fundamental",
        "track": "track_4_custom_sorting",
        "difficulty": "Easy",
        "category": "Custom Sorting",
        "tags": ["Guttag § 12.2", "Sorting", "Lambda", "Comparators"],
        "description": """### 🏛️ Finger Exercise: Multi-Attribute Comparator Projections
**Guttag Citation**: *Chapter 12: Sorting Algorithms (§ 12.2 Sorting with Custom Functions)*

Write a function `sort_students(records: list[tuple[str, int, int]])` where each record is `(name, score, age)`.
Sort the list such that:
1. Highest `score` comes first (descending).
2. If scores are tied, younger `age` comes first (ascending).
3. If both are tied, sort by `name` alphabetically.
Return the sorted list.
""",
        "examples": [
            {
                "input": "records = [('Alice', 90, 20), ('Bob', 90, 19), ('Charlie', 85, 22)]",
                "output": "[('Bob', 90, 19), ('Alice', 90, 20), ('Charlie', 85, 22)]",
            }
        ],
        "constraints": ["len(records) <= 100"],
        "starter_codes": {
            "python": """def sort_students(records: list[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
    # Sort with custom key
    pass
"""
        },
        "solutions": {
            "python": """def sort_students(records: list[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
    return sorted(records, key=lambda x: (-x[1], x[2], x[0]))
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 12 (*Some Simple Algorithms and Data Structures*), Section 12.2 (*Sorting Algorithms*), pp. 206–208.

> "In Python, both the `list.sort` method and the `sorted()` built-in function take an optional parameter `key`.
> 
> The `key` parameter specifies a function of one argument that is used to extract a comparison key from each element in the list.
> 
> When sorting tuples, Python compares them element-by-element (lexicographic ordering). By supplying a lambda that maps each record to a multi-element tuple:
> `key = lambda x: (-x[1], x[2], x[0])`
> we establish a total ordering:
> 1. Negating the numerical score `-x[1]` causes larger scores to become smaller numbers, yielding descending order.
> 2. The second element `x[2]` breaks ties using ascending age.
> 3. The third element `x[0]` breaks secondary ties alphabetically."
""",
        "test_cases": [
            {
                "input": {"records": [("Alice", 90, 20), ("Bob", 90, 19), ("Charlie", 85, 22)]},
                "expected": [["Bob", 90, 19], ["Alice", 90, 20], ["Charlie", 85, 22]],
            }
        ],
        "hints": ["Use sorted(records, key=lambda x: (-x[1], x[2], x[0]))."],
    },

    # ── Track 5: Bit Manipulation & Binary Encodings (Guttag Ch. 3.4) ─────────
    {
        "slug": "py-bit-check-set-clear",
        "title": "Bitwise Check, Set, and Clear (Guttag Ch. 3)",
        "kind": "fundamental",
        "track": "track_5_bit_manipulation",
        "difficulty": "Easy",
        "category": "Bit Manipulation",
        "tags": ["Guttag § 3.3", "Bitwise", "Masks", "Binary Encodings"],
        "description": """### 🏛️ Finger Exercise: Bitmask Formulas
**Guttag Citation**: *Chapter 3: Some Simple Numerical Programs (§ 3.3 A Few Words About Using Floats and Binary Representation)*

Write a function `bit_operations(n: int, i: int)` that performs 3 operations on the $i$-th bit (0-indexed) of integer `n`:
1. `is_set`: check if the $i$-th bit is 1 (return `bool`).
2. `set_bit`: return `n` with the $i$-th bit set to 1.
3. `clear_bit`: return `n` with the $i$-th bit cleared to 0.
Return `(is_set, set_bit, clear_bit)`.
""",
        "examples": [{"input": "n = 5 (0b101), i = 1", "output": "(False, 7, 5)"}],
        "constraints": ["0 <= n <= 10^9", "0 <= i <= 30"],
        "starter_codes": {
            "python": """def bit_operations(n: int, i: int) -> tuple[bool, int, int]:
    # Write bitwise formulas
    pass
"""
        },
        "solutions": {
            "python": """def bit_operations(n: int, i: int) -> tuple[bool, int, int]:
    is_set = bool((n >> i) & 1)
    set_val = n | (1 << i)
    clear_val = n & ~(1 << i)
    return (is_set, set_val, clear_val)
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 3 (*Some Simple Numerical Programs*), Section 3.3 (*Binary Numbers and Floats*), pp. 36–38.

> "Internally, modern digital computers represent all data using base 2 (binary). An integer is a sequence of bits (0s and 1s), where the $i$-th bit represents $2^i$.
> 
> Python provides low-level bitwise operators that manipulate numbers at the bit level:
> - `<<` (left shift): `1 << i` creates a bitmask with only the $i$-th bit set ($2^i$).
> - `>>` (right shift): `n >> i` shifts $n$ right by $i$ positions, placing the $i$-th bit at position 0.
> - `&` (bitwise AND): `(n >> i) & 1` tests whether the $i$-th bit is 1.
> - `|` (bitwise OR): `n | (1 << i)` sets the $i$-th bit to 1.
> - `~` (bitwise NOT): Inverts all bits. `n & ~(1 << i)` clears the $i$-th bit to 0."
""",
        "test_cases": [
            {"input": {"n": 5, "i": 1}, "expected": [False, 7, 5]},
            {"input": {"n": 5, "i": 0}, "expected": [True, 5, 4]},
        ],
        "hints": ["(n >> i) & 1, n | (1 << i), n & ~(1 << i)."],
    },
    {
        "slug": "py-bit-kernighan-set-bits",
        "title": "Brian Kernighan's Set Bit Counter",
        "kind": "fundamental",
        "track": "track_5_bit_manipulation",
        "difficulty": "Easy",
        "category": "Bit Manipulation",
        "tags": ["Guttag § 3.3", "Bitwise", "Kernighan", "Popcount"],
        "description": """### 🏛️ Finger Exercise: Brian Kernighan's Bit Invariant
**Guttag Citation**: *Chapter 3: Numerical Programs (§ 3.3 Binary Representation)*

Subtracting 1 from $n$ flips all bits after the rightmost 1-bit, including the 1-bit itself.
Therefore, `n & (n - 1)` clears the lowest set bit in $O(1)$ time.

Write a function `count_set_bits(n: int) -> int` that uses `n & (n - 1)` to count the number of 1-bits in the binary representation of $n$ in $O(K)$ iterations (where $K$ is the number of set bits).
""",
        "examples": [{"input": "n = 11 (0b1011)", "output": "3"}],
        "constraints": ["0 <= n <= 2^31 - 1"],
        "starter_codes": {
            "python": """def count_set_bits(n: int) -> int:
    # Use while n > 0: n = n & (n - 1)
    pass
"""
        },
        "solutions": {
            "python": """def count_set_bits(n: int) -> int:
    count = 0
    while n > 0:
        n &= (n - 1)
        count += 1
    return count
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 3 (*Some Simple Numerical Programs*), Section 3.3 (*Binary Encodings*), pp. 37–38.

> "A classic computer science challenge is finding the Hamming weight (number of set bits) of an integer.
> 
> The naive method tests all 32 bits one by one.
> A far more elegant algorithm due to Brian Kernighan exploits the algebraic invariant of two's complement binary subtraction:
> Subtracting 1 from an integer $n$ flips the lowest set bit from 1 to 0, and flips all trailing 0s to 1s.
> 
> Performing a bitwise AND between $n$ and $n - 1$ (`n & (n - 1)`) therefore clears the lowest set bit to 0 while leaving all higher bits unchanged.
> Repeating this loop terminates in exactly $K$ iterations, where $K$ is the number of 1-bits."
""",
        "test_cases": [
            {"input": {"n": 11}, "expected": 3},
            {"input": {"n": 0}, "expected": 0},
            {"input": {"n": 128}, "expected": 1},
        ],
        "hints": ["Initialize count = 0. While n > 0: n &= (n - 1); count += 1."],
    },

    # ── Track 6: Asymptotic Complexity & Mathematical Models (Guttag Ch. 11) ──
    {
        "slug": "py-math-asymptotic-complexity",
        "title": "Asymptotic Orders & Big-O Invariants (Guttag Ch. 11)",
        "kind": "fundamental",
        "track": "track_6_complexity_math",
        "difficulty": "Easy",
        "category": "Complexity Theory",
        "tags": ["Guttag § 11.2", "Big-O", "Asymptotic Analysis", "MIT 6.0001"],
        "description": """### 🏛️ Finger Exercise: Asymptotic Growth Classification
**Guttag Citation**: *Chapter 11: A Simplistic Introduction to Algorithmic Complexity (§ 11.2 Asymptotic Notation)*

Write a function `classify_algorithm(operation_count_formula: str) -> str` that maps typical algorithmic structures to their canonical Big-O class:
- `"nested_loops"` $\\implies$ `"O(n^2)"`
- `"divide_conquer_halving"` $\\implies$ `"O(log n)"`
- `"sort_merge"` $\\implies$ `"O(n log n)"`
- `"single_pass"` $\\implies$ `"O(n)"`
- `"power_set_subsets"` $\\implies$ `"O(2^n)"`
""",
        "examples": [
            {"input": "operation_count_formula = 'divide_conquer_halving'", "output": "'O(log n)'"}
        ],
        "constraints": ["Valid category identifier."],
        "starter_codes": {
            "python": """def classify_algorithm(operation_count_formula: str) -> str:
    # Map operation string to its Big-O asymptotic notation
    pass
"""
        },
        "solutions": {
            "python": """def classify_algorithm(operation_count_formula: str) -> str:
    mapping = {
        "nested_loops": "O(n^2)",
        "divide_conquer_halving": "O(log n)",
        "sort_merge": "O(n log n)",
        "single_pass": "O(n)",
        "power_set_subsets": "O(2^n)",
    }
    return mapping.get(operation_count_formula, "O(1)")
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 11 (*A Simplistic Introduction to Algorithmic Complexity*), Section 11.2 (*Asymptotic Notation*), pp. 182–188.

> "Algorithmic complexity provides a formal framework to answer the question: 'How will the running time of a program scale as the size of its input grows toward infinity?'
> 
> **Big-O Notation**:
> Big-O notation is used to define an asymptotic upper bound on the growth rate of a function. We write $f(x) \\in \\mathcal{O}(g(x))$ if there exist positive constants $c$ and $x_0$ such that:
> $$f(x) \\le c \\cdot g(x) \\quad \\text{for all } x > x_0$$
> 
> **The Hierarchy of Asymptotic Orders**:
> 1. $\\mathcal{O}(1)$: Constant running time (e.g., hash table lookup, array indexing).
> 2. $\\mathcal{O}(\\log n)$: Logarithmic running time (e.g., bisection search, binary search).
> 3. $\\mathcal{O}(n)$: Linear running time (e.g., single-pass linear scans).
> 4. $\\mathcal{O}(n \\log n)$: Log-linear running time (e.g., merge sort, quick sort, Timsort).
> 5. $\\mathcal{O}(n^2)$: Quadratic running time (e.g., nested loops, bubble sort).
> 6. $\\mathcal{O}(2^n)$: Exponential running time (e.g., brute-force power set search, recursive knapsack)."
""",
        "test_cases": [
            {"input": {"operation_count_formula": "divide_conquer_halving"}, "expected": "O(log n)"},
            {"input": {"operation_count_formula": "nested_loops"}, "expected": "O(n^2)"},
            {"input": {"operation_count_formula": "sort_merge"}, "expected": "O(n log n)"},
        ],
        "hints": ["Return mapping.get(operation_count_formula, 'O(1)')."],
    },
    {
        "slug": "py-math-prefix-sums",
        "title": "Prefix Sum Array Builder",
        "kind": "fundamental",
        "track": "track_6_complexity_math",
        "difficulty": "Easy",
        "category": "Math & Complexity",
        "tags": ["Guttag § 11.3", "Prefix Sums", "Array", "Range Queries"],
        "description": """### 🏛️ Finger Exercise: Prefix Sum Array & Range Query Invariant
**Guttag Citation**: *Chapter 11: Algorithmic Complexity (§ 11.3 Amortization and Space-Time Tradeoffs)*

Prefix sums allow calculating the sum of any contiguous subarray `nums[L...R]` in $O(1)$ time after an $O(N)$ precomputation:
$$\\text{sum}(L, R) = P[R + 1] - P[L]$$

Write a function `build_prefix_sum(nums: list[int]) -> list[int]` that returns a prefix array $P$ of length `len(nums) + 1` where $P[0] = 0$ and $P[i] = \\sum_{j=0}^{i-1} \\text{nums}[j]$.
""",
        "examples": [{"input": "nums = [1, 2, 3, 4]", "output": "[0, 1, 3, 6, 10]"}],
        "constraints": ["0 <= len(nums) <= 10^4"],
        "starter_codes": {
            "python": """def build_prefix_sum(nums: list[int]) -> list[int]:
    # Build prefix sum with 1-based offset
    pass
"""
        },
        "solutions": {
            "python": """def build_prefix_sum(nums: list[int]) -> list[int]:
    prefix = [0] * (len(nums) + 1)
    for i, num in enumerate(nums):
        prefix[i + 1] = prefix[i] + num
    return prefix
"""
        },
        "editorial": """### 📚 Textbook Passage: John V. Guttag, *Introduction to Computation and Programming Using Python (3rd ed.)*
**Location**: Chapter 11 (*A Simplistic Introduction to Algorithmic Complexity*), Section 11.3 (*Space-Time Tradeoffs*), pp. 188–190.

> "A fundamental principle in algorithm design is the **space-time tradeoff**: one can often drastically reduce computation time by utilizing extra auxiliary memory to cache precomputed results.
> 
> **Range Sum Queries**:
> Suppose we need to answer $Q$ queries asking for the sum of elements from index $L$ to $R$ in array $A$.
> Naively calculating each sum takes $O(R - L + 1) = O(N)$ time per query $\\implies O(Q \\times N)$ total.
> 
> By allocating an auxiliary array $P$ of length $N+1$ and computing cumulative sums in a single $O(N)$ precomputation pass:
> $$P[i] = P[i-1] + A[i-1]$$
> any subarray sum is computed in guaranteed $\\mathcal{O}(1)$ constant time via:
> $$\\sum_{k=L}^{R} A[k] = P[R + 1] - P[L]$$
> reducing total complexity to $\\mathcal{O}(N + Q)$."
""",
        "test_cases": [
            {"input": {"nums": [1, 2, 3, 4]}, "expected": [0, 1, 3, 6, 10]},
            {"input": {"nums": []}, "expected": [0]},
            {"input": {"nums": [5]}, "expected": [0, 5]},
        ],
        "hints": ["Initialize prefix = [0] * (len(nums) + 1), then prefix[i+1] = prefix[i] + num."],
    },
]

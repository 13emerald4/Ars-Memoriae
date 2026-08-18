"""Pre-LeetCode Fundamentals & Python Basics Catalog.

Grounded at a high level in John V. Guttag's 'Introduction to Computation and Programming
Using Python' (MIT 6.0001 / 6.0002).

Provides 36 progressive micro-drills across 7 tracks building cognitive reflex
automaticity on Python primitives, mathematical invariants, and core algorithmic scaffolds.
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
        "tags": ["Guttag Ch. 2", "Types", "Type Casting", "Scalar Primitives"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 2: Introduction to Python)
**Principle**: *Scalar Types, Type Conversions & Truthiness*

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
        "editorial": """### 🏛️ Guttag Principle: Types and Scalar Objects (Ch. 2.1)
- Python is dynamically typed but **strongly typed**: an object's type determines the operations that can be performed on it.
- `int(s)` parses a valid numeric string into an arbitrary-precision integer.
- `str(n)` converts an object to its canonical string representation.
- `float(s)` parses IEEE 754 floating-point numbers.
- `bool(x)` evaluates Python truthiness: `0`, `None`, `""`, `[]`, `{}`, `set()` evaluate to `False`; all non-zero/non-empty objects evaluate to `True`.
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
        "tags": ["Guttag Ch. 2", "Arithmetic", "Modulo", "Floor Division"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 2: Introduction to Python)
**Principle**: *Integer Division Invariant: $a = b \\times (a // b) + (a \\% b)$*

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
        "editorial": """### 🏛️ Guttag Principle: Arithmetic & Modulo Rules (Ch. 2.1)
- Python's `//` operator performs **floor division**, which always rounds towards negative infinity:
  - `7 // 2 = 3`
  - `-7 // 2 = -4` (unlike C++/Java which truncates towards zero to produce `-3`).
- The fundamental mathematical invariant holds in Python: `a == (a // b) * b + (a % b)`.
- `divmod(a, b)` computes both values simultaneously in a single low-level opcode.
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
        "tags": ["Guttag Ch. 3", "Bisection Search", "Approximation", "MIT 6.0001"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 3: Simple Numerical Programs)
**Principle**: *Monotonic Interval Halving & Error Bound Guarantees*

In Guttag's classic numerical framework, finding the square root of $x \\ge 1$ is framed as searching within a bounded interval $[low, high] = [0, x]$.
Write a function `bisection_sqrt(x: float, epsilon: float = 0.01) -> float` that finds an approximation $ans$ such that $|ans^2 - x| \\le \\epsilon$.

**Algorithm**:
1. Initialize `low = 0.0`, `high = max(1.0, x)`.
2. Compute `ans = (low + high) / 2.0`.
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
        "editorial": """### 🏛️ Guttag Principle: Bisection Search & Convergence (Ch. 3.2)
- **Why this unlocks LeetCode**: Bisection search on continuous domains is the direct theoretical foundation of **Binary Search on the Answer Space** (e.g. *Koko Eating Bananas*, *Capacity to Ship Packages*).
- **Logarithmic Convergence**: In each iteration, the search interval $[low, high]$ is halved. The total iterations required to reach precision $\\epsilon$ is guaranteed to be $O(\\log_2((high - low) / \\epsilon))$.
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
        "tags": ["Guttag Ch. 3", "Newton-Raphson", "Calculus", "Optimization"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 3: Simple Numerical Programs)
**Principle**: *Quadratic Convergence via Tangent Line Successive Refinements*

Guttag introduces the **Newton-Raphson** method for finding roots of polynomials $f(y) = y^2 - k = 0$.
The successive approximation update rule is:
$$y_{new} = y - \\frac{f(y)}{f'(y)} = y - \\frac{y^2 - k}{2y}$$

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
        "editorial": """### 🏛️ Guttag Principle: Newton-Raphson & Computational Efficiency (Ch. 3.3)
- While Bisection Search converges linearly ($1$ bit of precision per iteration), Newton-Raphson exhibits **quadratic convergence** (the number of correct decimal digits doubles on each iteration).
- This establishes the core algorithmic lesson: problem structure (smoothness/derivatives) enables exponentially faster convergence than blind search.
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
        "title": "Nested Helper Scope & Nonlocal (Guttag Ch. 4)",
        "kind": "fundamental",
        "track": "track_0_python_basics",
        "difficulty": "Easy",
        "category": "Python Basics",
        "tags": ["Guttag Ch. 4", "Scope", "Stack Frames", "Recursion Helper"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 4: Functions & Scoping)
**Principle**: *Environment Model of Execution, Stack Frames & Lexical Bindings*

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
        "editorial": """### 🏛️ Guttag Principle: Scoping & Symbol Tables (Ch. 4.2)
- When a function is called, Python creates a new **stack frame** (local environment).
- By default, assigning to a name inside a function creates a binding in the local frame.
- `nonlocal` explicitly binds the identifier to the nearest enclosing non-global scope, preventing accidental shadowing.
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
        "tags": ["Guttag Ch. 5", "Mutability", "Aliasing", "Side-Effects"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 5: Structured Types & Mutability)
**Principle**: *Object Identity vs Value Equality: Aliasing & In-Place Mutation*

Guttag highlights a classic computational bug: **mutating a list while iterating over it**.
When you remove an element during iteration, the list index shifts left, causing subsequent elements to be skipped!

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
        "editorial": """### 🏛️ Guttag Principle: Aliasing and Mutability (Ch. 5.2.1)
- If two variables `L1` and `L2` point to the same list (`L2 = L1`), mutating `L1.append(4)` changes `L2` as well because they share the same memory identity (`id(L1) == id(L2)`).
- To create an independent copy, use cloning: `L2 = L1[:]` or `L2 = list(L1)` or a list comprehension `[x for x in L1]`.
- Never modify the length of a mutable collection while an iterator is traversing it!
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
        "tags": ["Guttag Ch. 4", "Higher-Order Functions", "Lambdas", "First-Class"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 4: Functions & Abstraction)
**Principle**: *Functions as First-Class Mathematical Objects*

Guttag demonstrates that functions can be passed as arguments, returned as values, and bound to variables.
Write a function `apply_scaling(nums: list[int], factor: int, offset: int) -> list[int]` that creates an internal lambda function `transform = lambda x: (x * factor) + offset` and uses `[transform(x) for x in nums]` to return the transformed array.
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
        "editorial": """### 🏛️ Guttag Principle: First-Class Functions (Ch. 4.4)
- Treating functions as first-class objects allows building general algorithmic scaffolding (e.g., custom search predicates, comparator keys, mapping operators).
- In Python, `lambda x: expression` creates an anonymous function inline.
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
        "tags": ["Guttag Ch. 5", "2D Matrix", "List Comprehension", "Aliasing Trap"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 5: Structured Types)
**Principle**: *Avoiding Shallow Pointer Replication in Multidimensional Grids*

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
        "editorial": """### 🏛️ Guttag Principle: Multidimensional References (Ch. 5.3)
- In `[[0] * C] * R`, `* R` creates shallow references to the same single row object.
- The idiomatic Python construction creates a distinct inner list in each iteration:
  `[[default_val] * C for _ in range(R)]`.
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
        "tags": ["Guttag Ch. 10", "OOP", "ADT", "Representation Invariant"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 10: Classes & OOP)
**Principle**: *Abstract Data Types (ADTs) & Representation Invariants*

Guttag defines an **Abstract Data Type (ADT)** as a set of objects and operations that preserve a formal **representation invariant**.
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
        "editorial": """### 🏛️ Guttag Principle: ADTs and Encapsulation (Ch. 10.1)
- An ADT enforces a **data abstraction barrier**: callers interact through abstract operations (`insert`, `remove`), while the implementation guarantees invariant consistency (e.g. sorted uniqueness).
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
        "tags": ["Guttag Ch. 10", "Deque", "Queue", "FIFO"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 10: Data Structures)
**Principle**: *First-In-First-Out (FIFO) Order & Amortized $O(1)$ Operations*

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
        "editorial": """### 🏛️ Guttag Principle: Queues and FIFO Invariants (Ch. 10.3)
- `collections.deque` uses a doubly-linked chain of contiguous memory blocks, guaranteeing strict $O(1)$ push/pop at both ends.
- This is the mandatory backbone for all Breadth-First Search (BFS) graph and tree traversals.
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
        "tags": ["Guttag Ch. 6", "Recursion", "Induction", "Divide-and-Conquer"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 6: Recursion)
**Principle**: *Inductive Decomposition: Base Case & State Reduction*

Guttag defines recursive problem solving via **mathematical induction**:
1. **Base Case**: A string of length $0$ or $1$ is vacuously a palindrome.
2. **Inductive Step**: A string $s$ of length $> 1$ is a palindrome if and only if $s[0] == s[-1]$ **AND** the inner substring $s[1:-1]$ is a palindrome.

Write a recursive function `is_palindrome_inductive(s: str) -> bool` that implements this exact inductive logic (assume string is already lowercased and clean).
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
        "editorial": """### 🏛️ Guttag Principle: Inductive Thinking in Recursion (Ch. 6.1)
- Every valid recursive algorithm requires two components:
  1. At least one **base case** directly solvable without further recursion.
  2. An **inductive step** that transforms the problem into a strictly smaller subproblem, ensuring progression towards the base case.
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
        "tags": ["Guttag Ch. 15", "Dynamic Programming", "Memoization", "Decision Trees"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 15: Dynamic Programming)
**Principle**: *Optimal Substructure & Overlapping Subproblems*

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
        "editorial": """### 🏛️ Guttag Principle: Memoization and Dynamic Programming (Ch. 15.1)
- Dynamic Programming applies when a problem exhibits:
  1. **Optimal Substructure**: The optimal solution to the problem contains within it optimal solutions to subproblems.
  2. **Overlapping Subproblems**: The same subproblems are solved multiple times across branches of the decision tree.
- Memoization trades memory ($O(n)$ space table) to eliminate redundant exponential computation.
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
        "tags": ["Guttag Ch. 12", "Binary Search", "Template"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 12: Search & Sorting)
**Principle**: *Binary Search on Sorted Collections*

Write a function `binary_search(nums: list[int], target: int) -> int` that implements the classic binary search template on a sorted array `nums`.
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
        "editorial": """### 🏛️ Guttag Principle: Search Complexity (Ch. 12.1)
- Linear search takes $O(N)$ comparisons.
- Bisection search on sorted structures eliminates half the remaining candidates on each comparison, running in $O(\\log N)$ time.
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
        "tags": ["Guttag Ch. 14", "Guttag Ch. 15", "Knapsack", "Decision Tree"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 14 & 15: Optimization Problems)
**Principle**: *Binary Decision Tree: Take vs Don't-Take*

Guttag models the classic **0/1 Knapsack** problem as exploring a binary decision tree for each item $i$:
1. **Don't take item $i$**: Subproblem value is `knapsack(i + 1, avail_weight)`.
2. **Take item $i$** (if $w_i \\le \\text{avail_weight}$): Subproblem value is $v_i + \\text{knapsack}(i + 1, \\text{avail_weight} - w_i)$.
3. Choose the maximum of both branches and memoize with key `(i, avail_weight)`.

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
        "editorial": """### 🏛️ Guttag Principle: Knapsack & Optimization (Ch. 14.1 & 15.2)
- The binary decision tree represents all $2^n$ subsets.
- By caching state `(item_index, remaining_capacity)`, the number of distinct states is bounded by $N \\times W$, converting an NP-hard exponential brute force into a pseudo-polynomial $O(N \\times W)$ DP algorithm.
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
        "tags": ["Guttag Ch. 12", "Merge Sort", "Sorting", "Divide-and-Conquer"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 12: Sorting Algorithms)
**Principle**: *$O(N \\log N)$ Divide-and-Conquer Recurrence*

Guttag details **Merge Sort** as the canonical divide-and-conquer algorithm:
1. **Divide**: If list has length $< 2$, it is already sorted. Otherwise split into `left = nums[:mid]` and `right = nums[mid:]`.
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
        "editorial": """### 🏛️ Guttag Principle: Merge Sort Analysis (Ch. 12.2)
- Recurrence relation: $T(N) = 2T(N/2) + O(N)$.
- By the Master Theorem, the recursion tree has depth $\\log_2 N$ with $O(N)$ work at each level $\\implies O(N \\log N)$ total time complexity.
- Merge sort is **stable** (preserves the original relative order of equivalent keys).
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
        "tags": ["Guttag Ch. 12", "Sorting", "Lambda", "Comparators"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 12: Sorting Algorithms)
**Principle**: *Total Preorders & Multi-Attribute Key Projections*

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
        "editorial": """### 🏛️ Guttag Principle: Multi-Key Projections (Ch. 12.2)
- Python's sorting engine (Timsort) performs lexicographic tuple comparisons.
- Key `lambda x: (-x[1], x[2], x[0])` projects each record into a comparison tuple where inverting `-x[1]` flips sort direction to descending.
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
        "tags": ["Guttag Ch. 3", "Bitwise", "Masks", "Binary Encodings"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 3: Binary Numbers & Radix)
**Principle**: *Binary Radix Representations & Bitmask Operators*

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
        "editorial": """### 🏛️ Guttag Principle: Binary Encodings (Ch. 3.4)
- Bitwise operators operate directly on the two's complement binary representation:
  - Mask creation: `1 << i`
  - Bit testing: `(n >> i) & 1`
  - Bit setting: `n | (1 << i)`
  - Bit clearing: `n & ~(1 << i)`
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
        "tags": ["Guttag Ch. 3", "Bitwise", "Kernighan", "Popcount"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 3: Binary Numbers)
**Principle**: *Algebraic Identity: $n \\ \\& \\ (n - 1)$ Clears Lowest Set Bit*

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
        "editorial": """### 🏛️ Guttag Principle: Bit Invariants (Ch. 3.4)
- Naive popcount checks all 32 bits ($O(32)$).
- Brian Kernighan’s loop executes exactly once per 1-bit, terminating immediately when all set bits are extinguished ($O(K)$).
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
        "tags": ["Guttag Ch. 11", "Big-O", "Asymptotic Analysis", "MIT 6.0001"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 11: Algorithmic Complexity)
**Principle**: *Asymptotic Dominance & Orders of Growth*

Guttag formalizes algorithmic complexity through **asymptotic dominance**:
$$\\mathcal{O}(1) < \\mathcal{O}(\\log n) < \\mathcal{O}(n) < \\mathcal{O}(n \\log n) < \\mathcal{O}(n^2) < \\mathcal{O}(2^n)$$

Write a function `classify_algorithm(operation_count_formula: str) -> str` that maps typical algorithmic loop structures to their canonical Big-O class:
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
        "editorial": """### 🏛️ Guttag Principle: Asymptotic Growth Laws (Ch. 11.2)
- Asymptotic analysis focuses on scalability as input size $n \\to \\infty$.
- Additive law: $O(f(n)) + O(g(n)) = O(\\max(f(n), g(n)))$.
- Multiplicative law: nested loops multiply complexities $O(f(n)) \\times O(g(n)) = O(f(n) \\times g(n))$.
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
        "tags": ["Guttag Ch. 11", "Prefix Sums", "Array", "Range Queries"],
        "description": """### 🏛️ Guttag Computational Invariant (MIT 6.0001 — Chapter 11: Complexity Optimization)
**Principle**: *Precomputation Tradeoff: $O(N)$ Space for $O(1)$ Range Queries*

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
        "editorial": """### 🏛️ Guttag Principle: Precomputation & Caching (Ch. 11.3)
- Range queries naively take $O(R - L + 1) = O(N)$ per query $\\implies O(Q \\times N)$ for $Q$ queries.
- Prefix sums precalculate cumulative values in $O(N)$, reducing all subsequent range queries to $O(1)$ time $\\implies O(N + Q)$ total.
""",
        "test_cases": [
            {"input": {"nums": [1, 2, 3, 4]}, "expected": [0, 1, 3, 6, 10]},
            {"input": {"nums": []}, "expected": [0]},
            {"input": {"nums": [5]}, "expected": [0, 5]},
        ],
        "hints": ["Initialize prefix = [0] * (len(nums) + 1), then prefix[i+1] = prefix[i] + num."],
    },
]

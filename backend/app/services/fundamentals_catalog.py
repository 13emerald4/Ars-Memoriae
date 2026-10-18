"""Pre-LeetCode Fundamentals & Python Basics Catalog.

Grounded foundationally in MIT 6.0001: 'Introduction to Computer Science and
Programming in Python' (MIT OpenCourseWare / Profs. John V. Guttag, Eric Grimson,
and Dr. Ana Bell) and the official companion textbook 'Introduction to Computation
and Programming Using Python' (Third Edition, MIT Press).

Grounded in John V. Guttag's 'Introduction to Computation and Programming
Using Python' (Third Edition, MIT Press / MIT 6.0001 & 6.0002).

Each lesson provides an in-depth reading covering theoretical foundations, the
textbook's argument, canonical code, common pitfalls, and LeetCode transfer models.

Citation conventions
--------------------
* Chapter, section, and figure references were checked against the 3rd-edition PDF.
  Figures use the book's own hyphenated numbering (Figure 12-5, not Figure 12.4).
* Blockquotes and code listings are **paraphrases and reconstructions**, not verbatim
  transcriptions: the figure listings in the source PDF are images, so their exact text
  could not be extracted. Prose claims attributed to Guttag were verified against the
  extracted body text.
* Page numbers are deliberately omitted - the source PDF carries no printed page
  numbers, so any page citation would be unverifiable.
* Lessons covering material that is genuinely **not in the book** (bitwise operations,
  Brian Kernighan's algorithm, prefix sums, collections.deque) are labeled
  "Beyond the Book" in their tags and carry an explicit warning in the description.
"""

from __future__ import annotations

FUNDAMENTALS_CATALOG = [
    # ── Track 0: Python Core & Numerical Programs (MIT 6.0001 Lec 1–3, Pset 1) ──────────
    {
        "slug": "py-basics-type-casting",
        "title": "Type Casting & Conversions",
        "kind": "fundamental",
        "track": "track_0_python_basics",
        "difficulty": "Easy",
        "category": "Python Basics",
        "tags": ["MIT 6.0001 Lec 1", "Guttag § 2.2", "Types", "Type Casting", "Scalar Primitives"],
        "description": """### Finger Exercise: Type Conversions & Scalar Evaluation
**MIT 6.0001 Citation**: *Chapter 2: Introduction to Python (§ 2.2 The Basic Elements of Python)*

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
        "editorial": """# Chapter 2: Introduction to Python (§ 2.2 The Basic Elements of Python)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Objects, Types, and the Computation Model
A computer program is a sequence of definitions and commands that manipulate data objects. In Python's computational model, **everything is an object**, and every object has:
1. An **Identity** (an integer representing its memory address, inspectable via `id(x)`).
2. A **Type** (which defines what values it can hold and what operations can be performed on it, inspectable via `type(x)`).
3. A **Value** (the actual data stored in the memory representation).

Types in Python are fundamentally divided into two categories:
- **Scalar Types**: Primitive, indivisible objects with no accessible internal structure (e.g., `int`, `float`, `bool`, `NoneType`).
- **Non-Scalar Types**: Composite objects that possess internal structure and contain references to other objects (e.g., `str`, `list`, `tuple`, `dict`, `set`).

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 2, § 2.2 — paraphrased summary of the argument, not a verbatim quotation)*

> "Python is a **strongly typed** language with **dynamic type binding**.
> 
> By 'strongly typed', we mean that type mismatches are detected and flagged as errors (e.g., attempting to add `'42' + 1` raises an immediate `TypeError` rather than silently coercing types like JavaScript or C).
> By 'dynamically typed', we mean that variable names are merely labels (pointers) bound to objects in the heap; the type is an intrinsic attribute of the object itself, not the variable name.
> 
> #### The Four Primary Scalar Primitives:
> 1. **`int` (Arbitrary-Precision Integers)**: Unlike C, C++, or Java where integers are bounded by fixed hardware word sizes (e.g., 32-bit `[-2^31, 2^31-1]` or 64-bit `[-2^63, 2^63-1]`), Python 3 integers have **unbounded precision**. They can grow to arbitrary magnitudes limited only by the available memory on the machine ($2^{10000}$ computes instantly without overflow).
> 2. **`float` (Real Numbers)**: Floats are represented using standard IEEE 754 double-precision (64 bits: 1 sign bit, 11 exponent bits, 53 mantissa bits). Because binary fractions cannot represent all decimal fractions exactly (e.g., $0.1_{10} = 0.0001100110011..._2$), testing floating-point numbers with exact equality `==` is hazardous and should almost always use approximate tolerance $|a - b| < \\epsilon$.
> 3. **`bool` (Boolean Truth Values)**: The type `bool` has exactly two literals: `True` and `False`. In Python, `bool` is a subclass of `int` where `True == 1` and `False == 0`.
> 4. **`NoneType`**: Contains a solitary literal `None`, used to denote the absence of a return value or an uninitialized state.
> 
> #### Type Conversions (Casting) & Truthiness Rules:
> Type conversions are invoked by calling the type name as a constructor function:
> - `int('100')` parses decimal digits into an integer object. Optional radix: `int('1010', 2)` parses binary $\\implies 10$.
> - `float('3.14')` parses standard float representation.
> - `str(x)` produces the canonical human-readable string representation of object $x$.
> - `bool(x)` evaluates the **truthiness** of object $x$.
> 
> Python defines standard truth-value evaluation:
> An object is considered `False` if and only if it is:
> - `None` or `False`
> - Zero of any numeric type: `0`, `0.0`, `0j`
> - Any empty sequence or collection: `''`, `()`, `[]`, `{}`, `set()`, `range(0)`
> All other objects evaluate to `True`."

---

### § 3. Canonical Code Walkthrough
```python
# Demonstrating scalar types, identity, and explicit casting
val_str = "42"
num = 10

# 1. Type Casting
int_val = int(val_str)      # 42 (type: int)
str_val = str(num)          # '10' (type: str)
float_val = float(val_str)  # 42.0 (type: float)
bool_val = bool(num)        # True (because 10 != 0)

# 2. Dynamic Identity Inspection
x = 256
y = 256
print(x is y)  # True (CPython caches small integers [-5, 256])

a = 1000
b = 1000
print(a is b)  # False (different heap allocations, though a == b is True)
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **Implicit Coercion Fallacy**: You cannot perform `5 + "10"`. Python demands explicit casting: `5 + int("10")` or `str(5) + "10"`.
2. **Float Precision Loss**: `0.1 + 0.2 == 0.3` evaluates to `False` in Python due to IEEE 754 rounding (`0.1 + 0.2` is `0.30000000000000004`).
3. **Empty Collection Truthiness**: In conditional branching, writing `if len(arr) > 0:` is un-Pythonic. Idiomatic Python uses `if arr:` directly.

---

### § 5. Bridging to LeetCode Mastery
- **Stack & Queue Empty Checks**: In LeetCode problems (*Valid Parentheses*, *Daily Temperatures*), checking `while stack:` relies on empty collection `False` truthiness.
- **String Parsing & Digit Extraction**: Problems like *String to Integer (atoi)*, *Add Strings*, and *Multiply Strings* test manual character casting using ASCII offsets `ord(c) - ord('0')` vs `int(c)`.
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
        "tags": ["MIT 6.0001 Lec 1", "Guttag § 2.2.1", "Arithmetic", "Modulo", "Floor Division"],
        "description": """### Finger Exercise: Integer Division Invariant
**MIT 6.0001 Citation**: *Chapter 2: Introduction to Python (§ 2.2.1 Objects, Expressions, and Numerical Types)*

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
        "editorial": """# Chapter 2: Introduction to Python (§ 2.2.1 Objects, Expressions, and Numerical Types)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Mathematical Semantics of Integer Division
In arithmetic computing, division on integers produces two fundamental quantities: a **quotient** $q$ and a **remainder** $r$.
The fundamental division theorem states that for any integer dividend $a$ and non-zero integer divisor $b$, there exist unique integers $q$ and $r$ such that:
$$a = b \\cdot q + r \\quad \\text{where } 0 \\le |r| < |b|$$

However, computer programming languages differ in how they round non-integer quotients:
- **Truncating Division (C, C++, Java)**: Rounds quotient towards zero ($7/2 = 3$, $-7/2 = -3$).
- **Floor Division (Python, Ruby)**: Rounds quotient towards **negative infinity** ($7 // 2 = 3$, $-7 // 2 = -4$).

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 2, § 2.2.1 — paraphrased summary of the argument, not a verbatim quotation)*

> "The operators on numeric types include:
> - `/` (**True Division**): Always returns a float representing the exact mathematical quotient (e.g., `6 / 2` evaluates to `3.0`, not `3`).
> - `//` (**Floor Division**): Computes the quotient and applies the floor function $\\lfloor a / b \\rfloor$, which returns the largest integer less than or equal to the algebraic quotient.
> - `%` (**Modulo / Remainder**): Computes the remainder of floor division.
> 
> The relationship between `//` and `%` is governed by the invariant:
> $$a == (a // b) * b + (a \\% b)$$
> 
> Because Python's `//` rounds down toward $-\\infty$, the sign of the modulo remainder `a % b` in Python is **always identical to the sign of the divisor `b`** (unlike C++ where the remainder takes the sign of the dividend `a`).
> 
> For example:
> - $7 // 2 = 3$, and $7 \\% 2 = 1 \\implies 2 \\times 3 + 1 = 7$
> - $-7 // 2 = -4$, and $-7 \\% 2 = 1 \\implies 2 \\times (-4) + 1 = -7$
> - $7 // -2 = -4$, and $7 \\% -2 = -1 \\implies -2 \\times (-4) + (-1) = 7$
> 
> Python provides the built-in function `divmod(a, b)`, which returns the pair `(a // b, a % b)` in one call."

> Note: `divmod` is not discussed by Guttag; the floor-division and modulo semantics above are. Most CPUs do compute
> quotient and remainder in a single divide instruction, but that is a hardware note, not a claim from the text.

---

### § 3. Canonical Code Walkthrough
```python
# Verifying the Fundamental Division Invariant across positive & negative integers
def verify_division_invariant(a: int, b: int) -> bool:
    q = a // b
    r = a % b
    invariant_holds = (a == b * q + r)
    divmod_tuple = divmod(a, b)
    assert divmod_tuple == (q, r)
    return invariant_holds

assert verify_division_invariant(7, 2)    # q=3, r=1
assert verify_division_invariant(-7, 2)   # q=-4, r=1
assert verify_division_invariant(7, -2)   # q=-4, r=-1
assert verify_division_invariant(-7, -2)  # q=3, r=-1
```

---

### § 4. Common Pitfalls & Invariant Traps
1. **The Negative Modulo Trap**: In C++/Java, `-7 % 10` evaluates to `-7`. In Python, `-7 % 10` evaluates to `3`. If your LeetCode problem requires negative modulo behavior matching C++ truncation (such as *Reverse Integer*), you must write `int(a / b)` rather than `a // b`.
2. **Circular Array Index Wrapping**: When moving left in a circular buffer of size $N$, `(curr_idx - 1) % N` automatically handles negative wraparound in Python because `-1 % N == N - 1`. In C++, you would have to write `(curr_idx - 1 + N) % N`.

---

### § 5. Bridging to LeetCode Mastery
- **Digit Stripping & Reconstruction**: In *Reverse Integer*, *Palindrome Number*, and *Add Two Numbers*, extracting least significant digits uses `digit = n % 10` and stripping uses `n //= 10`.
- **2D Matrix Coordinate Flattening & Unflattening**:
  - Unflattening 1D index $k$ into 2D grid of width $C$: `row = k // C`, `col = k % C`.
  - Flattening 2D `(row, col)` into 1D index: `k = row * C + col`.
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
        "tags": ["MIT 6.0001 Lec 3", "MIT 6.0001 Pset 1", "Bisection Search", "Approximation"],
        "description": """### Finger Exercise: Bisection Search Approximation
**MIT 6.0001 Citation**: *Chapter 3: Some Simple Numerical Programs (§ 3.2 Approximate Solutions and Bisection Search)*

Implement Guttag's classic bisection search algorithm from Figure 3-5 to find the square root of $x \\ge 1$.
Write a function `bisection_sqrt(x: float, epsilon: float = 0.01) -> float` that finds an approximation $ans$ such that $|ans^2 - x| \\le \\epsilon$.

**Algorithm (Figure 3-5)**:
1. `low = 0.0`, `high = max(1.0, x)`
2. `ans = (low + high) / 2.0`
3. While $|ans^2 - x| > \\epsilon$:
   - If $ans^2 < x$: `low = ans`
   - Else: `high = ans`
   - `ans = (low + high) / 2.0`
4. Return `round(ans, 2)`.

> Note: `epsilon` bounds the error on $ans^2$, not on $ans$. With $\\epsilon = 0.01$ only about two decimal places of the root are actually justified, so the result is rounded to 2 — reporting more digits would advertise precision the method did not deliver.
""",
        "examples": [
            {"input": "x = 25.0, epsilon = 0.01", "output": "5.0"},
            {"input": "x = 2.0, epsilon = 0.01", "output": "1.41"},
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
    return round(ans, 2)
"""
        },
        "editorial": """# Chapter 3: Some Simple Numerical Programs (§ 3.2 Approximate Solutions & Bisection Search)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Interval Halving on Monotonic Functions
Numerical computation frequently requires finding roots of non-linear equations $f(y) = 0$ (such as finding $y$ such that $y^2 - x = 0$).
When an exact analytical closed-form solution is impossible or inefficient, we seek an **approximate numerical solution** within an error tolerance $\\epsilon > 0$:
$$|f(y)| \\le \\epsilon$$

The simplest approach is **Exhaustive Enumeration** (linear search with small step size $\\text{step}$). If we search for $\\sqrt{x}$ with $\\text{step} = 0.00001$, finding $\\sqrt{25}$ requires $500,000$ loop iterations.
If $x = 10^6$, exhaustive search becomes completely intractable.

**Bisection Search** (binary chop on continuous intervals) exploits the **Intermediate Value Theorem**:
If a function $f(y) = y^2 - x$ is continuous and monotonically increasing on $[low, high]$, and $f(low) < 0 < f(high)$, then there is guaranteed to exist a root $y^* \\in [low, high]$.
By testing the midpoint $mid = (low + high) / 2$, we can eliminate half the search space in every step.

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 3, § 3.2 — paraphrased summary of the argument, not a verbatim quotation)*

> "Suppose we know that the square root of $x$ lies somewhere in the interval $[low, high]$. We can evaluate our guess at the midpoint:
> $$ans = \\frac{low + high}{2}$$
> If $ans^2 < x$, then because $y^2$ is monotonically increasing for $y \\ge 0$, no value in $[low, ans]$ can possibly be the square root. We can discard the entire lower half of the interval and set $low = ans$.
> 
> Conversely, if $ans^2 > x$, no value in $[ans, high]$ can be the root, so we discard the upper half and set $high = ans$.
> 
> **Why Bisection Search is Exponentially Faster**:
> At each step, the size of the search interval is cut strictly in half.
> If the initial search interval has length $L_0 = high - low$, then after $k$ bisection steps, the interval length is:
> $$L_k = \\frac{L_0}{2^k}$$
> To achieve precision $\\epsilon$, we require $\\frac{L_0}{2^k} \\le \\epsilon$, which implies:
> $$k \\ge \\log_2\\left(\\frac{L_0}{\\epsilon}\\right)$$
> 
> While exhaustive enumeration takes time proportional to $\\frac{L_0}{\\epsilon}$ (linear complexity), bisection search takes time proportional to $\\log_2(\\frac{L_0}{\\epsilon})$ (logarithmic complexity).
> For $L_0 = 100$ and $\\epsilon = 0.0001$:
> - Exhaustive enumeration: $1,000,000$ iterations.
> - Bisection search: $\\lceil \\log_2(1,000,000) \\rceil = 20$ iterations!"

---

### § 3. Canonical Code Walkthrough (after Guttag Figure 3-5)
```python
# After Guttag Figure 3-5, "Using bisection search to approximate square root"
x = 25
epsilon = 0.01
numGuesses = 0
low = 0.0
high = max(1.0, x)  # Note: if 0 < x < 1, sqrt(x) > x, so upper bound must be max(1.0, x)
ans = (high + low) / 2.0

while abs(ans**2 - x) >= epsilon:
    numGuesses += 1
    if ans**2 < x:
        low = ans
    else:
        high = ans
    ans = (high + low) / 2.0

print(f'numGuesses = {numGuesses}')
print(f'{ans} is close to square root of {x}')
```

---

### § 4. Mathematical Complexity Derivation
$$\\text{Initial Interval Width: } W_0 = \\max(1, x)$$
$$\\text{Width after } k \\text{ iterations: } W_k = \\frac{W_0}{2^k}$$
$$\\text{Termination Condition: } W_k \\le \\epsilon \\implies 2^k \\ge \\frac{W_0}{\\epsilon} \\implies k = \\mathcal{O}\\left(\\log_2 \\frac{W_0}{\\epsilon}\\right)$$
The convergence rate is strictly linear in terms of digits of accuracy, requiring $\\approx 3.32$ bisection steps per decimal digit of precision.

---

### § 5. Bridging to LeetCode Mastery
This continuous bisection search is the direct foundation of one of LeetCode's most important hard paradigms: **Binary Search on the Answer Array**.
- **LeetCode 875 (Koko Eating Bananas)**: The speed $k$ is monotonic. If Koko can finish all piles at speed $mid$, she can finish at any speed $> mid$. Search space $[1, \\max(piles)]$ is bisected.
- **LeetCode 1011 (Capacity to Ship Packages Within D Days)**: Search capacity range $[\\max(weights), \\sum weights]$.
- **LeetCode 410 (Split Array Largest Sum)**: Bisect answer space $[\\max(nums), \\sum nums]$.
""",
        "test_cases": [
            {"input": {"x": 25.0, "epsilon": 0.01}, "expected": 5.0},
            {"input": {"x": 4.0, "epsilon": 0.001}, "expected": 2.0},
            {"input": {"x": 9.0, "epsilon": 0.01}, "expected": 3.0},
        ],
        "hints": ["Use low = 0.0, high = max(1.0, x), halve with ans = (low + high) / 2.0, and return round(ans, 2)."],
    },
    {
        "slug": "py-basics-newton-raphson",
        "title": "Newton-Raphson Successive Approximations",
        "kind": "fundamental",
        "track": "track_0_python_basics",
        "difficulty": "Easy",
        "category": "Numerical Programs",
        "tags": ["MIT 6.0001 Lec 3", "Guttag § 3.4", "Newton-Raphson", "Root Finding"],
        "description": """### Finger Exercise: Newton-Raphson Root Finding
**MIT 6.0001 Citation**: *Chapter 3: Some Simple Numerical Programs (§ 3.4 Newton-Raphson)*

Implement Guttag's Newton-Raphson root finder from Figure 3-7 for $f(y) = y^2 - k = 0$.
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
        "editorial": """# Chapter 3: Some Simple Numerical Programs (§ 3.4 Newton-Raphson Approximation)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Tangent Line Approximations
The Newton-Raphson method (often called Newton's method) is a calculus-based iterative root-finding algorithm.
Suppose we wish to find a root $r$ such that $f(r) = 0$, and we have an initial guess $y_0$.
Using the Taylor series expansion of $f(y)$ around $y_0$:
$$f(y) \\approx f(y_0) + f'(y_0)(y - y_0)$$
Setting $f(y) = 0$ to solve for the root intercept $y_1$:
$$0 = f(y_0) + f'(y_0)(y_1 - y_0) \\implies y_1 = y_0 - \\frac{f(y_0)}{f'(y_0)}$$

Geometrically, Newton-Raphson draws the tangent line to the curve $y = f(x)$ at $(y_0, f(y_0))$ and finds where this tangent line intersects the x-axis. This x-intercept becomes the next guess $y_1$.

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 3, § 3.4 — paraphrased summary of the argument, not a verbatim quotation)*

> "The most commonly used approximation algorithm for finding polynomial roots is usually attributed to Isaac Newton and Joseph Raphson.
> 
> For finding the square root of a number $k$, we want to find the root of the polynomial:
> $$f(y) = y^2 - k$$
> The first derivative with respect to $y$ is:
> $$f'(y) = 2y$$
> Substituting $f(y)$ and $f'(y)$ into the Newton-Raphson formula gives:
> $$y_{new} = y - \\frac{y^2 - k}{2y} = \\frac{1}{2}\\left(y + \\frac{k}{y}\\right)$$
> 
> Notice the intuitive beauty of this update formula: if $y$ is an overestimate of $\\sqrt{k}$, then $k/y$ is an underestimate. Averaging the two values $\\frac{1}{2}(y + k/y)$ yields a remarkably superior estimate.
> 
> **Quadratic Convergence**:
> Newton-Raphson converges **quadratically**. If the error at step $n$ is $\\epsilon_n$, the error at step $n+1$ is proportional to $\\epsilon_n^2$.
> This means that once the algorithm is close to the root, **the number of correct significant decimal digits doubles on every single iteration!**"

---

### § 3. Canonical Code Walkthrough (after Guttag Figure 3-7)
```python
# After Guttag Figure 3-7, "Implementation of Newton-Raphson method"
# Find x such that x**2 - 24 is within epsilon of 0
epsilon = 0.01
k = 24.0
guess = k / 2.0
numGuesses = 0

while abs(guess**2 - k) >= epsilon:
    numGuesses += 1
    guess = guess - (((guess**2) - k) / (2 * guess))

print(f'numGuesses = {numGuesses}')
print(f'{guess} is close to square root of {k}')
```

---

### § 4. Comparative Convergence Table
| Iteration $k$ | Bisection Search Guess ($k=24$) | Newton-Raphson Guess ($k=24$) |
| :--- | :--- | :--- |
| **0** | $12.0$ (Error: $120.0$) | $12.0$ (Error: $120.0$) |
| **1** | $6.0$ (Error: $12.0$) | $7.0$ (Error: $25.0$) |
| **2** | $3.0$ (Error: $15.0$) | $5.214285$ (Error: $3.18$) |
| **3** | $4.5$ (Error: $3.75$) | $4.900295$ (Error: $0.012$) |
| **4** | $5.25$ (Error: $3.56$) | $4.898979$ (Error: $0.000001$) |
| **Total Steps to $\\epsilon = 10^{-5}$** | **23 iterations** | **4 iterations** |

---

### § 5. Bridging to LeetCode Mastery
- **LeetCode 69 (Sqrt(x))**: Can be solved in $O(1)$ iterations using integer Newton-Raphson update `x1 = (x0 + n // x0) // 2`.
- **LeetCode 50 (Pow(x, n)) & Numerical Computations**: Demonstrates the principle of successive refinement vs brute force loops.
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
        "tags": ["MIT 6.0001 Lec 4", "Guttag § 4.1", "Scope", "Stack Frames", "LEGB Rule"],
        "description": """### Finger Exercise: Scoping & Stack Frames
**MIT 6.0001 Citation**: *Chapter 4: Functions, Scoping, and Abstraction (§ 4.1 Functions and Scoping)*

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
        "editorial": """# Chapter 4: Functions, Scoping, and Abstraction (§ 4.1 Functions and Scoping)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Lexical Scoping & Activation Records
When a program executes, the runtime environment maintains a **Call Stack** composed of **Stack Frames** (or activation records).
Each function invocation pushes a new stack frame containing:
1. Formal parameters bound to actual arguments.
2. Local variables allocated during execution.
3. The return address in the calling frame.

Python resolves identifiers using the **LEGB Rule**:
- **L (Local)**: Names assigned inside the current function frame.
- **E (Enclosing)**: Names in the local scope of any enclosing/outer functions (closures).
- **G (Global)**: Names assigned at top-level module scope.
- **B (Built-in)**: Pre-defined built-in names (`len`, `range`, `dict`, `int`).

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 4, § 4.1 — paraphrased summary of the argument, not a verbatim quotation)*

> "A function definition introduces a new name into the current environment and creates a function object. When a function is called, the interpreter creates a new symbol table (environment frame).
> 
> **Variable Binding Mechanics**:
> If a variable is assigned a value anywhere within the body of a function (`x = 5`), Python treats `x` as a **local variable** throughout the entire function frame.
> 
> This can lead to the classic `UnboundLocalError`:
> ```python
> count = 0
> def increment():
>     count = count + 1  # FAILS! count on right-hand side is treated as uninitialized local
> ```
> 
> To modify a variable defined in an enclosing parent function frame without creating a local shadowing variable, Python 3 introduced the `nonlocal` keyword.
> 
> When `nonlocal count` is declared inside a nested helper function, Python binds assignments directly to the nearest enclosing non-global scope, enabling clean lexical state encapsulation."

---

### § 3. Canonical Code Walkthrough
```python
def outer_search_engine(data: list[int]) -> int:
    match_count = 0
    max_seen = float('-inf')

    def dfs_helper(node_val: int):
        nonlocal match_count, max_seen  # Enclosing frame state binding
        if node_val > max_seen:
            max_seen = node_val
            match_count += 1

    for item in data:
        dfs_helper(item)

    return match_count
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **Assignment anywhere makes the name local everywhere.** Python decides scope
   statically, for the whole function body, before a line runs. So this fails on the
   *read*, not the write:

   ```python
   count = 0
   def bump():
       count = count + 1      # UnboundLocalError: count referenced before assignment
   ```

   The `count` on the right is already classified local because of the assignment on the
   left. `nonlocal count` (enclosing scope) or `global count` (module scope) fixes it.

2. **Reading needs no declaration; only rebinding does.** A helper can freely *read* an
   enclosing variable. The declaration is required only when you assign to the name.

3. **Mutating is not rebinding.** `results.append(x)` needs no `nonlocal`, because it
   mutates the object rather than rebinding the name. `results = []` does need it. This is
   why the mutable-accumulator pattern works without any declaration at all.

4. **`nonlocal` and `global` are different targets.** `nonlocal` binds to the nearest
   *enclosing function* scope and fails at compile time if there is none. `global` binds at
   module level. A helper nested one deep inside `solve()` wants `nonlocal`.

5. **The LEGB order is fixed: Local, Enclosing, Global, Built-in.** Shadowing a builtin
   (`list`, `sum`, `max`, `id`) at any inner level hides it from everything below.

6. **Prefer returning values when the recursion is small.** `nonlocal` is the clean answer
   for a running maximum threaded through a deep DFS; for a two-line helper, returning a
   tuple is easier to test.

---

### § 5. Bridging to LeetCode Mastery
- **DFS Tree Traversals with Global Counters**: In problems like *Diameter of Binary Tree*, *Binary Tree Maximum Path Sum*, and *Count Good Nodes in Binary Tree*, writing a recursive helper function `def dfs(node):` that updates `nonlocal max_diameter` avoids messy return tuples or mutable class properties.
""",
        "test_cases": [
            {"input": {"events": [1, -2, 3, 0, 5]}, "expected": 3},
            {"input": {"events": [-1, -2, -3]}, "expected": 0},
            {"input": {"events": [10, 20]}, "expected": 2},
        ],
        "hints": ["Inside process(), write 'nonlocal count' before modifying count."],
    },

    # ── Track 1: Structured Types, Mutability & Scoping (MIT 6.0001 Lec 4–5, Pset 2) ──
    {
        "slug": "py-fluency-mutability-aliasing",
        "title": "List Mutability & Aliasing Trap (Guttag Ch. 5)",
        "kind": "fundamental",
        "track": "track_1_pythonic_fluency",
        "difficulty": "Easy",
        "category": "Structured Types",
        "tags": ["MIT 6.0001 Lec 5", "Guttag § 5.3", "Mutability", "Aliasing", "Side-Effects"],
        "description": """### Finger Exercise: Mutating While Iterating & Aliasing
**MIT 6.0001 Citation**: *Chapter 5: Structured Types and Mutability (§ 5.3 Lists and Mutability)*

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
        "editorial": """# Chapter 5: Structured Types and Mutability (§ 5.3 Lists and Mutability)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Pointers, Heap Allocation, and Identity
In Python, non-scalar structured types (such as `list`, `dict`, `set`) are mutable heap-allocated objects.
A variable in Python does not store the list data directly; it stores a **pointer (reference)** to the list header in memory.

When you execute:
```python
L1 = [1, 2, 3]
L2 = L1  # Creates an ALIAS, not a copy!
```
`L1` and `L2` point to the exact same physical memory address (`id(L1) == id(L2)`).
Any mutation `L1.append(4)` modifies the underlying heap buffer, so evaluating `L2` immediately reflects `[1, 2, 3, 4]`.
This is called **Aliasing Side-Effects**.

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 5, § 5.3.1 Cloning — paraphrased summary of the argument, not a verbatim quotation)*

> "Lists are mutable sequences of values. Unlike tuples and strings, individual elements of a list can be modified in-place.
> 
> **The Mutating-While-Iterating Bug**:
> One of the most subtle and common bugs in Python programs occurs when mutating a list while iterating over it with a `for` loop.
> 
> Guttag makes this point in his discussion of list mutability:
> ```python
> # Mutating a list while iterating over it
> def remove_dups(L1, L2):
>     \"\"\"Assumes that L1 and L2 are lists.
>        Removes any element from L1 that also occurs in L2\"\"\"
>     for e in L1:
>         if e in L2:
>             L1.remove(e)
> ```
> Suppose `L1 = [1, 2, 3, 4]` and `L2 = [1, 2, 5, 6]`.
> If you run `remove_dups(L1, L2)`, you would expect `L1` to become `[3, 4]`.
> Instead, `L1` becomes `[2, 3, 4]`! The element `2` was never removed!
> 
> **Why this happens**:
> The Python interpreter maintains an internal integer index for the `for` loop, starting at 0:
> 1. At iteration 0, index is 0, element is `1`. `1` is in `L2`, so `L1.remove(1)` is executed.
> 2. `L1.remove(1)` shifts all elements left: `L1` is now `[2, 3, 4]`.
> 3. For the next iteration, the loop counter advances to **index 1**.
> 4. At index 1, the element is now `3`! The element `2` (which slid into index 0) was completely skipped!
> 
> **The Golden Rule**:
> Never mutate a list during iteration. Instead, iterate over a sliced shallow clone `for e in L1[:]` or construct a new list with a comprehension: `[e for e in L1 if e not in L2]`."

---

### § 3. Canonical Code Walkthrough
```python
# Safe vs Unsafe Filtering
nums = [1, 2, 3, 4, 5, 6]

# UNSAFE: In-place removal during loop
# for x in nums: if x % 2 != 0: nums.remove(x) # SKIPS ELEMENTS!

# SAFE 1: List Comprehension (Idiomatic & O(N))
evens = [x for x in nums if x % 2 == 0]

# SAFE 2: Sliced Clone Iteration
for x in nums[:]:
    if x % 2 != 0:
        nums.remove(x)  # Safe because loop counter tracks clone, though remove() is O(N^2)
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **Guttag's rule, stated plainly: "It is usually prudent to avoid mutating a list over
   which one is iterating."** The `for` loop holds a hidden integer counter, incremented
   after each iteration and compared against the list's *current* length. Remove an element
   and every later element slides down one slot while the counter still moves up — so exactly
   one element gets skipped per removal.

2. **`new_L = L` does not help.** Guttag calls this out explicitly: it "would not create a
   copy of `L`, but would merely introduce a new name for the existing list." Only
   `L[:]`, `L.copy()`, `list(L)` or a comprehension actually copy.

3. **Shallow copies share their contents.** `L[:]` and `L.copy()` both build a new outer
   list holding *the same objects*. For a list of lists, mutating an inner list is still
   visible through both. `copy.deepcopy(L)` is the fix when the elements are themselves
   mutable.

   ```python
   L = [2]
   L1 = [L]
   L2 = L1[:]           # shallow
   L.append(3)
   print(L1, L2)        # [[2, 3]] [[2, 3]]  -- both see it
   ```

4. **Iterating a clone is safe but still $O(n^2)$.** `for e in L1[:]` fixes correctness, not
   speed: each `L1.remove(e)` is itself $O(n)$. The comprehension
   `[e for e in L1 if e not in L2]` is the idiomatic and faster answer.

5. **`==` is not `is`.** Two lists can hold equal values and be different objects. Use `==`
   for value comparison and reserve `is` for identity (and for `None`).

6. **The backtracking corollary.** `result.append(path)` stores an alias to the live path
   object, which the recursion then keeps mutating — so every entry ends up identical (often
   empty). `result.append(path[:])` snapshots it.

---

### § 5. Bridging to LeetCode Mastery
- **Backtracking & Subsets**: In LeetCode 78 (*Subsets*) and LeetCode 46 (*Permutations*), appending the current path to the result list requires cloning `result.append(list(path))` or `result.append(path[:])`. If you write `result.append(path)`, every entry in `result` aliases the exact same `path` object, which gets emptied at the end of recursion resulting in `[[], [], []]`.
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
        "tags": ["MIT 6.0001 Lec 4", "Guttag § 4.4", "Higher-Order Functions", "Lambdas"],
        "description": """### Finger Exercise: First-Class Functions
**MIT 6.0001 Citation**: *Chapter 4: Functions, Scoping, and Abstraction (§ 4.4 Functions as Objects)*

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
        "editorial": """# Chapter 4: Functions, Scoping, and Abstraction (§ 4.4 Functions as Objects)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: First-Class Mathematical Objects
In computational abstraction, an entity is called a **first-class citizen** if it can be:
1. Passed as an argument to a function.
2. Returned as a value from a function.
3. Assigned to a variable or data structure element.

In Python, **functions are first-class objects**. A function name is simply a variable bound to a callable function object.
Functions that accept other functions as arguments or return functions are called **Higher-Order Functions**.

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 4, § 4.4 — paraphrased summary of the argument, not a verbatim quotation)*

> "Treating functions as first-class objects allows programmers to build highly general algorithmic abstractions.
> 
> For example, consider a general transformation function:
> ```python
> def applyToEach(L, f):
>     \"\"\"Assumes L is a list, f is a function.
>        Mutates L by replacing each element, e, of L by f(e)\"\"\"
>     for i in range(len(L)):
>         L[i] = f(L[i])
> ```
> We can pass `abs`, `int`, or any custom function to `applyToEach`.
> 
> **Anonymous Functions (Lambdas)**:
> Python provides the `lambda` reserved word to define anonymous functions anonymously inline:
> `lambda <parameters>: <single_expression>`
> 
> Lambdas are syntactically restricted to a single expression (no statements or assignments). They are especially useful when writing custom sort keys and transformation pipelines."

---

### § 3. Canonical Code Walkthrough
```python
# Higher-order comparator projections
points = [(1, 9), (5, 2), (3, 7)]

# Sort by second coordinate descending
points.sort(key=lambda p: -p[1])  # Result: [(1, 9), (3, 7), (5, 2)]
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **A `lambda` is a single *expression*, not a body.** No statements, no assignments, no
   `return`, no multi-line logic. The moment you want a branch, `def` is the answer —
   `lambda x: a if cond else b` is the limit of what belongs inline.

2. **Late binding: lambdas capture the *variable*, not its value.** All three functions
   below return `4`, because each captured the same `i`, whose final value is 2:

   ```python
   fs = [lambda x: x * i for i in range(3)]
   [f(2) for f in fs]                # [4, 4, 4]  -- not [0, 2, 4]

   fs = [lambda x, i=i: x * i for i in range(3)]   # bind at definition time
   [f(2) for f in fs]                # [0, 2, 4]
   ```

3. **`map` and `filter` return lazy iterators in Python 3.** They are consumed once. Wrap
   in `list(...)` if you need to iterate twice, or use a comprehension, which most readers
   find clearer anyway.

4. **A function object is not a call.** `sorted(L, key=len)` passes the function;
   `sorted(L, key=len(L))` calls it and passes an integer. Dropping or adding parentheses
   here is a common and confusing error.

5. **Assigning a lambda to a name defeats the point.** `f = lambda x: x + 1` is just a
   worse `def f(x): return x + 1` — it loses the useful `__name__` in tracebacks. Use
   `lambda` where a function is *passed*, not where one is *defined*.

6. **`key=` is evaluated once per element; a comparator would be once per comparison.**
   This is why Python dropped `cmp` in favour of `key` — $O(n)$ evaluations rather than
   $O(n \\log n)$. When you genuinely need pairwise logic, wrap it in
   `functools.cmp_to_key`.

---

### § 5. Bridging to LeetCode Mastery
- **Custom Priority Queue Comparators & Sorting**: In LeetCode 56 (*Merge Intervals*), intervals are sorted by start time `intervals.sort(key=lambda x: x[0])`. In LeetCode 692 (*Top K Frequent Words*), words are sorted with multi-key lambdas `sorted(count.keys(), key=lambda w: (-count[w], w))`.
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
        "tags": ["MIT 6.0001 Lec 5", "Guttag § 5.3.1", "2D Matrix", "List Comprehension"],
        "description": """### Finger Exercise: 2D Matrix Memory Initialization
**MIT 6.0001 Citation**: *Chapter 5: Structured Types and Mutability (§ 5.3.1 Cloning, § 5.3.2 List Comprehension)*

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
        "editorial": """# Chapter 5: Structured Types and Mutability (§ 5.3.1 Cloning, § 5.3.2 List Comprehension)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Shallow Pointer Replication vs Deep Allocation
When the list multiplication operator `L * n` is evaluated, Python creates a new list containing $n$ references pointing to the elements of `L`.
If `L = [0]`, `[0] * 3` creates `[0, 0, 0]`. Because `0` is an immutable scalar integer, modifying one index replaces that pointer and causes no side-effects.

However, if `row = [0, 0, 0]` is a **mutable list object**, writing:
```python
grid = [row] * 3
```
creates an outer list containing 3 pointers, **all pointing to the exact same inner `row` object in the heap**.

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 5, § 5.3.1 — paraphrased summary of the argument, not a verbatim quotation)*

> "Multidimensional structured arrays in Python are represented as lists of lists.
> 
> A catastrophic bug arises when attempting to initialize a matrix using the shorthand:
> `matrix = [[0] * cols] * rows`
> 
> Let us trace what happens when you write `matrix[0][0] = 1`:
> 1. `matrix[0]` resolves to the single inner list object in the heap.
> 2. Index 0 of that object is mutated to `1`.
> 3. But `matrix[1]` and `matrix[2]` are aliases pointing to that exact same heap address!
> 4. As a result, `matrix` becomes:
>    `[[1, 0, 0], [1, 0, 0], [1, 0, 0]]`!
> 
> **The Idiomatic Solution**:
> To ensure that each row is an independently allocated object with its own distinct heap identity, you must evaluate the inner list creation expression fresh for each row using a nested list comprehension:
> `matrix = [[default_val for _ in range(cols)] for _ in range(rows)]`."

---

### § 3. Canonical Code Walkthrough
```python
R, C = 3, 3

# BROKEN -- one row object, replicated three times
grid = [[0] * C] * R
grid[0][0] = 1
# [[1, 0, 0],
#  [1, 0, 0],      <- all three rows changed
#  [1, 0, 0]]

# CORRECT -- the inner expression is re-evaluated once per row
grid = [[0] * C for _ in range(R)]
grid[0][0] = 1
# [[1, 0, 0],
#  [0, 0, 0],      <- independent rows
#  [0, 0, 0]]
```

Proving it with identities rather than eyeballing output:

```python
bad = [[0] * 3] * 3
id(bad[0]) == id(bad[1])      # True  -- ONE list, three references
bad[0] is bad[1]              # True

good = [[0] * 3 for _ in range(3)]
id(good[0]) == id(good[1])    # False -- three distinct lists
good[0] is good[1]            # False
```

**Why the inner `[0] * C` is still safe.** The multiplication operator replicates
*references*, not objects — in both cases. It is harmless for `[0] * C` because `0` is an
immutable `int`: assigning `row[i] = 5` rebinds that slot rather than mutating the shared
object. It is fatal for `[row] * R` because a list *is* mutable, so `grid[0][0] = 1` reaches
through every reference at once.

```
[[0] * C] * R                  [[0] * C for _ in range(R)]

grid[0] ─┐                     grid[0] ──> [0, 0, 0]
grid[1] ─┼──> [0, 0, 0]        grid[1] ──> [0, 0, 0]
grid[2] ─┘                     grid[2] ──> [0, 0, 0]
        ONE object                     THREE objects
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **The bug is silent.** No exception, no warning — just a DP table or visited grid whose
   rows are secretly the same object, producing answers that are wrong in ways that look
   like an algorithm error rather than an allocation error.
2. **`copy()` and `[:]` do not fix it.** Both are *shallow* copies: they build a new outer
   list holding the same inner objects. `copy.deepcopy(grid)` fixes it, or just build it
   correctly in the first place.
3. **It applies to any mutable element, not just lists.** `[set()] * n`, `[{}] * n` and
   `[[] for _ in range(n)]` vs `[[]] * n` are the same trap.
4. **`_` signals a deliberately unused loop variable.** `for _ in range(R)` says the index
   is irrelevant — only the repetition matters.
5. **Guttag's general rule covers this case.** Slicing and `L.copy()` "perform what is
   known as a shallow copy" — a new list holding *the objects*, not copies of them. The
   grid trap is that rule applied to a list of lists.

---

### § 5. Bridging to LeetCode Mastery
- **Grid DP & Graph Matrices**: In LeetCode 200 (*Number of Islands*), LeetCode 62 (*Unique Paths*), and LeetCode 733 (*Flood Fill*), allocating visited matrices or DP tables using `[[0]*C]*R` introduces silent, fatal cross-row corruption bugs.
""",
        "test_cases": [
            {"input": {"R": 2, "C": 3, "default_val": 7}, "expected": [[7, 7, 7], [7, 7, 7]]},
            {"input": {"R": 1, "C": 1, "default_val": 0}, "expected": [[0]]},
        ],
        "hints": ["Use [[default_val] * C for _ in range(R)]."],
    },

    {
        "slug": "py-fluency-mutable-default-arg",
        "title": "Mutable Default Argument Trap (Guttag Ch. 4)",
        "kind": "fundamental",
        "track": "track_1_pythonic_fluency",
        "difficulty": "Easy",
        "category": "Functional Abstractions",
        "tags": ["MIT 6.0001 Lec 4", "Guttag § 4.2", "Default Arguments", "Mutable Traps"],
        "description": """### Finger Exercise: Default Values Are Evaluated Once
**MIT 6.0001 Citation**: *Chapter 4: Functions, Scoping, and Abstraction (§ 4.1.2 Keyword Arguments and Default Values)*

A default value is evaluated **once, when the `def` statement executes** — not on each call.
A mutable default (`def f(acc=[])`) is therefore shared by every call and silently accumulates state between them.

Write `accumulate(item: int, bucket: list[int] | None = None) -> list[int]` that appends `item` to `bucket`
and returns it, using the `None` sentinel idiom so that **each call with no bucket starts empty**.
""",
        "examples": [
            {"input": "item = 1, bucket = None", "output": "[1]"},
            {"input": "item = 5, bucket = [9]", "output": "[9, 5]"},
        ],
        "constraints": ["bucket is either None or a list of ints"],
        "starter_codes": {
            "python": """def accumulate(item: int, bucket: list[int] | None = None) -> list[int]:
    # Use the None sentinel so each fresh call starts with its own list
    pass
"""
        },
        "solutions": {
            "python": """def accumulate(item: int, bucket: list[int] | None = None) -> list[int]:
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket
"""
        },
        "editorial": """# Chapter 4: Functions, Scoping, and Abstraction (§ 4.1.2 Keyword Arguments and Default Values)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: When Is a Default Evaluated?
A `def` statement is itself an executable statement. When Python executes it, it builds a function object and
evaluates every default-value expression **exactly once**, storing the resulting objects on the function object
(visible as `f.__defaults__`).

Every later call that omits the argument binds the parameter to that **same stored object**.

For an immutable default (`0`, `None`, `"x"`, `(1, 2)`) this is invisible: nothing can mutate it.
For a mutable default (`[]`, `{}`, `set()`) it is a shared, function-lifetime object — effectively hidden global state.

---

### § 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 4, § 4.1.2 — paraphrased summary of the argument, not a verbatim quotation)*

Guttag introduces default values so a caller can omit arguments that usually take an obvious value, and keyword
arguments so call sites read clearly regardless of parameter order. The subtlety the text stresses is that the
default belongs to the **function**, not to the call.

The failure mode:

```python
def add_to(item, target=[]):      # target is created ONCE
    target.append(item)
    return target

add_to(1)   # [1]
add_to(2)   # [1, 2]   <-- not [2]
add_to(3)   # [1, 2, 3]
```

The list is not recreated per call, so results leak across independent invocations.

**The sentinel idiom** is the standard repair — `None` is immutable, so it cannot accumulate anything:

```python
def add_to(item, target=None):
    if target is None:
        target = []               # fresh list per call
    target.append(item)
    return target
```

---

### § 3. Canonical Code Walkthrough
```python
def buggy(item, acc=[]):
    acc.append(item)
    return acc

def correct(item, acc=None):
    if acc is None:
        acc = []
    acc.append(item)
    return acc

assert buggy(1) == [1]
assert buggy(2) == [1, 2]        # leaked state from the previous call
assert buggy.__defaults__ == ([1, 2],)   # the default itself has been mutated

assert correct(1) == [1]
assert correct(2) == [2]         # independent
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **The memo-dict version is the same bug.** `def fib(n, memo={})` shares one cache across every top-level call.
   For pure functions that cache is a *feature*, which is why Guttag's `fastFib` uses it deliberately — but it is
   the identical mechanism, and it is a defect the moment the cached values depend on anything other than `n`.
2. **Class attributes repeat the trap.** A mutable value assigned in a class body is shared by every instance,
   for exactly the same reason.
3. **`is None`, not `or`.** Writing `acc = acc or []` also discards a legitimately empty list the caller passed in.

---

### § 5. Bridging to LeetCode Mastery
- **Repeated judge test cases**: a recursion whose result list defaults to `[]` carries answers from case 1 into
  case 2, producing a "works locally, fails on submit" bug that is very hard to see.
- **Backtracking signatures**: prefer `def dfs(i, path, out)` with explicit arguments, or the `None` sentinel —
  never a mutable default.
- **`@lru_cache` instead of `memo={}`**: gets the caching without the shared-default surface, and is cleared per run.
""",
        "test_cases": [
            {"input": {"item": 1, "bucket": None}, "expected": [1]},
            {"input": {"item": 5, "bucket": [9]}, "expected": [9, 5]},
            {"input": {"item": 7, "bucket": []}, "expected": [7]},
        ],
        "hints": [
            "Default the parameter to None, not to [].",
            "Inside the function: if bucket is None: bucket = []",
        ],
    },
    {
        "slug": "py-fluency-string-immutability",
        "title": "String Immutability & Concatenation Cost",
        "kind": "fundamental",
        "track": "track_1_pythonic_fluency",
        "difficulty": "Easy",
        "category": "Structured Types",
        "tags": ["MIT 6.0001 Lec 2", "Guttag § 2.3", "Strings", "Immutability", "Join Pattern"],
        "description": """### Finger Exercise: Building Strings Without Quadratic Cost
**MIT 6.0001 Citation**: *Chapter 2: Introduction to Python (§ 2.4 Strings and Input) & Chapter 5 (§ 5.3 Lists and Mutability)*

Strings are **immutable**. `s += c` cannot extend `s` in place — it allocates a new string and copies the whole
accumulated prefix, so building an $N$-character string one character at a time costs $O(N^2)$.

Write `build_reversed(words: list[str]) -> str` that joins `words` in reverse order separated by single spaces,
using `" ".join(...)` so the whole build is $O(N)$.
""",
        "examples": [
            {"input": "words = ['a', 'b', 'c']", "output": "'c b a'"},
            {"input": "words = ['hello']", "output": "'hello'"},
        ],
        "constraints": ["0 <= len(words) <= 10^4"],
        "starter_codes": {
            "python": """def build_reversed(words: list[str]) -> str:
    # Join the reversed list in one pass - do not use += in a loop
    pass
"""
        },
        "solutions": {
            "python": """def build_reversed(words: list[str]) -> str:
    return " ".join(reversed(words))
"""
        },
        "editorial": """# Chapter 2 (§ 2.4) & Chapter 5 (§ 5.3): Strings, Immutability, and the Cost of Concatenation
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Immutability Has a Running-Time Consequence
A Python `str` is an immutable sequence of Unicode code points. Every operation that "changes" a string in fact
returns a **new** string object; the original is untouched.

`s = s + c` therefore performs, on each execution:
1. allocate a new buffer of length `len(s) + len(c)`,
2. copy all `len(s)` existing characters into it,
3. copy `c`,
4. rebind the name `s` to the new object.

Step 2 is the problem. Doing this once per character of an $N$-character result copies
$$1 + 2 + 3 + \\dots + N = \\frac{N(N+1)}{2} = \\Theta(N^2)$$
characters in total — even though the answer has only $N$ characters in it.

`str.join` sums the lengths first, allocates the final buffer once, then copies each piece exactly once: $\\Theta(N)$.

---

### § 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 2 § 2.4 and Chapter 5 § 5.3 — paraphrased summary of the argument, not a verbatim quotation)*

Guttag introduces `str` alongside the other scalar-ish types and stresses that, like tuples, strings are immutable:
indexing and slicing read from a string, but no operation writes into one. Chapter 5 then draws the general
distinction the whole book leans on — mutable objects (`list`, `dict`, `set`) can be updated in place, immutable
objects (`int`, `float`, `str`, `tuple`) can only be replaced.

The practical consequence for strings is that "append" is not a real operation. What looks like appending is
rebuilding, and rebuilding inside a loop is where a linear-looking program becomes quadratic.

The idiomatic repair is to accumulate the pieces in a **mutable** list — where `append` genuinely is
amortized $O(1)$ — and collapse the list to a string once, at the end.

---

### § 3. Canonical Code Walkthrough
```python
# SLOW: Theta(N^2) - each += copies the entire accumulated prefix
out = ""
for ch in chars:
    out += ch

# FAST: Theta(N) - append to a list, join once
parts = []
for ch in chars:
    parts.append(ch)     # amortized O(1)
out = "".join(parts)     # one allocation, one pass

# Mutating a single character requires a round trip through a list
s = "cat"
lst = list(s)
lst[0] = "b"
s = "".join(lst)         # 'bat'
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **`s[0] = 'b'` raises `TypeError`.** Convert to a list, mutate, join back.
2. **Slicing copies.** `s[1:-1]` builds a new string of length $N-2$. A recursion that peels characters with
   `s[1:-1]` is $O(N^2)$ even though it looks like $O(N)$ — pass `left`/`right` indices instead.
3. **CPython sometimes hides the bug.** An in-place optimization can make `+=` look linear when the string has
   exactly one reference. Do not rely on it; it silently disappears the moment a second name refers to the string.

---

### § 5. Bridging to LeetCode Mastery
- **Building any string answer**: collect into a list, `"".join` once. This is the single most common hidden TLE
  in otherwise-correct string solutions.
- **LeetCode 5 (Longest Palindromic Substring)** and **LeetCode 647 (Palindromic Substrings)**: expand around a
  center with indices; never slice inside the loop.
- **LeetCode 271 (Encode and Decode Strings)** and **LeetCode 297 (Serialize/Deserialize Binary Tree)**: build the
  encoding as a list of tokens, join at the end.
""",
        "test_cases": [
            {"input": {"words": ["a", "b", "c"]}, "expected": "c b a"},
            {"input": {"words": ["hello"]}, "expected": "hello"},
            {"input": {"words": []}, "expected": ""},
            {"input": {"words": ["x", "y"]}, "expected": "y x"},
        ],
        "hints": [
            "reversed(words) gives the reverse order without copying via slicing.",
            "Return ' '.join(reversed(words)).",
        ],
    },

    # ── Track 2: Abstract Data Types & Object-Oriented Design (MIT 6.0001 Lec 8–9, Pset 5) ──
    {
        "slug": "py-ds-custom-intset-adt",
        "title": "Abstract Data Type & Invariant Encapsulation (Guttag Ch. 10)",
        "kind": "fundamental",
        "track": "track_2_data_structures",
        "difficulty": "Easy",
        "category": "Abstract Data Types",
        "tags": ["MIT 6.0001 Lec 8", "Guttag § 10.1", "OOP", "Classes", "Abstract Data Types"],
        "description": """### Finger Exercise: Implementing Guttag's IntSet ADT
**MIT 6.0001 Citation**: *Chapter 10: Classes and Object-Oriented Programming (§ 10.1 Abstract Data Types and Classes)*

In Figure 10-1, Guttag defines the canonical `Int_set` Abstract Data Type.
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
        "editorial": """# Chapter 10: Classes and Object-Oriented Programming (§ 10.1 Abstract Data Types)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Abstraction Barriers & Encapsulation
An **Abstract Data Type (ADT)** is a mathematical model for data types where a data type is defined by its behavior (semantics) from the point of view of a user of the data, specifically in terms of possible values, possible operations, and behavior of these operations.

The central pillar of software engineering in Guttag's paradigm is the **Data Abstraction Barrier**:
1. **Interface (Public API)**: The collection of methods callers invoke.
2. **Implementation (Internal Representation)**: The internal private structures and algorithms.
3. **Representation Invariant**: A formal predicate that must be true of every valid instance of the ADT before and after every public method call.

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 10, § 10.1 — paraphrased summary of the argument, not a verbatim quotation)*

Classes provide a mechanism for creating new abstract data types. Guttag's worked example is `Int_set`
(**Figure 10-1, "Class Int_set"**), a set-of-integers abstraction built on a plain list — an implementation he
himself calls unnecessary given Python's built-in `set`, but pedagogically useful.

The class docstring, he stresses, describes **the abstraction the class provides**, not how it is implemented;
the comments below the docstring carry the implementation notes, and those are aimed at people modifying or
subclassing the code, not at people using it.

```python
# After Guttag Figure 10-1, "Class Int_set" (structure, not a transcription)
class Int_set(object):
    \"\"\"An Int_set is a set of integers\"\"\"
    # Representation invariant: self._vals contains no duplicates.

    def __init__(self):
        \"\"\"Create an empty set of integers\"\"\"
        self._vals = []          # leading _ marks the attribute private to the class

    def insert(self, e):
        \"\"\"Assumes e is an integer and inserts e into self\"\"\"
        if e not in self._vals:  # appends only if absent -- ESTABLISHES the invariant
            self._vals.append(e)

    def member(self, e):
        \"\"\"Assumes e is an integer. Returns True if e is in self\"\"\"
        return e in self._vals

    def remove(self, e):
        \"\"\"Assumes e is an integer and removes e from self.
           Raises ValueError if e is not in self\"\"\"
        try:
            self._vals.remove(e)  # ONE call suffices -- EXPLOITS the invariant
        except ValueError:
            raise ValueError(str(e) + ' not found')

    def __str__(self):
        \"\"\"Returns a string representation of self\"\"\"
        if not self._vals:
            return '{}'
        return '{' + ','.join(str(e) for e in sorted(self._vals)) + '}'
```

**The invariant is the whole lesson.** Guttag states it exactly: *the representation invariant for `Int_set` is
that `vals` contains no duplicates.* From that single sentence, two responsibilities follow:

- **`__init__` establishes it.** The invariant holds trivially for the empty list.
- **Every other method maintains it.** `insert` appends `e` only if it is not already present — which is *why*
  the check is there, not an optimization.

And the invariant then pays for itself. `remove` may call `list.remove` exactly **once**, because the invariant
guarantees there is at most one occurrence of `e` to delete. An implementation that could not assume the
invariant would have to loop.

This is what data abstraction buys: **representation-independence**. A client writes `s.insert(3)` and
`s.member(3)`; it never learns whether `_vals` is a list, a sorted list, or something else entirely.

---

### § 3. Canonical Code Walkthrough: The Invariant Doing Work
Watch the invariant get established, maintained, and then exploited:

```python
s = Int_set()          # __init__ ESTABLISHES it: [] trivially has no duplicates
s.insert(3)            # _vals = [3]     guard passed, invariant maintained
s.insert(1)            # _vals = [3, 1]  invariant maintained
s.insert(3)            # _vals = [3, 1]  guard REJECTED it -- this is the maintenance
s.remove(3)            # ONE list.remove call is provably enough -- this is the payoff
```

The `insert` guard and the `remove` shortcut are the same fact seen from two sides:

```python
def insert(self, e):
    if e not in self._vals:      # PAYS to maintain the invariant
        self._vals.append(e)

def remove(self, e):
    try:
        self._vals.remove(e)     # SPENDS the invariant: at most one occurrence exists,
    except ValueError:           # so one call cannot leave a duplicate behind
        raise ValueError(str(e) + ' not found')
```

Without the invariant, `remove` would need a loop to strip every copy. The check in
`insert` is not defensive clutter — it is what buys the simplicity in `remove`.

**The abstraction barrier in one line.** Compare what a client may do with what an
implementer may do:

```python
# CLIENT side of the barrier -- uses only exported operations
s.insert(3); s.member(3); s.remove(3); print(s)

# IMPLEMENTER side -- may touch the representation
self._vals.append(e)

# VIOLATION -- reaching across the barrier
s._vals.append('banana')     # invariant destroyed; every later method now lies
```

The leading underscore is the convention Guttag uses to mark exactly this line.

---

### § 4. Common Pitfalls & Invariant Rules
1. **A getter that returns the internal list leaks the representation.** Returning
   `self._vals` hands the caller a live alias — `s.get_vals().append('banana')` silently
   breaks the invariant from outside. Return a copy (`self._vals[:]`) when you must expose it.
2. **The docstring describes the abstraction; comments describe the implementation.**
   Guttag is deliberate about this split: the docstring is for people *using* the class, the
   comments below it for people *modifying* it. Leaking representation detail into the
   docstring defeats the barrier.
3. **State the invariant as a comment, in words.** "`_vals` contains no duplicates" is what
   lets a future reader (you) know which shortcuts are legal.
4. **Every public method is a checkpoint.** The invariant must hold when a method returns,
   even if it is temporarily broken partway through.
5. **This `Int_set` is deliberately inefficient.** `member` is $O(n)$ because `_vals` is an
   unsorted list. Guttag says outright the class is "unnecessary and unnecessarily
   complicated" given Python's built-in `set` — it exists to teach the barrier, not to be used.

---

### § 5. Bridging to LeetCode Mastery
- **Design Problems**: In LeetCode 146 (*LRU Cache*), LeetCode 380 (*Insert Delete GetRandom O(1)*), and LeetCode 208 (*Implement Trie*), maintaining internal representation invariants across hash maps and doubly linked lists is the core testing metric.
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
        "tags": ["MIT 6.0001 Lec 10", "Guttag § 12.1", "Queues", "Deque", "FIFO", "O(1) Popping"],
        "description": """### Finger Exercise: FIFO Queue Mechanics
**MIT 6.0001 Citation**: *Chapter 11: Algorithmic Complexity (§ 11.3 Some Important Complexity Classes)*
> Note: **Beyond the book**: Guttag does not cover `collections.deque`. The O(N) vs O(1) argument below is his; the deque itself is a Python-fluency extension added for LeetCode work.

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
        "editorial": """# Chapter 11: Algorithmic Complexity (§ 11.3 Complexity Classes) — extended to FIFO Queues
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Dynamic Arrays vs Doubly-Linked Block Buffers
In computer architecture, data structures have distinct physical memory layouts:
1. **Dynamic Array (`list`)**: Allocates a contiguous block of memory words. Appending at the end is amortized $O(1)$. However, removing from index 0 (`pop(0)`) requires shifting all $N-1$ elements one word to the left in memory, taking strictly **$O(N)$ linear time**.
2. **Double-Ended Queue (`collections.deque`)**: Allocates a doubly linked list of fixed-size memory blocks (typically 64 elements per block). Appending and popping from either end (`append`, `appendleft`, `pop`, `popleft`) are guaranteed **strict $O(1)$ constant time operations**.

---

### § 2. Applying Guttag's Complexity Argument to Queues
*(Cost argument reconstructed from Guttag, Chapter 11, § 11.3. `collections.deque` itself is not covered in the text — this section extends his reasoning.)*

A **queue** is a First-In-First-Out (FIFO) data structure: elements are inserted at the back and removed from the front.

Guttag's § 11.3 point is that a per-operation cost you assume is $O(1)$ can silently dominate the total. That is exactly what happens here. If you implement Breadth-First Search using a Python `list` and call `list.pop(0)` on every node expansion, each pop shifts the remaining $N-1$ elements. An algorithm designed to run in $O(V + E)$ degrades to $O(V^2 + E)$, producing **Time Limit Exceeded (TLE)** on large inputs.

`collections.deque` stores elements as a doubly linked list of fixed-size blocks, so `popleft()` unlinks the head block entry without touching the rest — genuine $O(1)$, and the property BFS actually needs.

---

### § 3. Canonical Code Walkthrough
```python
from collections import deque

q = deque()
q.append(10)        # [10]          O(1)
q.append(20)        # [10, 20]      O(1)
q.popleft()         # -> 10,  [20]  O(1)   <- the operation a list gets wrong
q.append(30)        # [20, 30]      O(1)
list(q)             # [20, 30]
```

Why the same program on a `list` degrades. Removing index 0 must slide every remaining
element down one slot in the contiguous buffer:

```
list.pop(0) on [a, b, c, d, e]
     [a][b][c][d][e]
        \\  \\  \\  \\        every element shifts left  ->  O(N) per pop
     [b][c][d][e]

deque.popleft() on the same data
     unlink the head entry, move the head index  ->  O(1), nothing else touched
```

Full complexity comparison:

| Operation | `list` | `deque` |
| :-- | :-- | :-- |
| `append` / `push_back` | $O(1)$ amortized | $O(1)$ |
| `pop()` / from the right | $O(1)$ amortized | $O(1)$ |
| `pop(0)` / `popleft()` | **$O(N)$** | $O(1)$ |
| `insert(0, x)` / `appendleft(x)` | **$O(N)$** | $O(1)$ |
| `q[i]` random access | $O(1)$ | **$O(N)$** |

That last row is the trade: a deque gives up cheap indexing to get cheap ends. For BFS
you only ever touch the ends, so it is pure win.

The canonical BFS skeleton this exists to serve:

```python
from collections import deque

def bfs(start, neighbors):
    seen = {start}                     # mark on PUSH, not on pop
    q = deque([start])
    depth = 0
    while q:
        for _ in range(len(q)):        # snapshot the level size first
            node = q.popleft()
            for nxt in neighbors(node):
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        depth += 1
    return depth
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **`list.pop(0)` in a BFS is a silent $O(V^2)$.** The code looks correct and passes the
   small examples; it only fails on the large hidden cases, as a timeout rather than a wrong
   answer. This is the single most common cause of a "my BFS is right but TLEs" bug.
2. **Mark visited when you *enqueue*, not when you dequeue.** Marking on pop lets the same
   node be pushed several times before it is first processed, inflating the queue and, with
   weights, producing wrong answers.
3. **Snapshot `len(q)` before iterating a level.** Reading `len(q)` inside the loop sees the
   children you just appended and collapses the level boundaries.
4. **`deque[i]` is $O(N)$.** Never index into the middle of a deque inside a loop; if you
   need random access you wanted a list.
5. **`deque(maxlen=k)` silently discards from the far end** when it overflows — excellent for
   sliding windows, a data-loss bug anywhere else.

---

### § 5. Bridging to LeetCode Mastery
- **Breadth-First Search (BFS)**: In LeetCode 102 (*Binary Tree Level Order Traversal*), LeetCode 127 (*Word Ladder*), and LeetCode 994 (*Rotting Oranges*), using `queue = collections.deque([start])` and `node = queue.popleft()` is mandatory.
""",
        "test_cases": [
            {"input": {"ops": ["push", "push", "pop", "push"], "vals": [10, 20, 0, 30]}, "expected": [20, 30]},
            {"input": {"ops": ["push", "pop"], "vals": [5, 0]}, "expected": []},
        ],
        "hints": ["Use deque.append() and deque.popleft()."],
    },

    {
        "slug": "py-ds-hash-table-dict",
        "title": "Hash Tables & Dictionaries (Guttag Ch. 12)",
        "kind": "fundamental",
        "track": "track_2_data_structures",
        "difficulty": "Easy",
        "category": "Data Structures",
        "tags": ["MIT 6.0001 Lec 6", "MIT 6.0001 Pset 3", "Hash Tables", "Dictionaries"],
        "description": """### Finger Exercise: Trading Space for Constant-Time Lookup
**MIT 6.0001 Citation**: *Chapter 12: Some Simple Algorithms and Data Structures (§ 12.3 Hash Tables)*

A hash table converts a key into a bucket index with a hash function, giving **expected $O(1)$** insertion,
lookup, and deletion — the single most valuable data structure for interview problems.

Write `first_repeated(nums: list[int]) -> int` that returns the first value in `nums` that has already been
seen earlier in the list, or `-1` if every value is distinct. Use a `set` so the scan is one pass, $O(N)$.
""",
        "examples": [
            {"input": "nums = [2, 5, 3, 5, 2]", "output": "5"},
            {"input": "nums = [1, 2, 3]", "output": "-1"},
        ],
        "constraints": ["0 <= len(nums) <= 10^5"],
        "starter_codes": {
            "python": """def first_repeated(nums: list[int]) -> int:
    # One pass with a set of already-seen values
    pass
"""
        },
        "solutions": {
            "python": """def first_repeated(nums: list[int]) -> int:
    seen = set()
    for n in nums:
        if n in seen:
            return n
        seen.add(n)
    return -1
"""
        },
        "editorial": """# Chapter 12: Some Simple Algorithms and Data Structures (§ 12.3 Hash Tables)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Converting a Key Into an Address
Binary search (§ 12.1) buys $O(\\log N)$ lookup, but only after paying $O(N \\log N)$ to sort, and only for
keys that admit an ordering. A hash table asks a different question: instead of *comparing* the key against
other keys, can we **compute the key's storage location directly**?

A **hash function** maps a key to an integer bucket index:
$$\\text{bucket} = \\text{hash}(k) \\bmod m$$

Lookup then costs one hash evaluation plus one bucket probe — independent of how many keys are stored.

Two keys can hash to the same bucket. This is a **collision**, and it is unavoidable: there are more possible
keys than buckets (pigeonhole principle). The table resolves collisions by **chaining** — each bucket holds a
small list of the entries that landed there.

---

### § 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 12, § 12.3 — paraphrased summary of the argument, not a verbatim quotation)*

Guttag builds the argument in three steps, and implements it as class `Int_dict` in **Figure 12-7,
"Implementing dictionaries using hashing"** — a list of hash buckets, each bucket a list of `(key, value)`
tuples, so collisions are handled by storing every colliding entry in the same bucket list.

**Step 1 — the ideal.** If the hash function spread keys perfectly evenly across $m$ buckets holding $n$ entries,
every bucket would hold $n/m$ entries. Keeping $m$ proportional to $n$ makes that a constant, so lookup is $O(1)$.

**Step 2 — the honest caveat.** Guttag states it directly: with no collisions lookup would be constant time,
because each bucket holds 0 or 1 entries; but if everything hashed to the same bucket it would be *linear* in
the number of entries, since the code performs a linear search of that bucket. Making the table large enough
reduces collisions enough "to allow us to treat the complexity as constant time. That is, we can trade space
for time." The $O(1)$ claim is an expected cost bought with memory, not a guarantee.

**Step 3 — the requirement this imposes on keys.** A key must produce the *same* hash for its whole lifetime, or
it would go missing from the bucket it was filed under. That is why **only immutable objects are hashable** in
Python: `int`, `str`, `tuple`, `frozenset` may be keys; `list`, `dict`, `set` may not. The rule that ties the two
halves together is:
$$a == b \\implies \\text{hash}(a) == \\text{hash}(b)$$

This is the tradeoff Guttag names explicitly in § 12.3 — "we can trade space for time": spend $O(n)$ memory on the table,
buy $O(1)$ lookups.

---

### § 3. Canonical Code Walkthrough
```python
# The three operations that cover most interview uses
seen = set()                 # membership only
seen.add(5)
5 in seen                    # O(1) expected -- vs O(n) for `5 in some_list`

index_of = {}                # key -> value
index_of["a"] = 0

from collections import Counter, defaultdict
freq = Counter("mississippi")        # {'i': 4, 's': 4, 'p': 2, 'm': 1}
groups = defaultdict(list)           # no "if key not in d" branch needed
groups["vowel"].append("a")

# Hashability is enforced at runtime
d = {}
d[(1, 2)] = "ok"             # tuple: immutable, hashable
# d[[1, 2]] = "boom"         # TypeError: unhashable type: 'list'
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **`x in list` is $O(N)$; `x in set` is $O(1)$.** Swapping the container is often the entire optimization —
   this is what turns a quadratic scan into a linear one.
2. **A list cannot be a dict key.** Convert to a `tuple` (or a sorted string) first. This is exactly why
   *Group Anagrams* keys on `tuple(sorted(word))` rather than the character list.
3. **Sets are unordered.** Never rely on iteration order for output; sort explicitly when the judge expects a
   fixed sequence.
4. **Worst case is still $O(n)$.** If asked to justify "O(1) dictionary access", say *expected* — adversarial
   key sets can force collisions.

---

### § 5. Bridging to LeetCode Mastery
- **LeetCode 1 (Two Sum)**: store `value -> index` while scanning; look up the complement in $O(1)$. Turns the
  obvious $O(N^2)$ double loop into one pass.
- **LeetCode 49 (Group Anagrams)**: key a `defaultdict(list)` on the sorted-character tuple.
- **LeetCode 128 (Longest Consecutive Sequence)**: put everything in a set, then only start counting from values
  whose predecessor is absent — $O(N)$ without sorting.
- **LeetCode 560 (Subarray Sum Equals K)**: prefix sums plus a frequency dict, single pass.
- **LeetCode 217 (Contains Duplicate)** and **LeetCode 242 (Valid Anagram)**: the direct drills for this lesson.
""",
        "test_cases": [
            {"input": {"nums": [2, 5, 3, 5, 2]}, "expected": 5},
            {"input": {"nums": [1, 2, 3]}, "expected": -1},
            {"input": {"nums": []}, "expected": -1},
            {"input": {"nums": [7, 7]}, "expected": 7},
        ],
        "hints": [
            "Keep a set of values already seen.",
            "Return n the first time `n in seen` is True; return -1 after the loop.",
        ],
    },
    {
        "slug": "py-ds-magic-methods-ordering",
        "title": "Magic Methods & Custom Ordering (Guttag Ch. 10)",
        "kind": "fundamental",
        "track": "track_2_data_structures",
        "difficulty": "Medium",
        "category": "Abstract Data Types",
        "tags": ["MIT 6.0001 Lec 8", "Guttag § 10.1", "Dunder Methods", "Operator Overloading"],
        "description": """### Finger Exercise: Teaching Built-In Operators About Your Type
**MIT 6.0001 Citation**: *Chapter 10: Classes and Object-Oriented Programming (§ 10.1.1 Magic Methods and Hashable Types)*

Special ("dunder") methods let a user-defined class respond to built-in syntax: `__len__` for `len(x)`,
`__eq__` for `==`, `__lt__` for `<` — and therefore for `sorted()`, `min()`, `max()`, and `heapq`.

Write `rank_tasks(tasks: list[tuple[str, int]]) -> list[str]` where each task is `(name, priority)`.
Define a class `Task` with `__lt__` ordering by **descending priority**, ties broken by **ascending name**,
then return the task names in sorted order.
""",
        "examples": [
            {
                "input": "tasks = [('write', 2), ('alpha', 5), ('beta', 5)]",
                "output": "['alpha', 'beta', 'write']",
                "explanation": "priority 5 outranks 2; 'alpha' < 'beta' breaks the tie.",
            }
        ],
        "constraints": ["0 <= len(tasks) <= 1000"],
        "starter_codes": {
            "python": """def rank_tasks(tasks: list[tuple[str, int]]) -> list[str]:
    class Task:
        def __init__(self, name: str, priority: int):
            self.name = name
            self.priority = priority

        def __lt__(self, other) -> bool:
            # Higher priority first; ties broken by name ascending
            pass

    pass
"""
        },
        "solutions": {
            "python": """def rank_tasks(tasks: list[tuple[str, int]]) -> list[str]:
    class Task:
        def __init__(self, name: str, priority: int):
            self.name = name
            self.priority = priority

        def __lt__(self, other) -> bool:
            if self.priority != other.priority:
                return self.priority > other.priority
            return self.name < other.name

    objs = [Task(name, pri) for name, pri in tasks]
    return [t.name for t in sorted(objs)]
"""
        },
        "editorial": """# Chapter 10: Classes and Object-Oriented Programming (§ 10.1.1 Magic Methods and Hashable Types)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Operators Are Method Calls
Python's built-in syntax is a thin surface over method dispatch. When you write `a < b`, the interpreter calls
`a.__lt__(b)`. When you write `len(x)`, it calls `x.__len__()`. Nothing about `<` or `len` is reserved for
built-in types — a class that defines the corresponding method participates in that syntax on equal footing.

This is what makes an ADT (§ 10.1) feel like a native type instead of a bag of named methods. It is also
polymorphism in its most practical form: `sorted()` does not care what it is sorting, only that the elements
answer `__lt__`.

The methods that carry the most weight:

| Method | Powers |
| :-- | :-- |
| `__init__` | construction, establishing the representation invariant |
| `__repr__` / `__str__` | debugging output, `print` |
| `__eq__` | `==`, `in`, dict/set key matching |
| `__hash__` | usability as a dict key or set member |
| `__lt__` | `<`, `sorted()`, `min()`, `max()`, `heapq` |
| `__len__` | `len()`, and emptiness truthiness (`if obj:`) |
| `__getitem__` | `obj[i]`, and iteration as a fallback |

---

### § 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 10, § 10.1.1 and Figure 10-2 "Using magic methods" — paraphrase, not a verbatim quotation)*

Guttag's framing is that a class defines a new **type**, and a type is characterized by the operations it
supports. Special methods are how a new type acquires the operations users already know.

His running examples make two points that matter here.

**Point 1 — `__str__` is about the abstraction, not the representation.** Defining it means `print(obj)` shows
something meaningful to a client who has never seen the internal fields. Without it, the client gets an
address-like default that leaks nothing useful.

**Point 2 — comparison methods define an ordering, and the ordering must be consistent.** Once `__lt__` exists,
every ordering-based operation in the language routes through it. That is leverage, and also a hazard: an
inconsistent `__lt__` (one where `a < b` and `b < a` can both hold) produces sorts that are silently wrong
rather than errors.

The pairing rule the text is explicit about: **if you define `__eq__`, you must also define `__hash__`.**
Guttag notes that had his `Toy` class defined `__eq__` without `__hash__`, using instances as dictionary keys
would raise `unhashable type: 'Toy'`. He adds the requirement a custom `__hash__` must satisfy: the hash value
of an object must stay **constant throughout that object's lifetime**. Classes that never define `__eq__` keep
identity-based equality and stay hashable by default.

---

### § 3. Canonical Code Walkthrough
```python
import heapq

class Task:
    def __init__(self, name, priority):
        self.name = name
        self.priority = priority

    def __lt__(self, other):
        # Higher priority sorts first; ties broken alphabetically
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.name < other.name

    def __eq__(self, other):
        return (self.priority, self.name) == (other.priority, other.name)

    def __hash__(self):                     # required once __eq__ is defined
        return hash((self.priority, self.name))

    def __repr__(self):
        return f"Task({self.name!r}, {self.priority})"

ts = [Task("write", 2), Task("beta", 5), Task("alpha", 5)]

sorted(ts)          # [Task('alpha', 5), Task('beta', 5), Task('write', 2)]
min(ts)             # Task('alpha', 5)   -- uses __lt__

heapq.heapify(ts)   # works with no wrapper tuple, because __lt__ exists
heapq.heappop(ts)   # Task('alpha', 5)
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **`heapq` is a min-heap with no `key=` parameter.** Either define `__lt__` so "smallest" means what you want,
   or push `(-priority, name)` tuples. There is no third option.
2. **Defining `__eq__` silently removes hashability.** Add `__hash__` explicitly, and derive both from the *same*
   tuple of fields so they cannot disagree.
3. **A tuple key is usually simpler.** `sorted(tasks, key=lambda t: (-t[1], t[0]))` needs no class at all. Reach
   for `__lt__` when the same ordering is used in several places, or when the objects go into a heap.
4. **`__lt__` alone is enough for sorting.** Python's sort only ever calls `<`; you do not need the full set of
   comparison methods unless clients use them directly.

---

### § 5. Bridging to LeetCode Mastery
- **LeetCode 23 (Merge k Sorted Lists)**: `ListNode` has no ordering, so the standard fix is pushing
  `(node.val, tiebreak, node)` — or giving the wrapper a `__lt__`.
- **LeetCode 295 (Find Median from Data Stream)**: two heaps, the max-heap simulated by negation.
- **LeetCode 347 (Top K Frequent Elements)** and **LeetCode 973 (K Closest Points)**: ordering by a derived value
  is the whole problem.
- **Design rounds**: a class with `__repr__` and a coherent `__eq__`/`__hash__` pair is what "production quality"
  means when an interviewer says it.
""",
        "test_cases": [
            {
                "input": {"tasks": [["write", 2], ["alpha", 5], ["beta", 5]]},
                "expected": ["alpha", "beta", "write"],
            },
            {"input": {"tasks": []}, "expected": []},
            {"input": {"tasks": [["solo", 1]]}, "expected": ["solo"]},
        ],
        "hints": [
            "In __lt__, compare self.priority > other.priority when priorities differ.",
            "When priorities tie, return self.name < other.name.",
            "Build Task objects, call sorted(objs), then pull out .name.",
        ],
    },

    # ── Track 3: Inductive Recursion & Algorithmic Scaffolds (MIT 6.0001 Lec 6, Pset 3–4) ──
    {
        "slug": "py-scaffold-inductive-palindrome",
        "title": "Inductive Recursive Palindrome (Guttag Ch. 6)",
        "kind": "fundamental",
        "track": "track_3_algorithmic_scaffolds",
        "difficulty": "Easy",
        "category": "Inductive Recursion",
        "tags": ["MIT 6.0001 Lec 6", "Guttag § 6.1", "Recursion", "Induction", "Palindromes"],
        "description": """### Finger Exercise: Inductive Palindromic Recursion
**MIT 6.0001 Citation**: *Chapter 6: Recursion and Global Variables (§ 6.2 Palindromes)*

Implement Guttag's recursive palindrome checker from Figure 6-4.
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
        "editorial": """# Chapter 6: Recursion and Global Variables (§ 6.2 Inductive Palindromes)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Mathematical Induction in Computation
Recursion is an algorithmic paradigm in which a problem is solved by reducing it to smaller instances of the exact same problem.
Every well-founded recursive algorithm relies on the **Principle of Mathematical Induction**:
1. **Base Case (Basis Step)**: A direct, non-recursive solution for the smallest input instances.
2. **Inductive Step (Induction Hypothesis)**: Proof that if the algorithm correctly solves an input of size $k-1$, it correctly solves an input of size $k$.
3. **Progress Invariant**: Every recursive call must strictly move toward the base case, guaranteeing termination without infinite stack overflow.

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 6, § 6.2 — paraphrased summary of the argument, not a verbatim quotation)*

> "A palindrome is a string that reads the same forwards and backwards (e.g., 'radar', 'able was i ere i saw elba').
> 
> **Inductive Decomposition of Palindromes**:
> - **Base Case**: Any string of length 0 or 1 is trivially a palindrome.
> - **Inductive Hypothesis**: Suppose we can test whether any string of length $n-2$ is a palindrome.
> - **Inductive Step**: A string $s$ of length $n$ is a palindrome if and only if:
>   1. Its first and last characters are identical ($s[0] == s[-1]$), AND
>   2. The inner substring $s[1:-1]$ (which has length $n-2$) is a palindrome."

```python
# After Guttag Figure 6-4, "Palindrome testing"
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

---

### § 3. Canonical Code Walkthrough (after Guttag Figure 6-4, "Palindrome testing")
Guttag's version separates **normalizing** the input from **testing** it — two jobs, two
functions:

```python
def is_palindrome(s):
    # Assumes s is a str. Returns True if s is a palindrome; False otherwise.
    # Punctuation, blanks and capitalization are ignored.

    def to_chars(s):
        s = s.lower()
        letters = ''
        for c in s:
            if c in 'abcdefghijklmnopqrstuvwxyz':
                letters = letters + c
        return letters

    def is_pal(s):
        if len(s) <= 1:            # BASE CASE
            return True
        return s[0] == s[-1] and is_pal(s[1:-1])   # INDUCTIVE STEP

    return is_pal(to_chars(s))
```

Tracing `is_pal('radar')`:

```
is_pal('radar')   r == r  ->  and is_pal('ada')
  is_pal('ada')   a == a  ->  and is_pal('d')
    is_pal('d')   len <= 1 -> True          <- base case reached
```

Three frames, each shrinking the string by two characters. `and` short-circuits, so a
mismatch at any level returns `False` without descending further.

---

### § 4. Common Pitfalls & Invariant Rules
1. **Both base cases matter.** `len(s) <= 1` covers the empty string *and* the single
   character. Testing only `len(s) == 1` makes even-length inputs recurse past the bottom
   and raise `IndexError`.
2. **`s[1:-1]` is a copy, and that is the hidden cost.** Each level allocates a new string
   of length $n - 2$, so total work is $n + (n-2) + (n-4) + \\dots = \\Theta(n^2)$ — quadratic,
   despite only $n/2$ frames. The linear version passes indices instead:
   `is_pal(s, left + 1, right - 1)`.
3. **Recursion depth is $n/2$.** For $n = 10^5$ that exceeds CPython's default limit.
   The two-pointer loop is the production form.
4. **Normalize before testing, never during.** Folding the `to_chars` filter into `is_pal`
   makes the base case fire on stripped punctuation and quietly returns wrong answers.

---

### § 5. Bridging to LeetCode Mastery
- **Divide-and-Conquer Strings & Trees**: In LeetCode 131 (*Palindrome Partitioning*), LeetCode 9 (*Palindrome Number*), and LeetCode 100 (*Same Tree*), decomposing problems into `root.val == other.val and isSame(left) and isSame(right)` directly applies Guttag's inductive base case decomposition.
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
        "tags": ["MIT 6.0001 Lec 6", "Guttag § 14.1", "Recursion Trees", "Memoization", "Dynamic Programming"],
        "description": """### Finger Exercise: Memoized Fibonacci Tree
**MIT 6.0001 Citation**: *Chapter 15: Dynamic Programming (§ 15.1 Fibonacci Sequences, Revisited)*

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
        "editorial": """# Chapter 15: Dynamic Programming (§ 15.1 Fibonacci Sequences, Revisited)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: The Principle of Dynamic Programming
Dynamic Programming (DP) is an algorithmic paradigm devised by Richard Bellman in the 1950s.
It applies when a computational problem exhibits two key properties:
1. **Optimal Substructure**: An optimal solution to the problem contains within it optimal solutions to subproblems.
2. **Overlapping Subproblems**: The recursive search tree solves the **exact same subproblems over and over again**.

Without memoization, a recursive tree computing $Fib(n)$ has depth $n$ and branches into 2 calls at every level, creating $\\approx 2^n$ nodes $\\implies O(2^n)$ exponential blowup.
With **Memoization (Top-Down DP)**, we record the result of each subproblem in a lookup table (dictionary). When a subproblem is encountered again, we return the cached value in $O(1)$ time, reducing complexity to **$O(n)$ linear time**.

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 15, § 15.1 — paraphrased summary of the argument, not a verbatim quotation)*

> "Consider the classic recursive Fibonacci definition:
> ```python
> def fib(n):
>     if n == 0 or n == 1:
>         return 1
>     return fib(n - 1) + fib(n - 2)
> ```
> If you evaluate `fib(120)`, the function will perform roughly $2^{120} \\approx 1.3 \\times 10^{36}$ operations. Even on a supercomputer executing a trillion instructions per second, this would require $4 \\times 10^{16}$ years!
> 
> **Why is naive recursion so inefficient?**
> In computing `fib(6)`, `fib(4)` is computed twice, `fib(3)` is computed 3 times, and `fib(2)` is computed 5 times!
> 
> By maintaining a dictionary table `memo`, we check if `n in memo`. If present, we return `memo[n]` immediately. If absent, we compute it once, store it, and return it. The total number of subproblems is now exactly $n+1$, converting an impossible exponential execution into a fraction of a millisecond."

```python
# After Guttag Figure 15-2, "Implementing Fibonacci using a memo"
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

---

### § 3. Canonical Code Walkthrough (after Guttag Figure 15-2, "Implementing Fibonacci using a memo")
Guttag gives **both** dynamic-programming approaches in one figure, and names them:

```python
# MEMOIZATION - top-down. Start at the original problem, break it down,
# and record each answer in the table on the way back up.
def fib_memo(n, memo=None):
    # Assumes n is an int >= 0, memo used only by recursive calls.
    if memo is None:
        memo = {}
    if n == 0 or n == 1:
        return 1
    try:
        return memo[n]
    except KeyError:
        result = fib_memo(n - 1, memo) + fib_memo(n - 2, memo)
        memo[n] = result
        return result


# TABULAR - bottom-up. Start at the smallest subproblems and build upward.
# Works here because all the subproblems are known in advance and easy to
# enumerate in a useful order.
def fib_tab(n):
    tab = [1] * (n + 1)          # only first two entries are correct initially
    for i in range(2, n + 1):
        tab[i] = tab[i - 1] + tab[i - 2]
    return tab[n]
```

Guttag's own base case is `fib(0) == 1`; this drill uses the `{0: 0, 1: 1}` convention
instead, which is the one LeetCode expects. The *mechanism* is identical — only the
seed values differ.

---

### § 4. Common Pitfalls & Invariant Rules
1. **The naive cost is $O(fib(n))$, not $O(2^n)$.** Guttag is precise here: the growth is
   "proportional to the growth in the value of the result." The tree is lopsided — the
   `n-2` branch is shorter than the `n-1` branch — so the true base is the golden ratio
   $\\varphi \\approx 1.618$, not 2. $O(2^n)$ is a loose upper bound; $\\Theta(\\varphi^n)$ is tight.
2. **The scale is not rhetorical.** $fib(120) = 8{,}670{,}007{,}398{,}507{,}948{,}658{,}051{,}921$.
   At one nanosecond per recursive call, `fib(120)` would take roughly **250,000 years**.
   With a memo it is instant.
3. **`memo={}` as a default is the shared-mutable-default trap.** Guttag uses it
   deliberately — for a pure function the cache *should* persist. It becomes a defect the
   moment the cached values depend on anything besides `n`. The `None` sentinel is the
   safe default. See [Mutable Default Argument Trap](#).
4. **Memoize on the full state.** The key must capture everything the result depends on.
   `memo[n]` is right for Fibonacci; a two-argument recursion needs `memo[(i, j)]`.
5. **Top-down computes only what it reaches; bottom-up computes everything.** Prefer
   memoization when the reachable state space is sparse, tabulation when it is dense and
   you want to drop the recursion entirely.

---

### § 5. Bridging to LeetCode Mastery
- **1D Dynamic Programming**: In LeetCode 70 (*Climbing Stairs*), LeetCode 198 (*House Robber*), and LeetCode 322 (*Coin Change*), recognizing overlapping subproblems and memoizing states with `@functools.cache` or dictionary tables transforms brute-force backtracking into optimal linear solutions.
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
        "tags": ["MIT 6.0001 Lec 11", "Guttag § 12.2", "Binary Search", "Decrementing Function"],
        "description": """### Finger Exercise: Binary Search on Ordered Sequences
**MIT 6.0001 Citation**: *Chapter 12: Some Simple Algorithms and Data Structures (§ 12.1 Search Algorithms)*

Implement Guttag's binary search algorithm from Figure 12-3 on sorted array `nums`.
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
        "editorial": """# Chapter 12: Some Simple Algorithms and Data Structures (§ 12.1 Search Algorithms)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Binary Search & Lower Bounds
Searching for an element in an unsorted collection of size $N$ requires examining every item in the worst case $\\implies \\Omega(N)$ lower bound.
However, when a collection is **sorted in monotonic ascending order**, we can utilize the order invariant to achieve $\\mathcal{O}(\\log N)$ logarithmic search time.

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 12, § 12.1 — paraphrased summary of the argument, not a verbatim quotation)*

> "Binary search is one of the most fundamental search algorithms in computer science.
> 
> **The Search Invariant**:
> At any step, the target element $x$ is guaranteed to lie within the subsegment `L[left...right]`.
> 1. Pick the midpoint: `mid = (left + right) // 2`.
> 2. If `L[mid] == x`, return `mid`.
> 3. If `L[mid] < x`, then because `L` is sorted, all elements at indices $\\le mid$ are strictly less than $x$. Therefore, the target cannot lie in the lower half $\\implies set `left = mid + 1`.
> 4. If `L[mid] > x`, all elements at indices $\\ge mid$ are strictly greater than $x$. Therefore, the target cannot lie in the upper half $\\implies set `right = mid - 1`.
> 5. If `left > right`, the search interval is empty, confirming that $x \\notin L$."

---

### § 3. Canonical Code Walkthrough (after Guttag Figure 12-3, "Recursive binary search")
Guttag's implementation is split in two, and the split is the point of the example:

```python
# The WRAPPER: the interface clients actually call.
def search(L, e):
    # Assumes L is a list, sorted in ascending order.
    # Returns True if e is in L, False otherwise.
    def bin_search(L, e, low, high):
        # Decrementing function is high - low.
        if high == low:
            return L[low] == e
        mid = (low + high) // 2
        if L[mid] == e:
            return True
        elif L[mid] > e:
            if low == mid:        # nothing left to the left
                return False
            return bin_search(L, e, low, mid - 1)
        else:
            return bin_search(L, e, mid + 1, high)

    if len(L) == 0:
        return False
    return bin_search(L, e, 0, len(L) - 1)
```

Guttag calls `search` a **wrapper function**: it does no serious computation, it
just calls the helper with the right arguments. The reason it exists is an abstraction
argument — `low` and `high` "have nothing to do with the abstraction of searching a list
for an element. They are implementation details that should be hidden from those writing
programs that call `search`."

The iterative form in this drill collapses the same logic into one loop, trading the
recursion for an explicit `left`/`right` pair — no stack frames, same invariant.

---

### § 4. Why It Terminates, and Common Pitfalls
**The decrementing function.** Guttag proves termination the same way he does for
`while` loops: exhibit a quantity that maps the parameters to a non-negative integer,
halts the recursion at 0, and strictly shrinks on every call. For `bin_search` that
quantity is **`high - low`**:

1. It is at least 0 the first time it is called.
2. When it is exactly 0, no recursive call is made — the function just returns `L[low] == e`.
3. Each recursive call covers either the elements left of `mid` or those right of it,
   halving `high - low`.

Since `high - low` starts at `len(L) - 1` and can be halved at most $\\log_2(\\text{len}(L))$
times before reaching 0, the complexity is $\\Theta(\\log(\\text{len}(L)))$.

**Pitfalls:**
1. **The sorted precondition is the caller's job.** Guttag is explicit: if the assumption
   is not satisfied, "the implementation has no obligation to behave well. It could work,
   but it could also crash or return an incorrect answer." Should `search` verify it?
   No — checking would itself cost $O(\\text{len}(L))$ and destroy the whole point.
2. **`mid + 1` and `mid - 1`, never `mid`.** Recursing on `mid` itself does not shrink
   the decrementing function, so the recursion never terminates. *(Guttag leaves this as a
   finger exercise: "Why does the code use `mid+1` rather than `mid` in the second
   recursive call?")*
3. **Sorting first is not free.** Sorting to enable binary search costs
   $\\Theta(n \\log n)$. For a single lookup, a linear scan wins. It pays off across $k$
   searches: $\\Theta(n \\log n + k \\log n)$.
4. **A sorted linear scan is still $O(n)$.** Guttag's Figure 12-2 stops early once it
   passes the target — better average time, identical worst case.

---

### § 5. Bridging to LeetCode Mastery
- **LeetCode 704 (Binary Search)**, **LeetCode 33 (Search in Rotated Sorted Array)**, and **LeetCode 34 (Find First and Last Position)**: Mastering the `while left <= right:` template and strict boundary updates (`mid + 1`, `mid - 1`) prevents infinite loops and off-by-one errors.
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
        "tags": ["MIT 6.0002 / Lec 1", "Guttag § 14.2", "0/1 Knapsack", "Memoization"],
        "description": """### Finger Exercise: 0/1 Knapsack Binary Decision Tree
**MIT 6.0001 Citation**: *Chapter 14: Knapsack and Graph Optimization Problems (§ 14.1 Knapsack Problems) & Chapter 15 (§ 15.2)*

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
        "editorial": """# Chapter 14 & 15: Knapsack Problems & Dynamic Programming
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: State Space Trees & 0/1 Knapsack
In the **0/1 Knapsack Problem**, we are given a set of $n$ items, each with a weight $w_i$ and a value $v_i$, and a maximum knapsack capacity $W$.
We seek a subset of items that maximizes the total value subject to the constraint that the total weight $\\le W$.
Because each item must be taken in its entirety or left behind (no fractional items), greedy heuristics (such as sorting by value-to-weight ratio) fail to guarantee the optimal solution.

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 14 § 14.1 & Chapter 15 § 15.2 — paraphrased summary of the argument, not a verbatim quotation)*

> "We can conceptualize the search space as a **Binary Decision Tree** of depth $n$:
> - At depth 0, we decide whether to include item 0.
> - At depth 1, we decide whether to include item 1.
> - At depth $i$, the left branch corresponds to **taking item $i$**, and the right branch corresponds to **not taking item $i$**.
> 
> The brute-force decision tree has $2^n$ leaves.
> However, observe what defines the state of a subproblem at level $i$:
> The future optimal value depends solely on two integers: `(i, available_weight)`.
> 
> Even though there are $2^n$ possible subsets of items, the total number of distinct pairs `(i, avail)` cannot exceed:
> $$\\text{Number of States} \\le n \\times W$$
> By caching the result in `memo[(i, avail)]`, each distinct subproblem is solved exactly once.
> The time complexity drops from $O(2^n)$ down to **$O(n \\times W)$ pseudo-polynomial time**."

---

### § 3. Canonical Code Walkthrough (after Guttag Figure 15-5)
```python
# After Guttag Figure 15-5, "Using a decision tree to solve a knapsack problem"
def fastMaxVal(toConsider, avail, memo={}):
    if (len(toConsider), avail) in memo:
        result = memo[(len(toConsider), avail)]
    elif toConsider == [] or avail == 0:
        result = (0, ())
    elif toConsider[0].getWeight() > avail:
        result = fastMaxVal(toConsider[1:], avail, memo)
    else:
        nextItem = toConsider[0]
        # Explore Left Branch: Take item
        withVal, withToTake = fastMaxVal(toConsider[1:], avail - nextItem.getWeight(), memo)
        withVal += nextItem.getValue()
        # Explore Right Branch: Don't take item
        withoutVal, withoutToTake = fastMaxVal(toConsider[1:], avail, memo)
        # Choose maximum
        if withVal > withoutVal:
            result = (withVal, withToTake + (nextItem,))
        else:
            result = (withoutVal, withoutToTake)
    memo[(len(toConsider), avail)] = result
    return result
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **Greedy does not work here, and Guttag proves it.** He introduces knapsack precisely to
   show a greedy algorithm making "a sequence of local choices" that need not reach a global
   optimum. Sorting by value-to-weight ratio is optimal only when items can be split
   (the *fractional* knapsack). With all-or-nothing items, it fails.
2. **The state is `(index, capacity remaining)` — nothing else.** Two different item subsets
   reaching item `i` with the same remaining capacity have identical futures. That collapse
   is the entire optimization, taking $2^n$ leaves down to $n \\times W$ states.
3. **$O(n \\times W)$ is pseudo-polynomial, not polynomial.** $W$ is a *value*, and its
   encoding length is $\\log W$ bits, so the table is exponential in the input size. This is
   why knapsack DP is fast for `W = 1000` and hopeless for `W = 10^9`.
4. **Check `weights[i] <= avail` before taking.** Skipping the guard produces negative
   remaining capacity and a silently wrong memo entry keyed on an unreachable state.
5. **Both base cases are needed.** `i == n` (no items left) and `avail == 0` (no room left)
   each return 0; dropping either lets the recursion run off the end of the list.

---

### § 5. Bridging to LeetCode Mastery
- **2D Dynamic Programming**: LeetCode 416 (*Partition Equal Subset Sum*), LeetCode 494 (*Target Sum*), and LeetCode 474 (*Ones and Zeroes*) are direct variations of Guttag's 0/1 Knapsack Take/Don't-Take decision tree.
""",
        "test_cases": [
            {"input": {"weights": [1, 2, 3], "values": [6, 10, 12], "max_weight": 5}, "expected": 22},
            {"input": {"weights": [4, 5, 1], "values": [1, 2, 3], "max_weight": 3}, "expected": 3},
            {"input": {"weights": [10], "values": [100], "max_weight": 5}, "expected": 0},
        ],
        "hints": ["State is (i, avail). Base case: i == len(weights) or avail == 0 return 0. Explore take vs dont take."],
    },

    # ── Track 4: Divide-and-Conquer & Custom Sorting (MIT 6.0001 Lec 12) ──────────
    {
        "slug": "py-sort-merge-sort",
        "title": "Divide-and-Conquer Merge Sort (Guttag Ch. 12)",
        "kind": "fundamental",
        "track": "track_4_custom_sorting",
        "difficulty": "Easy",
        "category": "Divide-and-Conquer",
        "tags": ["MIT 6.0001 Lec 12", "Guttag § 12.3", "Merge Sort", "Divide-and-Conquer", "Stability"],
        "description": """### Finger Exercise: Implementing Merge Sort
**MIT 6.0001 Citation**: *Chapter 12: Some Simple Algorithms and Data Structures (§ 12.2 Sorting Algorithms)*

Implement Guttag's Merge Sort from Figure 12-5:
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
        "editorial": """# Chapter 12: Some Simple Algorithms and Data Structures (§ 12.2 Merge Sort)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Divide-and-Conquer Recurrence Relations
Merge Sort was invented in 1945 by John von Neumann. It is the prototypical **Divide-and-Conquer** algorithm:
1. **Divide**: Partition the problem of size $n$ into two subproblems of size $n/2$.
2. **Conquer**: Recursively solve each subproblem.
3. **Combine (Merge)**: Merge the two sorted sublists into a single sorted list in linear $O(n)$ time.

The running time recurrence relation is:
$$T(n) = 2 T(n/2) + O(n)$$
By the Master Theorem (Case 2), $T(n) = \\Theta(n \\log n)$ in the worst, average, and best cases.

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 12, § 12.2 — paraphrased summary of the argument, not a verbatim quotation)*

> "Why is merging two sorted lists so efficient?
> 
> Suppose we have two sorted lists `left` and `right` of lengths $n_1$ and $n_2$.
> To merge them, we look at the first element of each list. Whichever is smaller is appended to our output list and removed from its source list.
> Because every comparison guarantees that at least one element is placed into its final sorted position, merging takes at most $n_1 + n_2 - 1$ comparisons $\\implies O(n)$ linear time.
> 
> **The Recursion Tree Proof of $O(n \\log n)$**:
> - At depth 0, we merge 1 pair of lists of total size $n \\implies n$ work.
> - At depth 1, we merge 2 pairs of lists of size $n/2 \\implies 2 \\times (n/2) = n$ work.
> - At depth $k$, we merge $2^k$ pairs of lists of size $n/2^k \\implies 2^k \\times (n/2^k) = n$ work.
> 
> The tree depth is $\\log_2 n$.
> Multiplying the work per level ($n$) by the number of levels ($\\log_2 n$) gives the total asymptotic complexity: $\\mathcal{O}(n \\log n)$."

```python
# After Guttag Figure 12-5, "Merge sort"
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

---

### § 3. Tracing the Merge
The recursion is easy; the merge is where the linear-time claim is earned. Merging
`[1, 5, 9]` with `[2, 3, 8]`:

```
left  = [1, 5, 9]      right = [2, 3, 8]      out = []
 i=0, j=0   1 <= 2  -> take 1 from left       out = [1]
 i=1, j=0   5 >  2  -> take 2 from right      out = [1, 2]
 i=1, j=1   5 >  3  -> take 3 from right      out = [1, 2, 3]
 i=1, j=2   5 <= 8  -> take 5 from left       out = [1, 2, 3, 5]
 i=2, j=2   9 >  8  -> take 8 from right      out = [1, 2, 3, 5, 8]
 right exhausted -> extend with left[2:]      out = [1, 2, 3, 5, 8, 9]
```

Six elements, six placements, each decided by one comparison. Every comparison commits
at least one element to its final position permanently, which is why the merge cannot
exceed $n_1 + n_2$ steps.

**Why `<=` and not `<`.** When the two fronts are equal, taking from the **left** first
preserves the original relative order of equal elements. That single character is what
makes merge sort a **stable** sort. *(Guttag leaves exactly this as a finger exercise:
"Is `merge_sort` a stable sort?")*

---

### § 4. Common Pitfalls & Invariant Rules
1. **Base case must be `len < 2`, not `len == 1`.** An empty list has to terminate too, or
   an empty half sends the recursion into infinite descent.
2. **Return a copy at the base case.** Guttag's version returns `L[:]`. Returning `L`
   itself hands the caller an alias into the input, so a later in-place step corrupts data
   the caller still owns.
3. **The $O(n)$ auxiliary space is not optional.** Merge sort allocates a new list at every
   level. When a problem demands $O(1)$ extra space, merge sort is disqualified — reach for
   heapsort instead.
4. **Recursion depth is $\\log n$, not $n$.** Halving keeps the stack shallow; 10^6 elements
   is only ~20 frames deep. This is what makes it safe on inputs that would overflow a
   linear recursion.
5. **Slicing in the split costs real time.** `L[:middle]` copies. It does not change the
   asymptotic order but it doubles the constant factor; index-based merges avoid it.

---

### § 5. Bridging to LeetCode Mastery
- **Two-Pointer Merges & Linked Lists**: LeetCode 88 (*Merge Sorted Array*), LeetCode 21 (*Merge Two Sorted Lists*), and LeetCode 148 (*Sort List*) directly test this divide-and-conquer recurrence.
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
        "tags": ["MIT 6.0001 Lec 12", "Guttag § 12.3", "Multi-Key Sort", "Stable Sorting"],
        "description": """### Finger Exercise: Multi-Attribute Comparator Projections
**MIT 6.0001 Citation**: *Chapter 12: Sorting Algorithms (§ 12.2 Sorting with Custom Functions)*

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
        "editorial": """# Chapter 12: Sorting Algorithms (§ 12.2 Custom Multi-Key Comparators)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Lexicographic Tuple Ordering & Timsort
Python's built-in sorting algorithm, **Timsort** (devised by Tim Peters in 2002), is a hybrid stable sorting algorithm derived from Merge Sort and Insertion Sort with $O(n \\log n)$ worst-case and $O(n)$ best-case time complexity.

Timsort takes a `key` function parameter that projects each element to a comparable tuple.
When comparing two tuples `(a1, a2, a3)` and `(b1, b2, b3)`:
1. Python compares `a1` with `b1`. If `a1 != b1`, the ordering is decided.
2. If `a1 == b1`, it breaks the tie by comparing `a2` with `b2`.
3. If `a2 == b2`, it compares `a3` with `b3`.

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 12, § 12.2 — paraphrased summary of the argument, not a verbatim quotation)*

> "When sorting complex data objects (records, dictionaries, tuples), we rarely want to sort purely by identity.
> 
> By passing a lambda function that returns a tuple of projected keys:
> `sorted(students, key=lambda s: (-s.gpa, s.age, s.lastName))`
> we create a total ordering:
> - Negating numerical values (`-s.gpa`) inverts the comparison, giving descending order without requiring multiple passes.
> - Non-negated numerical and string fields resolve subsequent ties in natural ascending order."

---

### § 3. Canonical Code Walkthrough
```python
records = [('Alice', 90, 20), ('Bob', 90, 19), ('Charlie', 85, 22)]

# Score DESC, then age ASC, then name ASC.
# Negating the numeric field reverses that field only.
sorted(records, key=lambda r: (-r[1], r[2], r[0]))
# -> [('Bob', 90, 19), ('Alice', 90, 20), ('Charlie', 85, 22)]
```

How the tuple key decides the order:

```
Bob   -> (-90, 19, 'Bob')     first field ties with Alice (-90 == -90)
Alice -> (-90, 20, 'Alice')   second field breaks it: 19 < 20, so Bob wins
Charlie -> (-85, 22, ...)     -85 > -90, so Charlie sorts last
```

`sorted` and `list.sort` are not interchangeable — Guttag draws the distinction explicitly:

```python
L = [3, 5, 2]
sorted(L)        # -> [2, 3, 5]   returns a NEW list
L                # -> [3, 5, 2]   original untouched
L.sort()         # mutates in place, returns None
L                # -> [2, 3, 5]

D = {'a': 12, 'c': 5, 'b': 'dog'}
sorted(D)        # -> ['a', 'b', 'c']   sorting a dict sorts its KEYS
D.sort()         # AttributeError: 'dict' object has no attribute 'sort'
```

Both accept `key` and `reverse`. `key` plays the role that the `compare` parameter plays in
Guttag's hand-written merge sort — it supplies the comparison to be used:

```python
L = [[1, 2, 3], (3, 2, 1, 0), 'abc']
sorted(L, key=len, reverse=True)     # -> [(3, 2, 1, 0), [1, 2, 3], 'abc']
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **`reverse=True` reverses everything.** It flips *all* fields, including the tie-breakers
   you wanted ascending. Negate the individual numeric field instead.
2. **Negation only works on numbers.** There is no `-name`. To sort a string field
   descending while others ascend, exploit stability: sort by the string ascending first,
   then sort by the other key. Guttag guarantees this works — both `list.sort` and `sorted`
   "provide stable sorts", meaning elements that compare equal keep their relative order.
3. **`list.sort()` returns `None`.** `L = L.sort()` silently destroys the list. This is the
   mutator-returns-None convention shared with `append`, `reverse` and `extend`.
4. **Timsort's advantage is real data.** Guttag notes its worst case matches merge sort's,
   but "on average it performs considerably better" because it exploits the fact that many
   real data sets are already partially sorted.
5. **The key function is called once per element**, not once per comparison — so an
   expensive key is $O(n)$ evaluations, not $O(n \\log n)$.

---

### § 5. Bridging to LeetCode Mastery
- **Interval & Custom Object Sorting**: In LeetCode 435 (*Non-overlapping Intervals*) and LeetCode 179 (*Largest Number*), custom projection lambdas form the backbone of greedy intervals and custom ordering.
""",
        "test_cases": [
            {
                "input": {"records": [("Alice", 90, 20), ("Bob", 90, 19), ("Charlie", 85, 22)]},
                "expected": [["Bob", 90, 19], ["Alice", 90, 20], ["Charlie", 85, 22]],
            }
        ],
        "hints": ["Use sorted(records, key=lambda x: (-x[1], x[2], x[0]))."],
    },

    # ── Track 5: Bit Manipulation & Binary Encodings (MIT 6.0001 Numerics) ─────────
    {
        "slug": "py-bit-check-set-clear",
        "title": "Bitwise Check, Set, and Clear (Guttag Ch. 3)",
        "kind": "fundamental",
        "track": "track_5_bit_manipulation",
        "difficulty": "Easy",
        "category": "Bit Manipulation",
        "tags": ["MIT 6.0001 Numerics", "Guttag § 3.4", "Bitwise Operators", "Bit Manipulation"],
        "description": """### Finger Exercise: Bitmask Formulas
**Source**: *Beyond the textbook — extends Guttag Chapter 3 (§ 3.3 A Few Words about Using Floats)*
> Note: **Beyond the book**: Guttag § 3.3 covers binary representation only to explain float rounding error. Bitwise operators and bitmasks are **not** in the text; this drill adds them because LeetCode requires them.

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
        "editorial": """# Bitwise Logic — extending Guttag Chapter 3 (§ 3.3 A Few Words about Using Floats)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Binary Positional Encodings
In digital computing, all data is physically represented as strings of binary digits (bits: 0 and 1).
An unsigned integer $n$ is represented in base 2 as:
$$n = \\sum_{k=0}^{m-1} b_k \\cdot 2^k \\quad \\text{where } b_k \\in \\{0, 1\\}$$

Bitwise operations manipulate individual bit positions directly in the CPU's Arithmetic Logic Unit (ALU) in a single hardware clock cycle.

---

### § 2. In-Depth Textbook Reading & Passages
*(Not from Guttag. § 3.3 discusses binary representation only as the cause of float rounding error; bitwise operators are outside the book. The rules below are standard Python semantics.)*

> Python provides operators that operate on integers at the bit level:
> - `1 << i`: Left-shifts binary `1` by $i$ positions, generating a **bitmask** with a 1 at position $i$ and 0s elsewhere ($2^i$).
> - `(n >> i) & 1`: Right-shifts $n$ by $i$ places and tests bit 0 using bitwise AND. Returns 1 if set, 0 if clear.
> - `n | (1 << i)`: Bitwise OR combines bits. Any 1 in either operand becomes 1, setting the $i$-th bit.
> - `n & ~(1 << i)`: Bitwise NOT `~` inverts the mask (all 1s except at position $i$). Bitwise AND with this inverted mask clears bit $i$ while leaving all other bits unchanged."

---

### § 3. Canonical Code Walkthrough
Guttag does establish the foundation these operators act on. In § 3.3 he derives binary
positional notation directly: a binary number is a sequence of digits each 0 or 1, "often
called **bits**"; the rightmost is the $2^0$ place, the next the $2^1$ place, and so on, so
`101` represents $1 \\times 4 + 0 \\times 2 + 1 \\times 1 = 5$. A sequence of length $n$ can
represent $2^n$ different numbers. Computers use this representation, he notes, not out of
anatomy but because "it is easy to build hardware switches" that hold one of two states.

*(Finger exercise from the text: what is the decimal equivalent of the binary number `10011`?)*

The four primitive operations, traced on `n = 5` (binary `0101`) at bit `i = 1`:

```python
n = 5        # 0101
i = 1

# 1. BUILD THE MASK -- a 1 in position i, zeros everywhere else
mask = 1 << i               # 0010   (this is 2**i)

# 2. TEST bit i
(n >> i) & 1                # 0101 >> 1 = 0010, & 1 -> 0   (bit 1 is clear)
bool(n & mask)              # equivalent, without the shift

# 3. SET bit i  -- OR forces a 1, leaves every other bit alone
n | mask                    # 0101 | 0010 = 0111 -> 7

# 4. CLEAR bit i -- AND with the inverted mask
~mask                       # ...11111101
n & ~mask                   # 0101 & 1101 = 0101 -> 5   (already clear, unchanged)

# 5. TOGGLE bit i -- XOR flips exactly the masked position
n ^ mask                    # 0101 ^ 0010 = 0111 -> 7
```

Why each operator is the right one:

| Goal | Operator | Because |
| :-- | :-- | :-- |
| set | `|` | `x | 1 = 1`, `x | 0 = x` — forces on, leaves the rest |
| clear | `& ~` | `x & 0 = 0`, `x & 1 = x` — forces off, leaves the rest |
| toggle | `^` | `x ^ 1 = not x`, `x ^ 0 = x` — flips, leaves the rest |
| test | `& ` | isolates the bit, discarding everything else |

---

### § 4. Common Pitfalls & Invariant Rules
1. **Bitwise operators bind looser than comparison.** `n & 1 == 0` parses as
   `n & (1 == 0)` — always `0`. Write `(n & 1) == 0`. This is the single most common
   bit-manipulation bug in Python.
2. **`~n` is not "flip within 32 bits".** Python integers are unbounded, so `~5 == -6`,
   not `0xFFFFFFFA`. To simulate fixed-width behaviour, mask explicitly with
   `& 0xFFFFFFFF`.
3. **Shifting by a negative amount raises `ValueError`.** Guard `i >= 0`.
4. **`n >> i` on a negative `n` is an arithmetic shift.** The sign bit propagates, so the
   result stays negative forever. Mask to a fixed width first when treating a value as a
   bit pattern rather than a number.
5. **`1 << i` overflows nothing, but a wrong `i` silently gives a huge number.** `1 << 100`
   is a perfectly valid 101-bit integer in Python; there is no error to catch.

---

### § 5. Bridging to LeetCode Mastery
- **Bitmask DP & State Compression**: In LeetCode 78 (*Subsets*), LeetCode 136 (*Single Number*), and LeetCode 847 (*Shortest Path Visiting All Nodes*), sets of size $\\le 30$ are encoded as integer bitmasks where checking membership is `(mask >> i) & 1` and adding an element is `mask | (1 << i)`.
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
        "tags": ["MIT 6.0001 Numerics", "Brian Kernighan", "Set Bits", "Bitmasking"],
        "description": """### Finger Exercise: Brian Kernighan's Bit Invariant
**Source**: *Beyond the textbook — classical bit-manipulation result, not covered by Guttag*
> Note: **Beyond the book**: Brian Kernighan’s algorithm does not appear anywhere in Guttag. It is included because it is standard interview material.

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
        "editorial": """# Brian Kernighan’s Algorithm — beyond Guttag
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Two's Complement Subtraction Invariant
The standard method to count set bits tests each bit individually $\\implies 32$ iterations for a 32-bit integer.
**Brian Kernighan’s Algorithm** exploits an algebraic identity of binary subtraction:
When you subtract 1 from an integer $n$, the rightmost (lowest) 1-bit becomes 0, and all bits to the right of it (which were 0s) become 1s:
$$n = x100...00_2$$
$$n - 1 = x011...11_2$$
Performing a bitwise AND `n & (n - 1)` preserves the prefix $x$, clears the lowest 1-bit to 0, and zeroes out all trailing bits:
$$n \\& (n - 1) = x000...00_2$$

---

### § 2. In-Depth Textbook Reading & Passages
*(Not from Guttag — this result is not in the text. Stated here as standard bit-manipulation practice.)*

> Brian Kernighan’s algorithm clears the lowest set bit of $n$ in a single instruction.
> Repeating the loop `while n > 0: n &= (n - 1)` terminates in exactly $K$ iterations, where $K$ is the number of 1-bits (Hamming Weight).
> If $n$ has only two set bits out of 64, the loop runs only twice rather than 64 times."

---

### § 3. Canonical Code Walkthrough
```python
def count_set_bits(n):
    count = 0
    while n > 0:
        n &= (n - 1)      # clears exactly the lowest set bit
        count += 1
    return count
```

Tracing `n = 11` (binary `1011`, three set bits, therefore three iterations):

```
iter 1:  n     = 1011
         n - 1 = 1010          (lowest 1 flipped to 0, nothing below it)
         n & (n-1) = 1010      -> count = 1

iter 2:  n     = 1010
         n - 1 = 1001          (lowest 1 at position 1 -> 0, bit 0 -> 1)
         n & (n-1) = 1000      -> count = 2

iter 3:  n     = 1000
         n - 1 = 0111          (all lower bits flip on)
         n & (n-1) = 0000      -> count = 3, loop ends
```

Contrast with the naive scan, which always runs the full word width:

```python
def count_naive(n):
    count = 0
    while n:
        count += n & 1        # 32 iterations for a 32-bit int,
        n >>= 1               # regardless of how few bits are set
    return count
```

For `n = 2**31` (a single set bit), the naive version runs **32** iterations and
Kernighan's runs **1**.

---

### § 4. Common Pitfalls & Invariant Rules
1. **`n & (n - 1) == 0` tests a power of two — but guard `n > 0` first.** `n = 0` also
   satisfies the expression, and zero is not a power of two.
2. **Negative inputs never terminate under `while n > 0`.** Python's arbitrary-precision
   negatives have conceptually infinite leading 1s. Mask with `& 0xFFFFFFFF` before counting.
3. **The complexity is $O(K)$, not $O(1)$.** $K$ is the number of set bits — bounded by the
   word size, so it is $O(1)$ *for fixed-width* integers, but genuinely $O(\\log n)$ for
   Python's unbounded ones.
4. **`int.bit_count()` exists in Python 3.10+** and `bin(n).count('1')` works everywhere.
   Know the trick because it is asked; use the builtin when the interviewer allows it.
5. **Related identity: `n & -n` isolates the lowest set bit** (rather than clearing it),
   because `-n == ~n + 1` in two's complement. That is the indexing trick behind Fenwick trees.

---

### § 5. Bridging to LeetCode Mastery
- **LeetCode 191 (Number of 1 Bits)**, **LeetCode 231 (Power of Two)**: An integer $n > 0$ is a power of two if and only if `(n & (n - 1)) == 0`.
- **LeetCode 338 (Counting Bits)**: Dynamic programming state transition: `dp[i] = dp[i & (i - 1)] + 1`.
""",
        "test_cases": [
            {"input": {"n": 11}, "expected": 3},
            {"input": {"n": 0}, "expected": 0},
            {"input": {"n": 128}, "expected": 1},
        ],
        "hints": ["Initialize count = 0. While n > 0: n &= (n - 1); count += 1."],
    },

    # ── Track 6: Asymptotic Complexity & Efficiency (MIT 6.0001 Lec 10–11) ──
    {
        "slug": "py-math-asymptotic-complexity",
        "title": "Asymptotic Orders & Big-O Invariants (Guttag Ch. 11)",
        "kind": "fundamental",
        "track": "track_6_complexity_math",
        "difficulty": "Easy",
        "category": "Complexity Theory",
        "tags": ["MIT 6.0001 Lec 10", "Guttag § 11.1", "Big-O", "Complexity Classes"],
        "description": """### Finger Exercise: Asymptotic Growth Classification
**MIT 6.0001 Citation**: *Chapter 11: A Simplistic Introduction to Algorithmic Complexity (§ 11.2 Asymptotic Notation)*

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
        "editorial": """# Chapter 11: A Simplistic Introduction to Algorithmic Complexity (§ 11.2 Asymptotic Notation)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Formal Asymptotic Growth Analysis
When measuring algorithm efficiency, absolute execution time measured in seconds depends heavily on computer hardware, processor speed, operating system scheduling, and compiler optimizations.
Computer scientists analyze efficiency asymptotically as input size $n \\to \\infty$.

**Formal Definition of Big-O**:
We say that $f(n) \\in \\mathcal{O}(g(n))$ if there exist positive constants $c$ and $n_0$ such that:
$$f(n) \\le c \\cdot g(n) \\quad \\text{for all } n \\ge n_0$$
Big-O provides an asymptotic **upper bound** on the worst-case growth rate of the function.

---

### § 2. In-Depth Textbook Reading & Passages
*(Reconstructed from Guttag, Chapter 11, § 11.2 — paraphrased summary of the argument, not a verbatim quotation)*

> "The primary purpose of Big-O notation is to characterize the scalability of an algorithm.
> 
> #### The Hierarchy of Complexity Classes:
> 1. $\\mathcal{O}(1)$ (**Constant Time**): Running time does not depend on the input size $n$ (e.g., hash table key lookup, array index dereference).
> 2. $\\mathcal{O}(\\log n)$ (**Logarithmic Time**): Running time grows proportionally to the logarithm of input size. Usually associated with algorithms that cut the search space in half at each step (e.g., bisection search, binary search).
> 3. $\\mathcal{O}(n)$ (**Linear Time**): Running time grows linearly with input size (e.g., single-pass array traversal, counting elements).
> 4. $\\mathcal{O}(n \\log n)$ (**Log-Linear Time**): Divide-and-conquer algorithms that split the problem into subproblems of size $n/2$ and merge in $O(n)$ time (e.g., Merge Sort, Timsort).
> 5. $\\mathcal{O}(n^2)$ (**Quadratic Time**): Running time grows with the square of input size (e.g., nested loops, bubble sort).
> 6. $\\mathcal{O}(2^n)$ (**Exponential Time**): Running time doubles with each additional input element (e.g., exhaustive power set generation, recursive Fibonacci).
> 
> **The $10^8$ Operations Rule of Thumb**:
> Modern CPUs can execute approximately $10^8$ simple operations per second.
> - If $n = 10^5$, an $O(n^2)$ algorithm performs $10^{10}$ ops $\\implies$ **100 seconds $\\implies$ Time Limit Exceeded (TLE)**.
> - An $O(n \\log n)$ algorithm performs $10^5 \\times 17 \\approx 1.7 \\times 10^6$ ops $\\implies$ **0.02 seconds $\\implies$ Accepted**."

---

### § 3. Canonical Code Walkthrough: Reading Complexity Off the Code
Guttag's own § 11.3 examples, and how the shape of the code gives the class away:

```python
# THETA(1) -- constant. No dependence on input size at all.
def first(L):
    return L[0]

# THETA(log n) -- the search space is divided by a constant each step.
def bin_search(L, e, low, high):
    ...                       # halves high - low per call

# THETA(n) -- one bounded amount of work per element.
def total(L):
    s = 0
    for e in L:               # n iterations
        s += e                # O(1) body
    return s

# THETA(n log n) -- linear work repeated across log n levels.
def merge_sort(L):
    ...                       # log n levels, THETA(n) merging per level

# THETA(n^2) -- nested loops over the same collection.
def has_duplicate(L):
    for i in range(len(L)):       # n
        for j in range(len(L)):   # x n
            if i != j and L[i] == L[j]:
                return True
    return False

# THETA(2^n) -- one binary choice per element.
def power_set(L):                 # 2^n subsets to generate
    ...
```

**The multiplication rule.** Nested loops multiply; sequential blocks add, and the sum
collapses to its dominant term:

```python
for x in L:          # n
    ...
for y in L:          # + n        ->  2n  ->  THETA(n)
    ...

for x in L:          # n
    for y in L:      # * n        ->  n^2 ->  THETA(n^2)
        ...
```

**The trap: an $O(n)$ operation hidden inside an $O(n)$ loop.**

```python
out = []
for x in L:              # n iterations
    if x not in out:     # `in` on a LIST is O(n) -- so this is O(n^2) total
        out.append(x)

seen = set()
for x in L:              # n iterations
    if x not in seen:    # `in` on a SET is O(1) -- so this is O(n) total
        seen.add(x)
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **Complexity is about the input *size*, not the input *value*.** An algorithm looping
   `n` times where `n` is a supplied number is exponential in the input's encoding length —
   the pseudo-polynomial trap that makes knapsack's $O(nW)$ misleading.
2. **Drop constants and lower-order terms, but not before comparing correctly.**
   $3n^2 + 500n + 10^6$ is $\\Theta(n^2)$ — yet for $n < 100$ the constant dominates. Asymptotic
   analysis describes the limit, not small inputs.
3. **Say which case you mean.** Quicksort is $O(n \\log n)$ expected and $O(n^2)$ worst.
   Dictionary lookup is $O(1)$ expected and $O(n)$ worst. Stating only the good number is
   the most common complexity error in interviews.
4. **Count recursion frames in the space bound.** A recursive tree traversal is $O(H)$ space
   even with no explicit data structure allocated.
5. **The base of a logarithm never matters.** $\\log_2 n$ and $\\log_{10} n$ differ by a
   constant factor, so both are $O(\\log n)$.
6. **Amortized is not average.** `list.append` is $O(1)$ amortized — a guarantee about any
   sequence of operations, not a probabilistic claim about one call.

---

### § 5. Bridging to LeetCode Mastery
- Evaluating constraints during interviews:
  - $N \\le 20 \\implies \\mathcal{O}(2^N)$ or $\\mathcal{O}(N!)$ (Backtracking, Bitmask DP).
  - $N \\le 10^3 \\implies \\mathcal{O}(N^2)$ (2D DP, Nested loops).
  - $N \\le 10^5 \\implies \\mathcal{O}(N \\log N)$ or $\\mathcal{O}(N)$ (Sorting, Binary Search, Two Pointers, Monotonic Stack).
  - $N \\le 10^9 \\implies \\mathcal{O}(\\log N)$ or $\\mathcal{O}(1)$ (Math, Binary Search on Answer).
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
        "tags": ["MIT 6.0001 Lec 10", "Prefix Sums", "Range Queries", "O(1) Lookup"],
        "description": """### Finger Exercise: Prefix Sum Array & Range Query Invariant
**Source**: *Beyond the textbook — applies the space-for-time tradeoff Guttag draws in Chapter 12 (§ 12.3 Hash Tables)*
> Note: **Beyond the book**: prefix sums are not in Guttag. The trade-space-for-time principle they rest on is his (§ 12.3, on sizing a hash table); the technique itself is added for LeetCode.

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
        "editorial": """# Prefix Sums — applying Guttag’s space-for-time tradeoff (§ 12.3)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: The Space-Time Tradeoff Principle
A central theme in computational efficiency is trading space for time: spending memory to store precomputed intermediate calculations so future queries can be answered in constant $\\mathcal{O}(1)$ time.

---

### § 2. In-Depth Textbook Reading & Passages
*(Not from Guttag. The framing follows his space-for-time argument in § 12.3; the prefix-sum technique is not in the text.)*

> Suppose you are given an array $A$ of $N$ numbers and must answer $Q$ range sum queries: 'What is the sum of elements from index $L$ to $R$ inclusive?'
> 
> A naive loop summing $A[L...R]$ takes $\\mathcal{O}(R - L + 1) = \\mathcal{O}(N)$ time per query $\\implies \\mathcal{O}(Q \\times N)$ total time. For $Q = 10^5$ and $N = 10^5$, this requires $10^{10}$ operations (TLE).
> 
> **The Prefix Sum Array**:
> We precompute an auxiliary array $P$ of length $N+1$ where:
> - $P[0] = 0$
> - $P[i] = P[i-1] + A[i-1] = \\sum_{k=0}^{i-1} A[k]$
> 
> The sum of elements from index $L$ to $R$ is derived via the fundamental identity:
> $$\\sum_{k=L}^{R} A[k] = \\left(\\sum_{k=0}^{R} A[k]\\right) - \\left(\\sum_{k=0}^{L-1} A[k]\\right) = P[R + 1] - P[L]$$
> Precomputation takes $\\mathcal{O}(N)$ time and $\\mathcal{O}(N)$ auxiliary memory. Each subsequent range query takes **guaranteed $\\mathcal{O}(1)$ constant time**."

---

### § 3. Canonical Code Walkthrough
```python
def build_prefix_sum(nums):
    prefix = [0] * (len(nums) + 1)        # note: length n + 1
    for i, num in enumerate(nums):
        prefix[i + 1] = prefix[i] + num
    return prefix
```

Building it for `nums = [1, 2, 3, 4]`:

```
prefix[0] = 0                    <- the empty prefix; this entry is why the array is n+1 long
prefix[1] = prefix[0] + 1 = 1    <- sum of nums[0:1]
prefix[2] = prefix[1] + 2 = 3    <- sum of nums[0:2]
prefix[3] = prefix[2] + 3 = 6    <- sum of nums[0:3]
prefix[4] = prefix[3] + 4 = 10   <- sum of nums[0:4]

prefix = [0, 1, 3, 6, 10]
```

Answering queries in $O(1)$ each, by subtraction:

```python
# sum of nums[L..R] inclusive  ==  prefix[R + 1] - prefix[L]
sum(1..2) = prefix[3] - prefix[1] = 6 - 1 = 5      # nums[1] + nums[2] = 2 + 3
sum(0..3) = prefix[4] - prefix[0] = 10 - 0 = 10    # the whole array
sum(2..2) = prefix[3] - prefix[2] = 6 - 3 = 3      # a single element
```

The cost profile: $\\Theta(n)$ once to build, $\\Theta(1)$ per query, $\\Theta(n)$ extra memory.
Across $Q$ queries that is $\\Theta(n + Q)$ instead of the naive $\\Theta(n \\times Q)$.

---

### § 4. Common Pitfalls & Invariant Rules
1. **The array must have length $n + 1$.** The leading `0` represents the empty prefix and
   is what makes `L = 0` work without a special case. Building an $n$-length array forces an
   `if L == 0` branch into every query.
2. **`prefix[R + 1]`, not `prefix[R]`.** The off-by-one here is the whole technique.
   Write the invariant down: *`prefix[i]` is the sum of the first `i` elements* — then
   `sum(L..R)` is "first `R+1`" minus "first `L`".
3. **It only works on an immutable array.** A single update to `nums[i]` invalidates every
   `prefix[j]` for `j > i`, costing $O(n)$ to repair. If updates interleave with queries,
   you need a Fenwick tree or segment tree instead.
4. **The same trick generalizes.** Prefix XOR, prefix product, prefix counts and 2-D prefix
   sums all work by the same subtraction identity — any associative operation with an
   inverse.
5. **Pair it with a hash map for subarray-target problems.** Counting subarrays summing to
   `k` is not a range query: store the *frequency* of each prefix value seen so far and look
   up `prefix - k` in $O(1)$.

---

### § 5. Bridging to LeetCode Mastery
- **LeetCode 303 (Range Sum Query - Immutable)**: Direct implementation of prefix sum array.
- **LeetCode 560 (Subarray Sum Equals K)**: Combines prefix sums with hash map frequency counts to find subarrays summing to $k$ in single-pass $\\mathcal{O}(N)$ time.
""",
        "test_cases": [
            {"input": {"nums": [1, 2, 3, 4]}, "expected": [0, 1, 3, 6, 10]},
            {"input": {"nums": []}, "expected": [0]},
            {"input": {"nums": [5]}, "expected": [0, 5]},
        ],
        "hints": ["Initialize prefix = [0] * (len(nums) + 1), then prefix[i+1] = prefix[i] + num."],
    },

    # ── Track 7: Testing, Debugging & Exceptions (MIT 6.0001 Lec 7) ───────────
    {
        "slug": "py-verify-black-glass-box-testing",
        "title": "Black-Box & Glass-Box Testing (Guttag Ch. 8)",
        "kind": "fundamental",
        "track": "track_7_testing_exceptions",
        "difficulty": "Easy",
        "category": "Testing & Debugging",
        "tags": ["MIT 6.0001 Lec 7", "Guttag § 8.1", "Black-Box Testing", "Glass-Box Testing"],
        "description": """### Finger Exercise: Deriving Test Cases From a Specification
**MIT 6.0001 Citation**: *Chapter 8: Testing and Debugging (§ 8.1 Testing)*

Guttag's partition of test design:
- **Black-box tests** come from the *specification* — they survive a rewrite of the implementation.
- **Glass-box tests** come from the *code* — they aim to exercise every path through it.

Boundary conditions are where defects concentrate. Write `boundary_cases(n: int) -> list[int]` that returns the
canonical boundary probes for a size-`n` input, in this order and with no duplicates:
`0`, `1`, `n - 1`, `n`, `n + 1` — keeping only the non-negative values.
""",
        "examples": [
            {"input": "n = 5", "output": "[0, 1, 4, 5, 6]"},
            {"input": "n = 1", "output": "[0, 1, 2]", "explanation": "n-1 == 0 and n == 1 already appear; duplicates dropped."},
        ],
        "constraints": ["0 <= n <= 10^6"],
        "starter_codes": {
            "python": """def boundary_cases(n: int) -> list[int]:
    # Return [0, 1, n-1, n, n+1] with negatives removed and duplicates dropped,
    # preserving first-seen order.
    pass
"""
        },
        "solutions": {
            "python": """def boundary_cases(n: int) -> list[int]:
    candidates = [0, 1, n - 1, n, n + 1]
    out = []
    for c in candidates:
        if c >= 0 and c not in out:
            out.append(c)
    return out
"""
        },
        "editorial": """# Chapter 8: Testing and Debugging (§ 8.1 Testing)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: What Testing Can and Cannot Establish
Testing runs a program on sample inputs and compares actual behavior against the specification. Its logical
limit is worth stating exactly, because it governs how you should use it:

> Testing can demonstrate the **presence** of defects. It cannot demonstrate their **absence**.

For any interesting program the input space is far too large to enumerate — a function taking one 32-bit integer
already has $2^{32}$ possible inputs. So testing is a **sampling** problem: you cannot try everything, therefore
you must choose the sample that maximizes the chance of exposing a defect.

Guttag's answer is to partition the input space into groups whose members should all behave the same way, and
test one representative from each group, plus the values at the boundaries between groups.

---

### § 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 8, § 8.1.1–8.1.2 and Figure 8-1 "Testing boundary conditions" — paraphrase, not a verbatim quotation)*

**Black-box testing** derives tests from the specification alone, without reading the implementation. Two
properties make this valuable: the tests can be written before the code exists, and they remain valid when the
implementation is replaced. A black-box suite for `sqrt(x, epsilon)` would probe the boundary of the documented
domain, typical values, and the extremes the spec admits.

**Glass-box testing** derives tests from the code, aiming for **path completeness** — every potential path
through the program is exercised at least once. The text is careful about the limit here: loops make genuine
path completeness unattainable, because a loop that can run any number of times has unboundedly many paths. The
practical rule Guttag gives is to exercise each loop **zero times, once, and more than once**, which catches the
overwhelming majority of loop defects.

The two techniques are complements, not alternatives, and the reason is sharp: **a glass-box suite cannot find a
path that was never written.** If the code forgot to handle the empty input, no amount of covering the code that
*is* there will reveal the omission. Only a test derived from the specification will.

Where defects cluster: boundary conditions. Empty input, a single element, the first and last index, the maximum
permitted size, all-equal values, negatives, zero.

---

### § 3. Canonical Code Walkthrough
```python
def find_max(L):
    \"\"\"Assumes L is a non-empty list of numbers.
       Returns the largest element of L.\"\"\"
    best = L[0]
    for e in L[1:]:
        if e > best:
            best = e
    return best

# BLACK-BOX: derived from the docstring, not the body
assert find_max([3]) == 3                 # single element
assert find_max([1, 2, 3]) == 3           # max at the end
assert find_max([3, 2, 1]) == 3           # max at the start
assert find_max([-5, -2, -9]) == -2       # all negative
assert find_max([4, 4, 4]) == 4           # all equal

# GLASS-BOX: derived from the body -- exercise the loop 0, 1, and many times
assert find_max([7]) == 7                 # loop body runs 0 times
assert find_max([7, 8]) == 8              # loop body runs 1 time, branch taken
assert find_max([8, 7]) == 8              # loop body runs 1 time, branch NOT taken

# The bug black-box testing finds and glass-box testing cannot:
# find_max([]) raises IndexError. There is no code path for the empty list,
# so no amount of covering the existing code reveals the missing case.
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **Coverage is not correctness.** 100% line coverage says every line ran, not that any line was right.
2. **A glass-box suite is blind to omissions.** Missing functionality has no code to cover. Always derive some
   tests from the spec.
3. **Test the boundary, not near it.** If the spec says `n <= 100`, test `100` and `101`, not `50` and `150`.
4. **Re-run everything after a fix.** Repairs introduce new defects; that is what regression testing is for.

---

### § 5. Bridging to LeetCode Mastery
- **The constraints block is your black-box spec.** `1 <= n <= 10^5` names the boundaries to probe before
  submitting: `n = 1` and `n = 10^5`.
- **The four cases judges always include**: empty input, one element, all elements equal, maximum size.
- **Trace by hand before submitting.** A two-minute walk of `n = 0` and `n = 1` catches most off-by-one defects,
  and it is far cheaper than a Wrong Answer on a hidden case you cannot see.
""",
        "test_cases": [
            {"input": {"n": 5}, "expected": [0, 1, 4, 5, 6]},
            {"input": {"n": 1}, "expected": [0, 1, 2]},
            {"input": {"n": 0}, "expected": [0, 1]},
            {"input": {"n": 2}, "expected": [0, 1, 2, 3]},
        ],
        "hints": [
            "Start from the candidate list [0, 1, n-1, n, n+1].",
            "Skip any candidate that is negative or already present, preserving first-seen order.",
        ],
    },
    {
        "slug": "py-verify-exceptions-assertions",
        "title": "Exceptions & Assertions (Guttag Ch. 9)",
        "kind": "fundamental",
        "track": "track_7_testing_exceptions",
        "difficulty": "Easy",
        "category": "Testing & Debugging",
        "tags": ["MIT 6.0001 Lec 7", "Guttag § 9.1", "Exceptions", "Assertions", "Defensive Programming"],
        "description": """### Finger Exercise: Failing Loudly at the Point of Violation
**MIT 6.0001 Citation**: *Chapter 9: Exceptions and Assertions (§ 9.1 Handling Exceptions, § 9.3 Assertions)*

An unhandled exception halts the program with a traceback. A handled one lets the caller recover.
An **assertion** checks that an assumption actually holds, so a violated precondition is caught where it
happens rather than producing a corrupted answer somewhere downstream.

Write `safe_divide(pairs: list[tuple[int, int]]) -> list[float | None]` that returns `a / b` for each
`(a, b)` pair, substituting `None` wherever `b == 0` — catching `ZeroDivisionError` rather than pre-checking.
""",
        "examples": [
            {"input": "pairs = [(6, 2), (1, 0), (9, 3)]", "output": "[3.0, None, 3.0]"},
        ],
        "constraints": ["0 <= len(pairs) <= 1000"],
        "starter_codes": {
            "python": """def safe_divide(pairs: list[tuple[int, int]]) -> list:
    # Use try/except ZeroDivisionError, appending None on failure
    pass
"""
        },
        "solutions": {
            "python": """def safe_divide(pairs: list[tuple[int, int]]) -> list:
    out = []
    for a, b in pairs:
        try:
            out.append(a / b)
        except ZeroDivisionError:
            out.append(None)
    return out
"""
        },
        "editorial": """# Chapter 9: Exceptions and Assertions (§ 9.1 Handling Exceptions, § 9.3 Assertions)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Two Failure Channels
A function that cannot fulfil its specification has to communicate that somehow. There are two mechanisms, and
choosing between them is a design decision:

1. **Return a special value** (`-1`, `None`, `()`). Cheap, but the caller can silently ignore it, and the special
   value may collide with a legitimate answer. `find(x)` returning `-1` breaks the moment `-1` is a valid index.
2. **Raise an exception.** Cannot be ignored — control transfers immediately, and an unhandled exception halts
   the program with a traceback pointing at the failure.

Guttag's preference is unambiguous: **raise**. An error that stops the program is strictly better than an error
that quietly poisons a result.

---

### § 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 9, § 9.1–9.3 and Figure 9-1 "Using exceptions for control flow" — paraphrase, not a verbatim quotation)*

**Handling exceptions (§ 9.1).** A `try` block guards code that might fail; an `except` clause names the
exceptions it is prepared to handle and supplies the recovery. Naming the type matters — a bare `except:` catches
everything, including the programmer errors you wanted to see, which converts a loud defect into a silent one.

Guttag devotes a whole section (§ 9.2, "Exceptions as a Control Flow Mechanism", with Figure 9-1) to the point
that exceptions are not reserved for catastrophes. They are a reasonable control-flow mechanism for conditions
that are exceptional but expected — attempting the operation and handling the failure is often cleaner than
testing every precondition first, and it avoids the gap between the check and the use.

**Assertions (§ 9.3).** An assertion is a different tool with a different audience. Exceptions handle conditions
the program should survive; assertions state conditions that must be true if the code is correct at all.

The argument for them is about *where* a defect surfaces. Without a check, a violated assumption propagates —
the program keeps computing on bad state and fails much later, somewhere that has nothing to do with the cause.
That distance is what makes debugging expensive. An assertion collapses it to zero by failing at the point of
violation.

Guttag's idiom is to assert the **preconditions** of a function on entry, and its **representation invariant**
after any operation that could disturb it — the same invariant discipline the `IntSet` ADT in Chapter 10 relies on.

---

### § 3. Canonical Code Walkthrough
```python
# 1. Handling an expected failure
def get_ratio(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return None            # documented, checkable outcome

# 2. Exceptions as ordinary control flow -- no check-then-act gap
def lookup(d, k):
    try:
        return d[k]
    except KeyError:
        return 0
    # equivalently, and more idiomatically: return d.get(k, 0)

# 3. Raising, because the caller violated the contract
def average(scores):
    \"\"\"Assumes scores is a non-empty list of numbers.\"\"\"
    if not scores:
        raise ValueError("average requires a non-empty list")
    return sum(scores) / len(scores)

# 4. Asserting an invariant -- fails at the cause, not downstream
def binary_search(L, x):
    lo, hi = 0, len(L) - 1
    while lo <= hi:
        assert 0 <= lo and hi < len(L), "search window escaped the list"
        mid = (lo + hi) // 2
        if L[mid] == x:
            return mid
        if L[mid] < x:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **Never write a bare `except:`.** It swallows real defects — including `KeyboardInterrupt`. Name the type.
2. **Assertions are not input validation.** They are disabled under `python -O`, so never rely on one to check
   untrusted data. Assert what *your* code guarantees; `raise` for what a *caller* got wrong.
3. **`try` costs nothing when nothing is raised.** The overhead is in raising, not in guarding, so EAFP is not
   a performance compromise.
4. **Catch narrowly, at the level that can recover.** A handler that cannot actually fix anything should let the
   exception through.

---

### § 5. Bridging to LeetCode Mastery
- **Runtime Error verdicts are uncaught exceptions.** `IndexError` means a bounds check is missing;
  `KeyError` means a `.get(k, default)` or `defaultdict` is missing; `RecursionError` means the base case is
  unreachable or the input is deeper than the default ~1000-frame stack.
- **EAFP shortens real solutions.** `Counter`, `defaultdict`, and `d.get(k, 0)` all remove the
  "if key not in d" branch that clutters frequency-counting code.
- **A temporary `assert` localizes a binary-search bug in one run** — far faster than re-reading the loop.
- **Design rounds care about the contract.** Say what your method does on invalid input, and pick raise-vs-sentinel
  deliberately rather than by accident.
""",
        "test_cases": [
            {"input": {"pairs": [[6, 2], [1, 0], [9, 3]]}, "expected": [3.0, None, 3.0]},
            {"input": {"pairs": []}, "expected": []},
            {"input": {"pairs": [[0, 5]]}, "expected": [0.0]},
            {"input": {"pairs": [[4, 0], [8, 0]]}, "expected": [None, None]},
        ],
        "hints": [
            "Loop over the pairs, wrapping a / b in try/except ZeroDivisionError.",
            "Append None inside the except clause so the output length matches the input.",
        ],
    },
    # ── Track 8: Graphs & Graph Optimization (MIT 6.0002 / 6.0001 Adv) ──────────────────
    {
        "slug": "py-graph-adjacency-build",
        "title": "Graphs, Digraphs & Adjacency (Guttag Ch. 14)",
        "kind": "fundamental",
        "track": "track_8_graphs",
        "difficulty": "Easy",
        "category": "Graphs",
        "tags": ["MIT 6.0002 / 6.0001 Adv", "Guttag § 14.3", "Graphs", "Adjacency List", "Adjacency Matrix"],
        "description": """### \U0001f3db\ufe0f Finger Exercise: Building the Adjacency Structure
**MIT 6.0001 Citation**: *Chapter 14: Knapsack and Graph Optimization Problems (\u00a7 14.2 Graph Optimization Problems)*

A **graph** is a set of **nodes** (vertices) connected by **edges** (arcs). In a **digraph** the edges are
one-way: each has a **source** (parent) node and a **destination** (child) node.

Write `build_adjacency(n: int, edges: list[tuple[int, int]], directed: bool) -> list[list[int]]` returning an
adjacency list of `n` entries, where entry `i` holds `i`'s neighbours in ascending order. When `directed` is
`False`, every edge is added in both directions.
""",
        "examples": [
            {"input": "n = 3, edges = [(0,1),(0,2)], directed = False", "output": "[[1, 2], [0], [0]]"},
            {"input": "n = 3, edges = [(0,1),(0,2)], directed = True", "output": "[[1, 2], [], []]"},
        ],
        "constraints": ["1 <= n <= 1000", "0 <= u, v < n"],
        "starter_codes": {
            "python": """def build_adjacency(n: int, edges: list, directed: bool) -> list:
    # Return a list of n neighbour-lists, each sorted ascending
    pass
"""
        },
        "solutions": {
            "python": """def build_adjacency(n: int, edges: list, directed: bool) -> list:
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        if not directed:
            adj[v].append(u)
    for row in adj:
        row.sort()
    return adj
"""
        },
        "editorial": """# \U0001f4d6 Chapter 14: Knapsack and Graph Optimization Problems (\u00a7 14.2)
*John V. Guttag \u2014 Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

---

### \u00a7 1. Theoretical Foundations: Why Graphs Matter
A graph is a set of **nodes** (also called vertices) connected by **edges** (also called arcs). That is the entire
definition, and its generality is the point: any pairwise relation is a graph.

Guttag's framing is that formulating a problem as a graph is valuable precisely because **well-known algorithms
already exist** for the optimization problems that arise on them. You do not invent an algorithm; you recognize
a shape and reach for the matching tool.

Two variants matter:
- **Undirected graph** \u2014 the relation is symmetric. Facebook's "friend" relation: if Sam is a friend of Andrea,
  Andrea is a friend of Sam.
- **Directed graph (digraph)** \u2014 the relation is asymmetric. Each edge has a **source (parent)** node and a
  **destination (child)** node, and they are not interchangeable.

---

### \u00a7 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 14, \u00a7 14.2 and Figures 14-7/14-8 \u2014 paraphrase, not a verbatim quotation)*

Guttag builds the abstraction in layers: a `Node` class, an `Edge` class holding a source and a destination, then
`Graph` and `Digraph` classes. Notably he makes `Graph` a **subclass of `Digraph`** \u2014 an undirected graph is a
digraph in which every edge exists in both directions, so `Graph.add_edge` adds the reverse edge as well.

He names the two standard representations:

- **Adjacency matrix** \u2014 a 2-D table where cell `(i, j)` records whether an edge runs from `i` to `j`.
  $O(V^2)$ space; edge lookup is $O(1)$.
- **Adjacency list** \u2014 for each node, a list of the nodes it connects to. $O(V + E)$ space.

Which to choose depends on **density**. A graph where most possible edges exist (dense) suits a matrix; a graph
where each node has few neighbours (sparse) suits a list. Almost every interview graph is sparse, so the
adjacency list is the default.

---

### \u00a7 3. Canonical Code Walkthrough
```python
n = 4
edges = [(0, 1), (0, 2), (1, 3)]

# UNDIRECTED -- each edge recorded from both endpoints
adj = [[] for _ in range(n)]
for u, v in edges:
    adj[u].append(v)
    adj[v].append(u)
# [[1, 2], [0, 3], [0], [1]]

# DIRECTED -- source to destination only
adj = [[] for _ in range(n)]
for u, v in edges:
    adj[u].append(v)
# [[1, 2], [3], [], []]
```

The dict form, when nodes are not integers `0..n-1`:

```python
from collections import defaultdict
adj = defaultdict(list)
for u, v in edges:
    adj[u].append(v)
    adj[v].append(u)      # drop this line for a digraph
```

---

### \u00a7 4. Common Pitfalls & Invariant Rules
1. **Forgetting the reverse edge** is the classic undirected-graph bug. The traversal runs, finds a subset of the
   graph, and reports a confidently wrong answer.
2. **`[[]] * n` aliases one list `n` times.** Use `[[] for _ in range(n)]` \u2014 the same trap as the DP-grid drill.
3. **Self-loops and duplicate edges.** `(u, u)` adds `u` as its own neighbour; a repeated edge appears twice. Both
   are legal graphs, and both break code that assumes otherwise.
4. **Matrix costs $O(V^2)$ even when empty.** For $V = 10^5$ that is $10^{10}$ cells \u2014 not allocatable. Sparse
   graphs must use lists.
5. **Build once, outside the traversal.** Rebuilding adjacency inside a loop turns $O(V+E)$ into $O(V \\cdot E)$.

---

### \u00a7 5. Bridging to LeetCode Mastery
- **LeetCode 207/210 (Course Schedule I/II)**: prerequisites are a digraph; build adjacency plus in-degrees first.
- **LeetCode 133 (Clone Graph)**, **LeetCode 323 (Connected Components)**: undirected, both directions required.
- **LeetCode 1971 (Find if Path Exists)**: the minimal build-then-traverse exercise.
- Grids are **implicit** graphs \u2014 no adjacency structure needed, the 4 direction offsets *are* the edges.
""",
        "test_cases": [
            {"input": {"n": 3, "edges": [[0, 1], [0, 2]], "directed": False}, "expected": [[1, 2], [0], [0]]},
            {"input": {"n": 3, "edges": [[0, 1], [0, 2]], "directed": True}, "expected": [[1, 2], [], []]},
            {"input": {"n": 2, "edges": [], "directed": False}, "expected": [[], []]},
            {"input": {"n": 4, "edges": [[0, 1], [1, 3]], "directed": False}, "expected": [[1], [0, 3], [], [1]]},
        ],
        "hints": [
            "Build adj = [[] for _ in range(n)] -- never [[]] * n.",
            "Append v to adj[u]; when undirected also append u to adj[v].",
            "Sort each neighbour list before returning.",
        ],
    },
    {
        "slug": "py-graph-bfs-shortest-path",
        "title": "BFS Shortest Path (Guttag Ch. 14)",
        "kind": "fundamental",
        "track": "track_8_graphs",
        "difficulty": "Medium",
        "category": "Graphs",
        "tags": ["MIT 6.0002 / 6.0001 Adv", "Guttag § 14.4", "BFS", "Shortest Path", "Queue Scaffold"],
        "description": """### \U0001f3db\ufe0f Finger Exercise: Fewest Edges Wins
**MIT 6.0001 Citation**: *Chapter 14 (\u00a7 14.2.2 Shortest Path: Depth-First Search and Breadth-First Search)*

**Breadth-first search** generates paths in **ascending order of length**, so the first path it finds to the goal
is guaranteed to use the minimum number of edges.

Write `shortest_hops(n: int, edges: list[tuple[int, int]], start: int, end: int) -> int` returning the fewest
edges on any path from `start` to `end` in an **undirected** graph, or `-1` if unreachable. `start == end` is 0.
""",
        "examples": [
            {"input": "n = 4, edges = [(0,1),(1,2),(2,3),(0,3)], start = 0, end = 2", "output": "2"},
            {"input": "n = 3, edges = [(0,1)], start = 0, end = 2", "output": "-1"},
        ],
        "constraints": ["1 <= n <= 10^4", "0 <= start, end < n"],
        "starter_codes": {
            "python": """from collections import deque

def shortest_hops(n: int, edges: list, start: int, end: int) -> int:
    # BFS level by level; return the depth at which end is first reached
    pass
"""
        },
        "solutions": {
            "python": """from collections import deque

def shortest_hops(n: int, edges: list, start: int, end: int) -> int:
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)

    if start == end:
        return 0

    seen = {start}
    q = deque([(start, 0)])
    while q:
        node, d = q.popleft()
        for nxt in adj[node]:
            if nxt == end:
                return d + 1
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, d + 1))
    return -1
"""
        },
        "editorial": """# \U0001f4d6 Chapter 14 (\u00a7 14.2.2 Shortest Path: Depth-First and Breadth-First Search)
*John V. Guttag \u2014 Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

---

### \u00a7 1. Theoretical Foundations: Why BFS Finds the Shortest Path
BFS explores **many paths simultaneously**, adding one node to each path on every iteration. Because it extends
all length-$k$ paths before it creates any length-$(k+1)$ path, it enumerates paths in ascending order of length.

That ordering is the whole guarantee. Guttag states the consequence directly: since BFS generates the paths in
ascending order of length, **the first path found with the goal as its last node is guaranteed to have a minimum
number of edges**. No comparison step is needed \u2014 you return on first contact and you are provably optimal.

Guttag also notes the implementation asymmetry: DFS is "often implemented recursively", BFS is "usually
implemented iteratively" \u2014 because the queue must be explicit.

---

### \u00a7 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 14, \u00a7 14.2.2 and Figure 14-11 \u2014 paraphrase, not a verbatim quotation)*

The motivating example is the "six degrees of separation" question: given a social network as a graph with people
as nodes and the *friend* relation as edges, how many hops separate you from Lady Gaga? Because friendship is
symmetric, the graph is undirected.

Guttag's Figure 14-11 keeps a `path_queue` holding every path currently being explored. Each iteration removes
one path, checks whether its last node is the goal, and otherwise creates a new extended path for each child,
appending them all back to the queue. Tracing his 6-node digraph prints the paths in exactly ascending length
order \u2014 `0`, then `0->1`, `0->2`, then the length-3 paths, and so on \u2014 which is the property being relied on.

He closes with a finger exercise worth keeping in mind: *"Consider a digraph with weighted edges. Is the first
path found by BFS guaranteed to minimize the sum of the weights of the edges?"* The answer is **no** \u2014 BFS
minimizes the **count** of edges, not their total weight. Weighted shortest paths need Dijkstra.

---

### \u00a7 3. Canonical Code Walkthrough
```python
from collections import deque

def bfs(adj, start, end):
    if start == end:
        return 0
    seen = {start}                 # mark on ENQUEUE, never on dequeue
    q = deque([(start, 0)])        # (node, distance so far)
    while q:
        node, d = q.popleft()      # O(1) -- a list would make this O(N)
        for nxt in adj[node]:
            if nxt == end:
                return d + 1       # first contact IS the shortest
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, d + 1))
    return -1                      # queue drained, goal unreachable
```

Tracing on `edges = [(0,1),(1,2),(2,3),(0,3)]`, from `0` to `2`:

```
q = [(0,0)]                 seen = {0}
pop (0,0)  neighbours 1, 3  -> q = [(1,1), (3,1)]   seen = {0,1,3}
pop (1,1)  neighbour 2 == end  -> return 1 + 1 = 2
```

Two hops, `0 -> 1 -> 2`. The alternative `0 -> 3 -> 2` is also length 2 \u2014 when several shortest paths exist,
BFS returns whichever it reaches first, and Guttag notes DFS and BFS need not agree on *which* one.

---

### \u00a7 4. Common Pitfalls & Invariant Rules
1. **Mark visited on enqueue, not on dequeue.** Marking at pop time lets the same node enter the queue many times
   before it is first processed \u2014 the queue balloons and the run degrades badly.
2. **`list.pop(0)` silently makes it $O(V^2)$.** Use `deque.popleft()`. This is the single most common cause of a
   correct-looking BFS that times out.
3. **BFS minimizes edge count, not edge weight.** With weights, use Dijkstra \u2014 exactly Guttag's finger exercise.
4. **Handle `start == end` up front**, or the loop returns `-1` for a trivially reachable node.
5. **Complexity is $O(V + E)$ time, $O(V)$ space.** Every node is enqueued at most once, every edge inspected at
   most twice in an undirected graph.

---

### \u00a7 5. Bridging to LeetCode Mastery
- **LeetCode 1091 (Shortest Path in Binary Matrix)**, **LeetCode 127 (Word Ladder)**: unweighted shortest path.
- **LeetCode 994 (Rotting Oranges)**: multi-source BFS \u2014 seed the queue with *every* start, distance still works.
- **LeetCode 102 (Binary Tree Level Order)**: the level-snapshot pattern, `for _ in range(len(q))`.
- **LeetCode 542 (01 Matrix)**: multi-source BFS on a grid.
""",
        "test_cases": [
            {"input": {"n": 4, "edges": [[0, 1], [1, 2], [2, 3], [0, 3]], "start": 0, "end": 2}, "expected": 2},
            {"input": {"n": 3, "edges": [[0, 1]], "start": 0, "end": 2}, "expected": -1},
            {"input": {"n": 1, "edges": [], "start": 0, "end": 0}, "expected": 0},
            {"input": {"n": 5, "edges": [[0, 1], [1, 2], [2, 3], [3, 4]], "start": 0, "end": 4}, "expected": 4},
        ],
        "hints": [
            "Build the undirected adjacency list first.",
            "Use deque and store (node, distance) pairs.",
            "Return d + 1 the moment a neighbour equals end; mark seen when you enqueue.",
        ],
    },
    {
        "slug": "py-graph-dfs-cycle-detect",
        "title": "DFS & Cycle Detection (Guttag Ch. 14)",
        "kind": "fundamental",
        "track": "track_8_graphs",
        "difficulty": "Medium",
        "category": "Graphs",
        "tags": ["MIT 6.0002 / 6.0001 Adv", "Guttag § 14.4", "DFS", "Cycle Detection", "3-State Coloring"],
        "description": """### \U0001f3db\ufe0f Finger Exercise: Cyclic or Acyclic?
**MIT 6.0001 Citation**: *Chapter 14 (\u00a7 14.2.2 Shortest Path: Depth-First Search and Breadth-First Search)*

A **path** is a sequence of edges leading from one node to another; a **cycle** is a path that returns to where
it started. A graph containing a cycle is **cyclic**, one without is **acyclic**.

Write `has_cycle(n: int, edges: list[tuple[int, int]]) -> bool` that returns `True` when the **directed** graph
contains a cycle. Use DFS with three states so that revisiting a node already finished is not mistaken for a cycle.
""",
        "examples": [
            {"input": "n = 3, edges = [(0,1),(1,2),(2,0)]", "output": "True"},
            {"input": "n = 3, edges = [(0,1),(0,2),(1,2)]", "output": "False", "explanation": "Diamond shape, but no way back to 0."},
        ],
        "constraints": ["1 <= n <= 10^4"],
        "starter_codes": {
            "python": """def has_cycle(n: int, edges: list) -> bool:
    # DFS with WHITE / GREY / BLACK colouring
    pass
"""
        },
        "solutions": {
            "python": """def has_cycle(n: int, edges: list) -> bool:
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)

    WHITE, GREY, BLACK = 0, 1, 2
    colour = [WHITE] * n

    def dfs(node):
        colour[node] = GREY
        for nxt in adj[node]:
            if colour[nxt] == GREY:
                return True
            if colour[nxt] == WHITE and dfs(nxt):
                return True
        colour[node] = BLACK
        return False

    for i in range(n):
        if colour[i] == WHITE and dfs(i):
            return True
    return False
"""
        },
        "editorial": """# \U0001f4d6 Chapter 14 (\u00a7 14.2.2 Depth-First Search)
*John V. Guttag \u2014 Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

---

### \u00a7 1. Theoretical Foundations: Depth First, Then Back Up
Depth-first search follows one branch as far as it will go, then **backtracks** to the most recent unexplored
alternative. Guttag notes it is "often implemented recursively" \u2014 the call stack *is* the record of the current
path, which is exactly what makes cycle detection natural.

The vocabulary Guttag introduces here does the work:
- A **path** is a sequence of edges from one node to another.
- A **cycle** is a path whose start and end are the same node.
- A graph with at least one cycle is **cyclic**; one with none is **acyclic**.

An acyclic digraph (a DAG) is the structure that admits a valid ordering of dependencies. A cyclic one does not
\u2014 which is why "can these courses be scheduled?" is literally "is this digraph acyclic?".

---

### \u00a7 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 14, \u00a7 14.2.2 and Figure 14-9 \u2014 paraphrase, not a verbatim quotation)*

Guttag's DFS shortest-path code (Figure 14-9) carries the path built so far and, critically, checks whether a
candidate next node is **already in that path** before recursing. Without that guard, a cyclic graph sends the
recursion around the loop forever.

That guard is the seed of cycle detection. The subtlety is that "already visited" and "currently on the path" are
different questions. A node reached twice by two different branches is not a cycle; a node reached again *while
still on the current recursion stack* is. Conflating the two reports cycles that do not exist.

The standard fix is three colours:

| Colour | Meaning |
| :-- | :-- |
| **WHITE** | not yet visited |
| **GREY** | on the current recursion stack \u2014 we are inside its call |
| **BLACK** | fully explored, its whole subtree is finished |

Encountering a **GREY** node is a back edge, and a back edge is exactly a cycle.

---

### \u00a7 3. Canonical Code Walkthrough
```python
WHITE, GREY, BLACK = 0, 1, 2
colour = [WHITE] * n

def dfs(node):
    colour[node] = GREY               # entering: now on the stack
    for nxt in adj[node]:
        if colour[nxt] == GREY:       # back edge -> CYCLE
            return True
        if colour[nxt] == WHITE and dfs(nxt):
            return True
    colour[node] = BLACK              # leaving: subtree finished
    return False

# Every node must be tried: the graph may be disconnected.
for i in range(n):
    if colour[i] == WHITE and dfs(i):
        return True
```

Tracing `edges = [(0,1),(1,2),(2,0)]`:

```
dfs(0)  colour[0] = GREY
  dfs(1)  colour[1] = GREY
    dfs(2)  colour[2] = GREY
      neighbour 0 is GREY  ->  CYCLE FOUND
```

And on the acyclic `[(0,1),(0,2),(1,2)]`:

```
dfs(0)  GREY
  dfs(1)  GREY -> dfs(2) GREY -> no neighbours -> BLACK; 1 -> BLACK
  neighbour 2 is BLACK  ->  finished already, NOT a cycle
0 -> BLACK, no cycle
```

Node 2 is reached twice \u2014 and a two-state visited set would wrongly flag it.

---

### \u00a7 4. Common Pitfalls & Invariant Rules
1. **Two states are not enough for a digraph.** A plain `visited` set reports a false cycle whenever two branches
   converge on the same node. You need to distinguish "on the stack" from "done".
2. **Undirected graphs use a different rule.** There, track the **parent** and ignore the edge you arrived on;
   any *other* visited neighbour is a cycle. Applying the directed rule to an undirected graph flags every edge.
3. **Loop over every node.** A disconnected graph can hide its cycle in a component your first DFS never reaches.
4. **Recursion depth is $O(V)$.** A 10^5-node chain overflows CPython's stack \u2014 convert to an explicit stack.
5. **Complexity is $O(V + E)$.** Each node is coloured once and each edge examined once.

---

### \u00a7 5. Bridging to LeetCode Mastery
- **LeetCode 207 (Course Schedule)**: literally "is this digraph acyclic?" \u2014 this exact algorithm.
- **LeetCode 210 (Course Schedule II)**: same detection, plus emit the order (nodes turn BLACK in reverse
  topological order).
- **LeetCode 802 (Find Eventual Safe States)**: the colouring generalizes directly.
- **LeetCode 261 (Graph Valid Tree)**: undirected \u2014 use the parent rule, and check edge count is `n - 1`.
""",
        "test_cases": [
            {"input": {"n": 3, "edges": [[0, 1], [1, 2], [2, 0]]}, "expected": True},
            {"input": {"n": 3, "edges": [[0, 1], [0, 2], [1, 2]]}, "expected": False},
            {"input": {"n": 2, "edges": []}, "expected": False},
            {"input": {"n": 4, "edges": [[0, 1], [2, 3], [3, 2]]}, "expected": True},
        ],
        "hints": [
            "Colour each node WHITE (unvisited), GREY (on stack), BLACK (finished).",
            "Seeing a GREY neighbour means a back edge, which is a cycle.",
            "Start a DFS from every WHITE node -- the graph may be disconnected.",
        ],
    },
    {
        "slug": "py-graph-greedy-vs-optimal",
        "title": "Greedy Algorithms & Where They Fail (Guttag Ch. 14)",
        "kind": "fundamental",
        "track": "track_8_graphs",
        "difficulty": "Easy",
        "category": "Optimization",
        "tags": ["MIT 6.0002 / 6.0001 Adv", "Guttag § 14.2", "Greedy Heuristics", "Optimization"],
        "description": """### \U0001f3db\ufe0f Finger Exercise: Locally Optimal Is Not Globally Optimal
**MIT 6.0001 Citation**: *Chapter 14 (\u00a7 14.1.1 Greedy Algorithms)*

A **greedy algorithm** makes the choice that looks best right now and never reconsiders. It is fast and simple,
and for the **0/1 knapsack** it is **not guaranteed to be optimal**.

Write `greedy_by_density(weights, values, capacity) -> int` that takes items in descending value-to-weight
order, adding each whole item that still fits, and returns the total value obtained. The drill is to see the
greedy answer, then compare it to the true optimum from the knapsack DP drill.
""",
        "examples": [
            {
                "input": "weights = [1, 2, 3], values = [6, 10, 12], capacity = 5",
                "output": "16",
                "explanation": "Greedy takes item 0 (density 6.0) then item 1 (5.0), filling 3 of 5 units for value 16. The optimum is items 1+2: weight exactly 5, value 22. Greedy committed to item 0 and could not take it back.",
            }
        ],
        "constraints": ["len(weights) == len(values) <= 100", "capacity >= 0"],
        "starter_codes": {
            "python": """def greedy_by_density(weights: list, values: list, capacity: int) -> int:
    # Sort by value/weight descending, take each whole item that fits
    pass
"""
        },
        "solutions": {
            "python": """def greedy_by_density(weights: list, values: list, capacity: int) -> int:
    items = sorted(
        range(len(weights)),
        key=lambda i: values[i] / weights[i],
        reverse=True,
    )
    total = 0
    remaining = capacity
    for i in items:
        if weights[i] <= remaining:
            remaining -= weights[i]
            total += values[i]
    return total
"""
        },
        "editorial": """# \U0001f4d6 Chapter 14 (\u00a7 14.1.1 Greedy Algorithms)
*John V. Guttag \u2014 Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

---

### \u00a7 1. Theoretical Foundations: The Shape of an Optimization Problem
Guttag frames every optimization problem with two parts:

1. An **objective function** to maximize or minimize.
2. A **set of constraints** that any solution must satisfy.

For the knapsack, the objective is total value and the constraint is total weight. Recognizing this shape is what
tells you which family of algorithms applies.

A **greedy algorithm** makes a sequence of **locally optimal** choices, hoping to arrive somewhere **globally
optimal**. It usually will not. That gap \u2014 locally optimal versus globally optimal \u2014 is the vocabulary Guttag
introduces here, and it is the entire lesson.

---

### \u00a7 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 14, \u00a7 14.1.1 \u2014 paraphrase, not a verbatim quotation)*

The obvious appeal of greedy is cost: sort the items, walk the list once. That is $O(n \\log n)$, against
exponential brute force.

The catch is that "best" is ambiguous, and the answer changes with the definition. Guttag runs the same greedy
scaffold under different metrics \u2014 take the most valuable item first, take the lightest item first, take the
best value-per-unit-weight first \u2014 and gets **different answers**, none reliably optimal. A greedy algorithm is
only as good as the ordering you happen to choose, and nothing about the method tells you which ordering is right.

The one case where greedy *is* provably optimal is the **continuous (fractional) knapsack**, where items may be
split. There you fill with the densest item until it runs out, then the next, and the last item is taken
fractionally to exactly fill the bag. No better packing exists.

The moment items become all-or-nothing \u2014 the **0/1 knapsack** \u2014 that proof collapses, and dynamic programming
becomes necessary.

---

### \u00a7 3. Canonical Code Walkthrough
```python
def greedy_by_density(weights, values, capacity):
    order = sorted(range(len(weights)),
                   key=lambda i: values[i] / weights[i],
                   reverse=True)
    total, remaining = 0, capacity
    for i in order:
        if weights[i] <= remaining:      # whole item only -- this is the 0/1 constraint
            remaining -= weights[i]
            total += values[i]
    return total
```

**The counterexample that matters.** `weights = [1, 2, 3]`, `values = [6, 10, 12]`, `capacity = 5`:

```
densities: item0 = 6/1 = 6.0,  item1 = 10/2 = 5.0,  item2 = 12/3 = 4.0
greedy order: item0, item1, item2   (densest first)
  take item0 (w=1)  remaining 4,  value 6
  take item1 (w=2)  remaining 2,  value 16
  item2 (w=3) does not fit in the remaining 2
greedy total = 16

optimum: item1 + item2 = weight 2 + 3 = 5 exactly, value 10 + 12 = 22
```

Greedy scores **16 against an optimum of 22** — a 27% shortfall, on three items. And note *why* it lost: item0
had the best density, so greedy grabbed it first, and that single unit of wasted capacity locked out the pairing
that exactly filled the bag. The choice was irrevocable, and that irrevocability is the defect.

---

### \u00a7 4. Common Pitfalls & Invariant Rules
1. **Greedy needs a proof, not a vibe.** It is correct only when the problem has the greedy-choice property.
   Without one, an interviewer's follow-up counterexample sinks the answer.
2. **The metric changes the answer.** Most-valuable-first, lightest-first and best-density-first are all "greedy"
   and all give different results. Say which ordering you mean.
3. **Fractional is optimal; 0/1 is not.** Know which variant you have been handed.
4. **Greedy never backtracks.** That is the source of both its speed and its wrongness.
5. **Use greedy as the baseline.** State it, show the counterexample, then reach for DP \u2014 that sequence
   demonstrates you know *why* DP is required.

---

### \u00a7 5. Bridging to LeetCode Mastery
- **Genuinely greedy**: LeetCode 55 (Jump Game), 134 (Gas Station), 435 (Non-overlapping Intervals),
  452 (Burst Balloons with arrows) \u2014 each has a provable exchange argument.
- **Looks greedy, is not**: LeetCode 322 (Coin Change) \u2014 largest-coin-first fails on `coins=[1,3,4], amount=6`
  (greedy gives 4+1+1 = 3 coins; optimal is 3+3 = 2). Needs DP.
- **LeetCode 416 (Partition Equal Subset Sum)**: the 0/1 knapsack in disguise \u2014 greedy cannot solve it.
""",
        "test_cases": [
            {"input": {"weights": [5, 4, 6], "values": [10, 8, 12], "capacity": 10}, "expected": 18},
            {"input": {"weights": [1, 2, 3], "values": [6, 10, 12], "capacity": 5}, "expected": 16},
            {"input": {"weights": [10], "values": [100], "capacity": 5}, "expected": 0},
            {"input": {"weights": [2, 2], "values": [3, 3], "capacity": 4}, "expected": 6},
        ],
        "hints": [
            "Sort item indices by values[i] / weights[i], descending.",
            "Walk that order, taking a whole item only when it still fits.",
            "Compare your answer to the 0/1 knapsack DP drill -- greedy can be lower.",
        ],
    },
    {
        "slug": "py-fluency-tuples-multiple-assign",
        "title": "Tuples & Multiple Assignment (Guttag Ch. 5)",
        "kind": "fundamental",
        "track": "track_1_pythonic_fluency",
        "difficulty": "Easy",
        "category": "Structured Types",
        "tags": ["MIT 6.0001 Lec 5", "Guttag § 5.1", "Tuples", "Destructuring", "Immutability"],
        "description": """### Finger Exercise: Packing and Unpacking
**MIT 6.0001 Citation**: *Chapter 5: Structured Types and Mutability (§ 5.1 Tuples, § 5.1.1 Multiple Assignment)*

A **tuple** is an ordered, **immutable** sequence. Because it cannot change, it is hashable, so it can key a
dict or join a set. **Multiple assignment** unpacks one in a single statement.

Write `min_max_swap(pairs: list[tuple[int, int]]) -> list[tuple[int, int]]` that returns each pair reordered
so the smaller value comes first, using tuple unpacking rather than indexing.
""",
        "examples": [{"input": "pairs = [(3, 1), (2, 8)]", "output": "[(1, 3), (2, 8)]"}],
        "constraints": ["0 <= len(pairs) <= 1000"],
        "starter_codes": {
            "python": """def min_max_swap(pairs: list) -> list:
    # Unpack each pair with `a, b = pair` and return it ordered
    pass
"""
        },
        "solutions": {
            "python": """def min_max_swap(pairs: list) -> list:
    out = []
    for a, b in pairs:
        if a > b:
            a, b = b, a
        out.append((a, b))
    return out
"""
        },
        "editorial": """# \U0001f4d6 Chapter 5: Structured Types and Mutability (§ 5.1 Tuples)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Ordered and Frozen
A tuple is an ordered sequence, written with parentheses, whose elements may be of any type — including other
tuples. It is Python's first **non-scalar immutable** type, and that immutability is not a restriction so much as
a capability: it is exactly what makes a tuple **hashable**.

Guttag pairs tuples with **multiple assignment**, the idiom that binds several names at once:

```python
x, y = 1, 2
```

The right-hand side is evaluated *fully* before any binding happens, which is what makes the one-line swap work.

---

### § 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 5, § 5.1 — paraphrase, not a verbatim quotation)*

Guttag's point is that multiple assignment is "particularly convenient when functions return multiple values."
A function computing both a minimum and a maximum returns them as one tuple, and the caller unpacks:

```python
def get_min_and_max(vals):
    return min(vals), max(vals)     # packs into a tuple

low, high = get_min_and_max([3, 1, 4])   # unpacks into two names
```

The alternative — returning a list and indexing `result[0]`, `result[1]` — is both noisier and less safe: the
unpacking form raises immediately if the arity is wrong, rather than silently reading the wrong slot.

The syntactic wrinkle worth remembering: a **one-element tuple needs a trailing comma**. `(1)` is just the
integer `1` in parentheses; `(1,)` is a tuple of length one.

---

### § 3. Canonical Code Walkthrough
```python
t = (1, 'two', 3)
t[0]                 # 1        indexing works
t[1:]                # ('two', 3)   slicing returns a tuple
len(t)               # 3
# t[0] = 9           # TypeError: 'tuple' object does not support item assignment

# The swap -- right side fully evaluated first, so no temp variable needed
a, b = 3, 1
a, b = b, a          # a = 1, b = 3

# Packing on return, unpacking at the call site
def divide(n, d):
    return n // d, n % d

q, r = divide(17, 5)     # q = 3, r = 2

# Hashability is the payoff
seen = {(0, 1), (2, 3)}       # tuples in a set -- fine
# {[0, 1]}                    # TypeError: unhashable type: 'list'
memo = {(3, 7): 'computed'}   # the standard DP memo key

# The trailing-comma trap
type((1))        # <class 'int'>
type((1,))       # <class 'tuple'>
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **`(1)` is not a tuple.** Without the trailing comma it is a parenthesized integer. This bites when returning
   a single-element tuple.
2. **Immutable does not mean deeply immutable.** `([1], 2)` is a tuple whose first element is a mutable list —
   and that tuple is *unhashable*, because hashability requires every element to be hashable.
3. **Unpacking arity must match exactly.** `a, b = (1, 2, 3)` raises `ValueError: too many values to unpack`.
   Use `a, *rest = ...` when the tail length varies.
4. **Tuples compare lexicographically**, element by element — which is why `key=lambda x: (-count, name)` gives
   multi-level sorting for free.
5. **Prefer a tuple for a fixed-arity record**, a list for a homogeneous collection. The type documents intent.

---

### § 5. Bridging to LeetCode Mastery
- **DP memo keys**: `memo[(i, remaining)]` requires a tuple — a list key raises `TypeError`.
- **Heap entries**: `heappush(h, (priority, tiebreak, item))` sorts by the tuple order automatically.
- **Coordinate sets**: `visited = {(r, c)}` in grid traversals.
- **Returning two values from a DFS**: `return height, is_balanced` avoids a second traversal.
""",
        "test_cases": [
            {"input": {"pairs": [[3, 1], [2, 8]]}, "expected": [[1, 3], [2, 8]]},
            {"input": {"pairs": []}, "expected": []},
            {"input": {"pairs": [[5, 5]]}, "expected": [[5, 5]]},
        ],
        "hints": ["Iterate with `for a, b in pairs`.", "Swap with `a, b = b, a` when a > b."],
    },
    {
        "slug": "py-fluency-sets-dicts",
        "title": "Sets, Dictionaries & Hashable Types (Guttag Ch. 5)",
        "kind": "fundamental",
        "track": "track_1_pythonic_fluency",
        "difficulty": "Easy",
        "category": "Structured Types",
        "tags": ["MIT 6.0001 Lec 5", "MIT 6.0001 Pset 3", "Sets", "Dicts", "Hashable Types"],
        "description": """### Finger Exercise: Membership in Constant Time
**MIT 6.0001 Citation**: *Chapter 5: Structured Types and Mutability (§ 5.6 Sets, § 5.7 Dictionaries)*

A **set** is an unordered collection of distinct **hashable** objects. A **dictionary** maps hashable **keys**
to **values**. Both give average $O(1)$ membership — against $O(n)$ for a list.

Write `common_counts(a: list[str], b: list[str]) -> dict` returning, for every string appearing in **both**
lists, how many times it appears in `a`. Words absent from `b` are excluded.
""",
        "examples": [
            {"input": "a = ['x','y','x','z'], b = ['x','z']", "output": "{'x': 2, 'z': 1}"},
        ],
        "constraints": ["0 <= len(a), len(b) <= 10^4"],
        "starter_codes": {
            "python": """def common_counts(a: list, b: list) -> dict:
    # Use a set for membership and a dict for counting
    pass
"""
        },
        "solutions": {
            "python": """def common_counts(a: list, b: list) -> dict:
    in_b = set(b)
    out = {}
    for w in a:
        if w in in_b:
            out[w] = out.get(w, 0) + 1
    return out
"""
        },
        "editorial": """# \U0001f4d6 Chapter 5 (§ 5.6 Sets, § 5.7 Dictionaries)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Hashability Is the Entry Requirement
Both `set` and `dict` are built on hashing, and both impose the same admission rule: their members (or keys)
must be **hashable**. Guttag introduces `hashable type` as a term precisely here.

An object is hashable when its hash value stays fixed for its lifetime. Mutable containers cannot promise that —
change the contents and the correct bucket changes, so the object would go missing from the table it was filed
in. Hence: `int`, `str`, `tuple`, `frozenset` may be keys; `list`, `dict`, `set` may not.

The payoff is the complexity difference that decides most interview problems:

| Operation | `list` | `set` / `dict` |
| :-- | :-- | :-- |
| `x in c` | $O(n)$ | $O(1)$ average |
| insert | $O(1)$ amortized | $O(1)$ average |
| delete | $O(n)$ | $O(1)$ average |

---

### § 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 5, § 5.6–5.7 — paraphrase, not a verbatim quotation)*

Guttag presents sets as the computational form of the mathematical set: unordered, no duplicates, supporting
union (`|`), intersection (`&`), difference (`-`) and subset tests. The unorderedness is a real constraint —
he is explicit that you should not rely on the iteration order of a set.

Dictionaries he describes as a mapping from keys to values, and he stresses the **`view object`**: `d.keys()`,
`d.values()` and `d.items()` are not snapshots but *live views* onto the dict. Mutate the dict and the view
reflects it — which is why mutating a dict while iterating its keys raises `RuntimeError`.

He returns to dicts in Chapter 12 to explain *why* they are fast: hashing converts a key into a list index, and
lookup is constant time provided collisions stay rare. The Chapter 5 promise is cashed by the Chapter 12
mechanism.

---

### § 3. Canonical Code Walkthrough
```python
# SETS -- membership, dedupe, algebra
s = {3, 1, 4, 1}          # {1, 3, 4}   duplicates collapse
3 in s                    # True, O(1)
s.add(5); s.discard(9)    # discard tolerates a missing element; remove raises

{1, 2} | {2, 3}           # {1, 2, 3}   union
{1, 2} & {2, 3}           # {2}         intersection
{1, 2} - {2, 3}           # {1}         difference

# DICTIONARIES -- mapping and safe access
d = {'a': 1, 'b': 2}
d['a']                    # 1
d['zz']                   # KeyError
d.get('zz', 0)            # 0      <- the branch-free idiom
d.setdefault('c', []).append(7)

for k, v in d.items():    # a live view, not a copy
    ...

from collections import Counter, defaultdict
Counter('mississippi')    # {'i': 4, 's': 4, 'p': 2, 'm': 1}
g = defaultdict(list); g['k'].append(1)   # no "if key not in" branch

# HASHABILITY
{(1, 2)}                  # fine -- tuple is immutable
# {[1, 2]}                # TypeError: unhashable type: 'list'
frozenset([1, 2]) in {frozenset([1, 2])}   # True -- frozenset IS hashable
```

The $O(n)$ to $O(1)$ swap that wins interviews:

```python
# O(n^2): `in` on a list scans it every time
out = []
for x in items:
    if x not in out:
        out.append(x)

# O(n): `in` on a set is constant
seen = set()
for x in items:
    if x not in seen:
        seen.add(x)
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **`{}` is an empty dict, not an empty set.** The empty set is `set()`.
2. **Never rely on set iteration order.** Sort explicitly when the output order is graded.
3. **A list cannot be a key.** Convert to `tuple(...)` — this is exactly why *Group Anagrams* keys on
   `tuple(sorted(word))`.
4. **Mutating a dict while iterating raises `RuntimeError`.** Iterate over `list(d.keys())` when you must delete.
5. **`d[k]` raises; `d.get(k, default)` does not.** Choose deliberately — a `KeyError` is sometimes the correct,
   loud behaviour.
6. **$O(1)$ is *expected*, not worst case.** Adversarial keys can collide into one bucket and degrade to $O(n)$.

---

### § 5. Bridging to LeetCode Mastery
- **LeetCode 1 (Two Sum)**: dict from value to index; look up the complement in $O(1)$.
- **LeetCode 49 (Group Anagrams)**: `defaultdict(list)` keyed on the sorted-character tuple.
- **LeetCode 128 (Longest Consecutive Sequence)**: set membership turns $O(n \\log n)$ into $O(n)$.
- **LeetCode 217 (Contains Duplicate)**, **242 (Valid Anagram)**, **560 (Subarray Sum Equals K)**.
""",
        "test_cases": [
            {"input": {"a": ["x", "y", "x", "z"], "b": ["x", "z"]}, "expected": {"x": 2, "z": 1}},
            {"input": {"a": [], "b": ["x"]}, "expected": {}},
            {"input": {"a": ["q"], "b": []}, "expected": {}},
            {"input": {"a": ["m", "m", "m"], "b": ["m"]}, "expected": {"m": 3}},
        ],
        "hints": [
            "Convert b to a set once, before the loop.",
            "Count with out[w] = out.get(w, 0) + 1.",
        ],
    },
    {
        "slug": "py-scaffold-recursive-factorial",
        "title": "Recursion & Recurrences: Factorial (Guttag Ch. 6)",
        "kind": "fundamental",
        "track": "track_3_algorithmic_scaffolds",
        "difficulty": "Easy",
        "category": "Inductive Recursion",
        "tags": ["MIT 6.0001 Lec 6", "Guttag § 6.1", "Recursion", "Factorial", "Call Stack"],
        "description": """### Finger Exercise: The Simplest Recursion
**MIT 6.0001 Citation**: *Chapter 6: Recursion and Global Variables (§ 6.1 Fibonacci Numbers)*

Guttag's Figure 6-1 gives **iterative and recursive implementations of factorial** side by side. The recursive
one is the definition transcribed:
$$n! = n \\times (n-1)! \\qquad 1! = 1$$

Write `factorial_recursive(n: int) -> int` using a base case and one recursive call. `factorial_recursive(0)`
must return `1`.
""",
        "examples": [{"input": "n = 5", "output": "120"}, {"input": "n = 0", "output": "1"}],
        "constraints": ["0 <= n <= 900"],
        "starter_codes": {
            "python": """def factorial_recursive(n: int) -> int:
    # Base case, then n * factorial_recursive(n - 1)
    pass
"""
        },
        "solutions": {
            "python": """def factorial_recursive(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial_recursive(n - 1)
"""
        },
        "editorial": """# \U0001f4d6 Chapter 6: Recursion and Global Variables (§ 6.1)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: An Inductive Definition Is Already Code
Guttag introduces recursion through **inductive definitions**. A recursive definition has exactly two parts:

1. A **base case** — the answer for the smallest input, given directly and without recursion.
2. A **recursive (inductive) case** — the answer for $n$ expressed in terms of strictly smaller inputs.

Factorial is the canonical example because the mathematics *is* the program:
$$1! = 1 \\qquad n! = n \\times (n-1)!$$

The mapping to code is mechanical. This is why Guttag places recursion immediately after functions: it is not a
trick, it is a definition style that Python can execute directly.

---

### § 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 6, § 6.1 and Figure 6-1 — paraphrase, not a verbatim quotation)*

Guttag shows the iterative and recursive versions together to make the trade explicit. The iterative version
carries an accumulator and a loop counter; the recursive version carries neither, because the call stack holds
that state implicitly.

His judgement is that the recursive version is easier to read and easier to convince yourself is correct — it
matches the definition line for line — while the iterative version avoids the per-call overhead and the depth
limit. Neither is universally better.

The correctness argument is induction: the base case is correct by inspection, and *if* the recursive call
returns the right answer for `n - 1`, then multiplying by `n` gives the right answer for `n`. Termination follows
because `n` strictly decreases toward the base case — the same **decrementing function** idea Guttag uses for
`while` loops.

---

### § 3. Canonical Code Walkthrough
```python
# RECURSIVE -- the definition, transcribed
def fact_recur(n):
    if n <= 1:            # BASE CASE
        return 1
    return n * fact_recur(n - 1)     # RECURSIVE CASE

# ITERATIVE -- explicit accumulator, explicit loop
def fact_iter(n):
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
```

Tracing `fact_recur(4)` — note the stack grows on the way down, and the multiplications happen on the way *back up*:

```
fact_recur(4)                       -> 4 * fact_recur(3)
  fact_recur(3)                     -> 3 * fact_recur(2)
    fact_recur(2)                   -> 2 * fact_recur(1)
      fact_recur(1)                 -> 1          <- base case
    returns 2 * 1  = 2
  returns 3 * 2  = 6
returns 4 * 6  = 24
```

Four stack frames live simultaneously at the deepest point. That is the recursion's real cost: $O(n)$ space,
against $O(1)$ for the loop.

---

### § 4. Common Pitfalls & Invariant Rules
1. **The base case must be reachable from every input.** `if n == 1` looks fine until someone passes `0`, and the
   recursion runs to `-1`, `-2`, ... until `RecursionError`. `if n <= 1` is the safe guard.
2. **`0! = 1`, by definition.** Not zero. Getting this wrong breaks every combinatorics problem downstream.
3. **Recursion depth is $O(n)$ and CPython caps it near 1000.** `factorial_recursive(5000)` raises
   `RecursionError` even though the arithmetic is fine — Python's ints are unbounded, its stack is not.
4. **Every recursive call must strictly shrink the input.** `fact(n)` calling `fact(n)` never terminates; so does
   calling `fact(n - 0)`.
5. **The multiplication happens on unwinding.** Nothing is computed on the way down — which is why this is *not*
   tail recursion in any useful sense, and why the frames must be kept.

---

### § 5. Bridging to LeetCode Mastery
- **The shape transfers, not the function.** Base case plus a strictly-smaller recursive call is the skeleton of
  every tree DFS: `if not node: return 0` is the same guard.
- **LeetCode 104 (Maximum Depth of Binary Tree)**: `1 + max(depth(left), depth(right))` — identical structure.
- **LeetCode 509 (Fibonacci Number)**, **LeetCode 70 (Climbing Stairs)**: the next recurrence up, and the point
  where memoization becomes necessary.
- **Combinatorics problems** need `math.comb` or a factorial table — recursion here is for teaching, not speed.
""",
        "test_cases": [
            {"input": {"n": 5}, "expected": 120},
            {"input": {"n": 0}, "expected": 1},
            {"input": {"n": 1}, "expected": 1},
            {"input": {"n": 10}, "expected": 3628800},
        ],
        "hints": ["Guard with `if n <= 1: return 1`.", "Otherwise return n * factorial_recursive(n - 1)."],
    },
    {
        "slug": "py-modules-files-with",
        "title": "Modules, Files & the with Statement (Guttag Ch. 7)",
        "kind": "fundamental",
        "track": "track_7_testing_exceptions",
        "difficulty": "Easy",
        "category": "Modules & Files",
        "tags": ["MIT 6.0001 Lec 7", "Guttag § 7.1", "Modules", "File IO", "Context Managers"],
        "description": """### Finger Exercise: Qualified Names and Managed Resources
**MIT 6.0001 Citation**: *Chapter 7: Modules and Files (§ 7.1 Modules, § 7.3 Files)*

A **module** is a `.py` file of related definitions. `import m` binds the module object, so its contents are
reached by **fully qualified name** (`m.thing`). A **file handle** must be closed; the **`with` statement`**
guarantees that even when an exception is raised.

Write `parse_records(lines: list[str]) -> list[tuple[str, int]]` that parses `"name,score"` lines into
`(name, score)` pairs, skipping blank lines and any line whose score is not an integer.
""",
        "examples": [
            {"input": "lines = ['ann,90', '', 'bob,x', 'cy,75']", "output": "[('ann', 90), ('cy', 75)]"}
        ],
        "constraints": ["0 <= len(lines) <= 10^4"],
        "starter_codes": {
            "python": """def parse_records(lines: list) -> list:
    # Split on ',', skip blanks and non-integer scores
    pass
"""
        },
        "solutions": {
            "python": """def parse_records(lines: list) -> list:
    out = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) != 2:
            continue
        name, score = parts[0].strip(), parts[1].strip()
        try:
            out.append((name, int(score)))
        except ValueError:
            continue
    return out
"""
        },
        "editorial": """# \U0001f4d6 Chapter 7: Modules and Files
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Splitting and Persisting
Chapter 7 answers two practical questions that Chapters 1–6 deliberately deferred: how do you split a program
across files, and how do you make data outlive the process?

**Modules** answer the first. A module is just a `.py` file containing definitions and statements. `import m`
executes it once and binds the resulting module object to the name `m`. Everything inside is then reached by
**fully qualified name** — `m.pi`, `m.area()`. That qualification is a feature, not friction: it says exactly
where a name came from and makes collisions impossible.

**Files** answer the second, through a **file handle** obtained from `open()`.

---

### § 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 7, § 7.1 and § 7.3 — paraphrase, not a verbatim quotation)*

On modules, Guttag's warning concerns `from m import *`. It dumps every name into the current namespace,
discarding the qualification. Two modules that both define `area` will silently shadow one another, and the
resulting bug points at neither import. Qualified access, or naming what you import, avoids the whole class.

On files, the key vocabulary is the **file handle** — the object `open()` returns, which tracks position within
the file. The modes matter: `'r'` reads, `'w'` **truncates and writes** (destroying existing content), `'a'`
appends. Guttag also flags the **newline character** `\\n` as the line separator that reading preserves and
`strip()` removes.

The `with` statement is the safety mechanism. Written as

```python
with open(path) as f:
    ...
```

it closes the handle when the block exits — **including when an exception propagates out of it**. The manual
`open()` / `close()` pair leaks the handle on any error path between them, which is why `with` is the form to use
unconditionally.

---

### § 3. Canonical Code Walkthrough
```python
# MODULES
import math                 # bind the module
math.sqrt(16)               # fully qualified -- origin is explicit

from math import sqrt       # bind one name
sqrt(16)

# from math import *        # AVOID: dumps every name, invites shadowing

# FILES -- with guarantees the close
with open('scores.txt', 'w') as f:      # 'w' TRUNCATES an existing file
    f.write('ann,90\\n')
    f.write('bob,85\\n')

with open('scores.txt') as f:           # 'r' is the default
    for line in f:                      # iterating a handle yields lines, lazily
        print(line.strip())             # strip() removes the trailing newline

# Equivalent without `with` -- and why it is worse
f = open('scores.txt')
try:
    data = f.read()
finally:
    f.close()          # `with` does exactly this, in one line, unmissably
```

Parsing defensively, which is what the drill exercises:

```python
for raw in lines:
    line = raw.strip()
    if not line:                  # skip blanks
        continue
    parts = line.split(',')
    if len(parts) != 2:           # malformed -- skip rather than crash
        continue
    try:
        out.append((parts[0].strip(), int(parts[1])))
    except ValueError:            # non-numeric score -- skip
        continue
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **`open(path, 'w')` destroys the file immediately**, before you write anything. Use `'a'` to append, and be
   certain which you meant.
2. **Always `with`.** A bare `open()` leaks the handle whenever anything between it and `close()` raises.
3. **Lines keep their `\\n`.** `line == 'ann,90'` fails while `line.strip() == 'ann,90'` succeeds — a classic
   silent parsing bug.
4. **`from m import *` invites shadowing.** Qualify, or import the specific names.
5. **A module runs on first import, once.** Top-level side effects fire then — guard scripts with
   `if __name__ == '__main__':`.
6. **Real input is dirty.** Blank lines, wrong field counts and non-numeric values are the norm; decide per case
   whether to skip or raise.

---

### § 5. Bridging to LeetCode Mastery
- LeetCode passes arguments directly, so file I/O rarely appears — but **competitive judges read stdin**, where
  this exact strip/split/convert discipline applies.
- **The standard library is the real transfer**: `from collections import deque, defaultdict, Counter`,
  `import heapq`, `import bisect`. Knowing what to import is worth more than any single algorithm.
- **`bisect.bisect_left`** is an already-correct binary search — use it instead of rewriting one under pressure.
- **Defensive parsing** is exactly the skill in *String to Integer (atoi)* and *Valid Number*.
""",
        "test_cases": [
            {"input": {"lines": ["ann,90", "", "bob,x", "cy,75"]}, "expected": [["ann", 90], ["cy", 75]]},
            {"input": {"lines": []}, "expected": []},
            {"input": {"lines": ["  spaced , 42 "]}, "expected": [["spaced", 42]]},
            {"input": {"lines": ["too,many,fields", "ok,1"]}, "expected": [["ok", 1]]},
        ],
        "hints": [
            "strip() each line and skip empties.",
            "split(',') and require exactly 2 parts.",
            "Wrap int(score) in try/except ValueError and skip on failure.",
        ],
    },
    {
        "slug": "py-basics-loops-range",
        "title": "while Loops, for Loops & range (Guttag Ch. 2)",
        "kind": "fundamental",
        "track": "track_0_python_basics",
        "difficulty": "Easy",
        "category": "Python Basics",
        "tags": ["MIT 6.0001 Lec 2", "Guttag § 2.4", "Loops", "While", "For", "Range"],
        "description": """### Finger Exercise: Iteration and Its Termination Argument
**MIT 6.0001 Citation**: *Chapter 2: Introduction to Python (§ 2.5 While Loops, § 2.6 For Loops and Range)*

**Iteration** is what lets a fixed-length program do an amount of work that depends on its input. A `while` loop
repeats while a test holds; a `for` loop walks a finite sequence, usually generated by `range`.

Write `first_divisor(n: int) -> int` returning the smallest integer `d` with `2 <= d <= n` that divides `n`
exactly, or `n` itself when `n` is prime. Stop scanning as soon as you find it.
""",
        "examples": [
            {"input": "n = 15", "output": "3"},
            {"input": "n = 13", "output": "13", "explanation": "13 is prime, so its smallest divisor above 1 is itself."},
        ],
        "constraints": ["2 <= n <= 10^6"],
        "starter_codes": {
            "python": """def first_divisor(n: int) -> int:
    # Scan upward from 2; return the first exact divisor, else n
    pass
"""
        },
        "solutions": {
            "python": """def first_divisor(n: int) -> int:
    d = 2
    while d * d <= n:
        if n % d == 0:
            return d
        d += 1
    return n
"""
        },
        "editorial": """# \U0001f4d6 Chapter 2 (§ 2.5 While Loops, § 2.6 For Loops and Range)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Why Loops Change What Programs Can Do
A straight-line program executes each statement once, so the work it does is fixed by its source length. A
branching program adds decisions but still cannot repeat. **Iteration** removes that ceiling: a few lines can now
do work proportional to the input.

Guttag pairs iteration with the obligation it creates. A loop that never stops is not a program, so every `while`
loop needs a **decrementing function** — a non-negative integer measure of the state that strictly decreases each
pass. When it hits zero, the loop exits. This is the same argument he later reuses to prove binary search
terminates.

A `for` loop needs no such argument: it walks a finite sequence, so termination is structural.

---

### § 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 2, § 2.5–2.6 — paraphrase, not a verbatim quotation)*

Guttag introduces `while` first because it is the general form, then `for` as the common special case. `range` is
what makes `for` numeric: `range(start, stop, step)` produces values from `start` up to **but not including**
`stop`. He is careful that `range` does not build a list — it generates values on demand, so `range(10**9)` costs
no memory.

`break` exits the innermost enclosing loop immediately, skipping any remaining iterations. Guttag's caution is
that `break` interacts with the loop's exit reasoning: after a `break` you can no longer assume the loop
condition became false, so any code depending on "the loop ran to completion" must be guarded.

The half-open convention of `range` — inclusive start, exclusive stop — is deliberate: it makes `range(len(L))`
exactly the valid indices of `L`, and makes adjacent ranges tile without overlap or gap.

---

### § 3. Canonical Code Walkthrough
```python
# WHILE -- general form; needs an explicit termination argument
d = 2
while d * d <= n:          # decrementing function: n - d*d, shrinks as d grows
    if n % d == 0:
        return d           # early exit the moment we succeed
    d += 1
return n

# FOR + range -- termination is structural
for i in range(5):         # 0, 1, 2, 3, 4   -- 5 is EXCLUDED
    ...
for i in range(2, 10, 3):  # 2, 5, 8
    ...
for i in range(len(L) - 1, -1, -1):    # walk backwards: len-1 down to 0
    ...

# range does not materialize
r = range(10**9)           # instant, O(1) memory
len(r)                     # 1000000000
```

Why `d * d <= n` and not `d <= n`: divisors come in pairs. If `n = a * b` with `a <= b`, then
`a <= sqrt(n)`. So the smallest non-trivial divisor, if one exists, is at or below the square root — scanning
past it is wasted work. That turns $O(n)$ into $O(\\sqrt{n})$: for `n = 10^6`, 1000 iterations instead of a million.

Tracing `first_divisor(15)`:

```
d = 2:  2*2 = 4  <= 15,  15 % 2 = 1   -> continue
d = 3:  3*3 = 9  <= 15,  15 % 3 = 0   -> return 3
```

And `first_divisor(13)`:

```
d = 2:  4  <= 13,  13 % 2 = 1  -> continue
d = 3:  9  <= 13,  13 % 3 = 1  -> continue
d = 4:  16 > 13   -> loop test fails, fall through
return 13    (prime)
```

---

### § 4. Common Pitfalls & Invariant Rules
1. **Forgetting to advance the loop variable** is the classic infinite `while`. If `d += 1` is missing, nothing
   decrements and the loop never ends.
2. **`range(stop)` excludes `stop`.** `range(1, 5)` is `1,2,3,4`. Off-by-one here is the most common beginner bug.
3. **Counting down needs all three arguments.** `range(n, -1, -1)` — omit the `-1` stop and you never reach 0.
4. **Never mutate a list while iterating it.** The hidden loop counter and the shifting list disagree — see the
   aliasing drill.
5. **`break` skips the `else` clause.** Python's `for...else` runs `else` only when the loop was *not* broken —
   useful for search, and surprising if unknown.
6. **Prefer `for x in L` over `for i in range(len(L))`** unless you genuinely need the index; use `enumerate`
   when you need both.

---

### § 5. Bridging to LeetCode Mastery
- **The $\\sqrt{n}$ divisor bound** is the whole trick in *Count Primes*, *Happy Number* and *Perfect Squares*.
- **Reverse iteration** `range(n-1, -1, -1)` drives suffix DP and in-place array shifting.
- **Two pointers and sliding window** are both `while` loops whose termination argument is that an index strictly
  advances — write that argument down when the loop looks suspicious.
- **`while` over `for`** whenever the step is data-dependent rather than a fixed count.
""",
        "test_cases": [
            {"input": {"n": 15}, "expected": 3},
            {"input": {"n": 13}, "expected": 13},
            {"input": {"n": 2}, "expected": 2},
            {"input": {"n": 49}, "expected": 7},
            {"input": {"n": 1000000}, "expected": 2},
        ],
        "hints": [
            "Start d at 2 and loop while d * d <= n.",
            "Return d as soon as n % d == 0; if the loop finishes, n is prime so return n.",
        ],
    },
    {
        "slug": "py-basics-string-indexing-slicing",
        "title": "String Indexing & Slicing (Guttag Ch. 2)",
        "kind": "fundamental",
        "track": "track_0_python_basics",
        "difficulty": "Easy",
        "category": "Python Basics",
        "tags": ["MIT 6.0001 Lec 2", "Guttag § 2.3", "Strings", "Indexing", "Slicing"],
        "description": """### Finger Exercise: Half-Open Slices
**MIT 6.0001 Citation**: *Chapter 2: Introduction to Python (§ 2.4 Strings and Input)*

**Indexing** selects one character; **slicing** selects a range, `s[start:end]`, including `start` and
**excluding** `end`. Negative indices count from the right, so `s[-1]` is the last character.

Write `extract_middle(s: str) -> str` returning `s` with its first and last characters removed. Strings of
length 2 or less return the empty string.
""",
        "examples": [
            {"input": "s = 'python'", "output": "'ytho'"},
            {"input": "s = 'ab'", "output": "''"},
        ],
        "constraints": ["0 <= len(s) <= 10^4"],
        "starter_codes": {
            "python": """def extract_middle(s: str) -> str:
    # Slice away the first and last characters
    pass
"""
        },
        "solutions": {
            "python": """def extract_middle(s: str) -> str:
    if len(s) <= 2:
        return ""
    return s[1:-1]
"""
        },
        "editorial": """# \U0001f4d6 Chapter 2 (§ 2.4 Strings and Input)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: A String Is a Sequence
A `str` is an ordered sequence of characters, and Guttag introduces it as the first type with internal structure
worth addressing. Two operations follow from that: **indexing** picks out one element, **slicing** picks out a
contiguous run.

The convention that governs both is **half-open**: `s[i:j]` includes index `i` and excludes index `j`. Two
properties fall out of it, and they are why the convention was chosen:

- The length of `s[i:j]` is exactly `j - i`.
- `s[:k]` and `s[k:]` partition the string perfectly — no overlap, no gap, for any `k`.

Guttag also introduces the **overloaded operator** here: `+` means addition on numbers and *concatenation* on
strings, and `*` means multiplication or **repetition**. Same symbol, type-dependent meaning.

---

### § 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 2, § 2.4 — paraphrase, not a verbatim quotation)*

Indices run from `0` to `len(s) - 1`. Negative indices count backwards from the end, `-1` being the last
character — so `s[-1]` avoids the noisier `s[len(s) - 1]`.

Slicing takes an optional third value, the step: `s[::2]` takes every second character and `s[::-1]` walks the
string backwards, which is the idiomatic reverse.

The property Guttag stresses hardest is that strings are **immutable**. `s[0] = 'x'` raises `TypeError`. Every
operation that appears to modify a string in fact returns a new one, leaving the original untouched. To change a
character you convert to a list, mutate, and `join` back.

Out-of-range *indexing* raises `IndexError`; out-of-range *slicing* silently clamps. `'abc'[5]` is an error,
`'abc'[1:99]` is `'bc'`. That asymmetry is deliberate and worth memorizing — it is why slice-based code so often
fails quietly rather than loudly.

---

### § 3. Canonical Code Walkthrough
```python
s = 'python'
#    p  y  t  h  o  n
#    0  1  2  3  4  5      forward
#   -6 -5 -4 -3 -2 -1      backward

s[0]        # 'p'
s[-1]       # 'n'          last character
s[1:4]      # 'yth'        indices 1,2,3 -- 4 EXCLUDED, length 4-1 = 3
s[:3]       # 'pyt'        start defaults to 0
s[3:]       # 'hon'        end defaults to len(s)
s[:]        # 'python'     a full copy
s[1:-1]     # 'ytho'       drop first and last -- the drill
s[::-1]     # 'nohtyp'     reversed
s[::2]      # 'pto'        every second character

len(s)      # 6
'y' in s    # True         substring test

# Immutability
# s[0] = 'P'          # TypeError
s.replace('p', 'P')   # 'Python'  -- a NEW string; s is unchanged

# Out-of-range: indexing raises, slicing clamps
# s[99]               # IndexError
s[2:99]               # 'thon'    -- no error
s[99:]                # ''        -- empty, still no error
```

Why the guard in the drill matters — the clamping is what makes it necessary:

```python
'ab'[1:-1]    # ''   correct by luck
'a'[1:-1]     # ''   correct by luck
''[1:-1]      # ''   correct by luck
```

Here the slice happens to give the right answer, but relying on clamping to handle your edge cases is fragile —
state the length condition explicitly so the intent is visible.

---

### § 4. Common Pitfalls & Invariant Rules
1. **The end index is excluded.** `s[0:len(s)]` is the whole string; `s[0:len(s)-1]` quietly drops the last
   character.
2. **Slicing never raises, indexing does.** A bad slice returns something plausible and wrong; a bad index stops
   the program. Silent is worse.
3. **`s[:]` copies.** On a string that is harmless; on a list it is the standard shallow clone.
4. **`s[::-1]` is $O(n)$ and allocates.** Fine once, quadratic inside a loop.
5. **Every "modification" allocates.** Building a string with `+=` in a loop is $\\Theta(n^2)$ — collect into a
   list and `''.join(...)` once.
6. **`s[1:-1]` on short strings yields `''`, not an error** — check the length when the distinction matters.

---

### § 5. Bridging to LeetCode Mastery
- **LeetCode 125 (Valid Palindrome)**, **344 (Reverse String)**: index from both ends rather than slicing, to
  stay $O(1)$ in space.
- **LeetCode 5 (Longest Palindromic Substring)**: expand around a centre with indices; slicing inside the loop
  turns it quadratic.
- **LeetCode 3 (Longest Substring Without Repeating Characters)**: the window is a pair of indices, never a slice.
- **General rule**: pass `(left, right)` indices through recursion instead of `s[1:-1]`, and an $O(n^2)$ solution
  becomes $O(n)$.
""",
        "test_cases": [
            {"input": {"s": "python"}, "expected": "ytho"},
            {"input": {"s": "ab"}, "expected": ""},
            {"input": {"s": ""}, "expected": ""},
            {"input": {"s": "abc"}, "expected": "b"},
        ],
        "hints": ["Return '' when len(s) <= 2.", "Otherwise s[1:-1] drops the first and last characters."],
    },
    {
        "slug": "py-ds-inheritance-substitution",
        "title": "Inheritance & the Substitution Principle (Guttag Ch. 10)",
        "kind": "fundamental",
        "track": "track_2_data_structures",
        "difficulty": "Medium",
        "category": "Abstract Data Types",
        "tags": ["MIT 6.0001 Lec 9", "MIT 6.0001 Pset 5", "Inheritance", "Liskov Substitution"],
        "description": """### Finger Exercise: A Subclass Must Be Usable as Its Superclass
**MIT 6.0001 Citation**: *Chapter 10 (§ 10.2 Inheritance, § 10.2.2 The Substitution Principle)*

**Inheritance** builds a type hierarchy: a subclass inherits its superclass's attributes and methods, and may
add or **override** them. The **substitution principle** constrains what an override may do — anywhere the
superclass works, the subclass must work too.

Write `describe_shapes(specs: list[tuple[str, float]]) -> list[str]` where each spec is `(kind, size)` with
`kind` in `"square"` / `"circle"`. Define a `Shape` base class with an `area()` method, override it in two
subclasses, and return `"kind:area"` strings with the area rounded to 2 decimals.
""",
        "examples": [
            {"input": "specs = [('square', 2), ('circle', 1)]", "output": "['square:4.0', 'circle:3.14']"}
        ],
        "constraints": ["0 <= len(specs) <= 500", "size > 0"],
        "starter_codes": {
            "python": """def describe_shapes(specs: list) -> list:
    class Shape:
        def area(self) -> float:
            raise NotImplementedError

    # Define Square and Circle subclasses overriding area()
    pass
"""
        },
        "solutions": {
            "python": """def describe_shapes(specs: list) -> list:
    import math

    class Shape:
        def __init__(self, size):
            self.size = size

        def area(self) -> float:
            raise NotImplementedError

        def describe(self) -> str:
            return self.name + ":" + str(round(self.area(), 2))

    class Square(Shape):
        name = "square"

        def area(self) -> float:
            return float(self.size ** 2)

    class Circle(Shape):
        name = "circle"

        def area(self) -> float:
            return math.pi * self.size ** 2

    kinds = {"square": Square, "circle": Circle}
    return [kinds[k](sz).describe() for k, sz in specs]
"""
        },
        "editorial": """# \U0001f4d6 Chapter 10 (§ 10.2 Inheritance)
*MIT 6.0001: Introduction to Computer Science and Programming in Python (Profs. John Guttag, Eric Grimson, Ana Bell — MIT Press Companion Text)*

---

### § 1. Theoretical Foundations: Hierarchies of Types
Inheritance lets one class be defined as a specialization of another. The subclass gets everything the superclass
has, and may **add** new attributes or **override** existing methods. The relation it expresses is *is-a*: a
`Square` **is a** `Shape`.

Guttag's own worked hierarchy runs `Person` → `MIT_person` → `Student` → `UG`, adding capability at each level.
The payoff is **polymorphism**: code written against `Shape` works unchanged on any subclass, because dispatch
happens on the actual object at call time.

Note the design point from Chapter 14: Guttag makes `Graph` a subclass of `Digraph`, not the reverse — an
undirected graph *is* a digraph in which every edge exists both ways. The direction of the hierarchy is a claim
about substitutability, and it has to be defensible.

---

### § 2. Reconstructed Reading
*(Reconstructed from Guttag, Chapter 10, § 10.2 and § 10.2.2 — paraphrase, not a verbatim quotation)*

When a method is called on an instance, Python looks for it on the object's class first, and only then walks up
the chain of superclasses. The first definition found wins — that is what makes overriding work, and it is why
a subclass method with the same name silently replaces the inherited one.

§ 10.2.2 states the rule that keeps hierarchies honest. The **substitution principle** says that wherever an
instance of the superclass is expected, an instance of any subclass must be acceptable. Concretely: an override
may **weaken** what it demands of callers and **strengthen** what it guarantees, but never the reverse. A
subclass that requires more, or delivers less, breaks code that was written correctly against the superclass —
and it breaks it silently, at a call site that never mentions the subclass.

Guttag's practical caution is that inheritance couples the subclass to the superclass's implementation, not just
its interface. Change the parent and every child may break. Where an *is-a* relation is not genuinely present,
**composition** — holding an instance rather than deriving from it — keeps the coupling narrow.

---

### § 3. Canonical Code Walkthrough
```python
import math

class Shape:                          # the abstraction
    def __init__(self, size):
        self.size = size

    def area(self):
        raise NotImplementedError     # subclasses MUST override

    def describe(self):               # inherited unchanged by both subclasses
        return f"{self.name}:{round(self.area(), 2)}"

class Square(Shape):
    name = "square"
    def area(self):                   # OVERRIDE
        return float(self.size ** 2)

class Circle(Shape):
    name = "circle"
    def area(self):                   # OVERRIDE
        return math.pi * self.size ** 2
```

Polymorphism in action — `describe` was written once, on `Shape`, and calls whichever `area` the object actually
has:

```python
shapes = [Square(2), Circle(1)]
[s.describe() for s in shapes]        # ['square:4.0', 'circle:3.14']

isinstance(Square(2), Shape)          # True  -- respects the hierarchy
type(Square(2)) is Shape              # False -- exact type, rejects subclasses
```

`describe` never branches on kind. Adding a `Triangle` requires no change to it at all — that is the whole return
on the hierarchy.

---

### § 4. Common Pitfalls & Invariant Rules
1. **Overriding `__init__` without calling `super().__init__()`** leaves the superclass's attributes unset, so
   inherited methods fail on a half-built object.
2. **The substitution principle is directional.** An override may accept *more* inputs and promise *more* about
   its output. Narrowing what it accepts, or weakening its guarantee, breaks existing callers.
3. **`isinstance` respects the hierarchy; `type(x) is C` does not.** Prefer `isinstance` unless you deliberately
   want to exclude subclasses.
4. **Deep hierarchies are a liability.** Each level adds coupling. Guttag's own examples stay shallow.
5. **Prefer composition when the relation is *has-a*.** LRU Cache *has* a dict and *has* a linked list; it is
   neither.
6. **`raise NotImplementedError` documents an abstract method** and fails loudly if a subclass forgets it — far
   better than returning `None` and corrupting a result downstream.

---

### § 5. Bridging to LeetCode Mastery
- Rare in algorithm rounds, **central in design rounds** — modelling a type hierarchy is the common ask.
- **LeetCode 341 (Flatten Nested List Iterator)**: implement an interface someone else defined.
- **LeetCode 146 (LRU Cache)**: the counterexample — composition, not inheritance.
- **Custom exception classes** subclass `Exception`, the same mechanism in a different setting.
""",
        "test_cases": [
            {"input": {"specs": [["square", 2], ["circle", 1]]}, "expected": ["square:4.0", "circle:3.14"]},
            {"input": {"specs": []}, "expected": []},
            {"input": {"specs": [["square", 3]]}, "expected": ["square:9.0"]},
        ],
        "hints": [
            "Give Shape an __init__ storing size, and an area() that raises NotImplementedError.",
            "Square.area returns size ** 2; Circle.area returns math.pi * size ** 2.",
            "Round to 2 decimals and join with ':'.",
        ],
    },
]

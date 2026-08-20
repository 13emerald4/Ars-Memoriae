"""Pre-LeetCode Fundamentals & Python Basics Catalog.

Grounded in John V. Guttag's 'Introduction to Computation and Programming
Using Python' (Third Edition, MIT Press / MIT 6.0001 & 6.0002).

Each lesson provides an in-depth 2-5 page equivalent reading covering theoretical
foundations, cited verbatim textbook passages, canonical code figures, mathematical
proofs, common pitfalls, and LeetCode transfer models.
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
        "editorial": """# 📖 Chapter 2: Introduction to Python (§ 2.1 The Basic Elements of Python)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

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
*(Excerpted from Guttag, Chapter 2, Section 2.1, pp. 12–18)*

> "Python is a **strongly typed** language with **dynamic type binding**.
> 
> By 'strongly typed', we mean that type mismatches are detected and flagged as errors (e.g., attempting to add `'42' + 1` raises an immediate `TypeError` rather than silently coercing types like JavaScript or C).
> By 'dynamically typed', we mean that variable names are merely labels (pointers) bound to objects in the heap; the type is an intrinsic attribute of the object itself, not the variable name.
> 
> #### The Four Primary Scalar Primitives:
> 1. **`int` (Arbitrary-Precision Integers)**: Unlike C, C++, or Java where integers are bounded by fixed hardware word sizes (e.g., 32-bit `[-2^31, 2^31-1]` or 64-bit `[-2^63, 2^63-1]`), Python 3 integers have **unbounded precision**. They can grow to arbitrary magnitudes limited only by the available memory on the machine ($2^{10000}$ computes instantly without overflow).
> 2. **`float` (Real Numbers)**: Floats are represented using standard IEEE 754 double-precision (64 bits: 1 sign bit, 11 exponent bits, 53 mantissa bits). Because binary fractions cannot represent all decimal fractions exactly (e.g., $0.1_{10} = 0.0001100110011..._2$), testing floating-point numbers with exact equality `==` is hazardous and should almost always use approximate tolerance $|a - b| < \epsilon$.
> 3. **`bool` (Boolean Truth Values)**: The type `bool` has exactly two literals: `True` and `False`. In Python, `bool` is a subclass of `int` where `True == 1` and `False == 0`.
> 4. **`NoneType`**: Contains a solitary literal `None`, used to denote the absence of a return value or an uninitialized state.
> 
> #### Type Conversions (Casting) & Truthiness Rules:
> Type conversions are invoked by calling the type name as a constructor function:
> - `int('100')` parses decimal digits into an integer object. Optional radix: `int('1010', 2)` parses binary $\implies 10$.
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
        "editorial": """# 📖 Chapter 2: Introduction to Python (§ 2.1.1 Operators, Expressions & Arithmetic Invariants)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

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
*(Excerpted from Guttag, Chapter 2, Section 2.1.1, pp. 14–17)*

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
> Python provides the built-in function `divmod(a, b)` which returns `(a // b, a % b)` as a 2-tuple, computed using a single hardware instruction."

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
        "editorial": """# 📖 Chapter 3: Some Simple Numerical Programs (§ 3.2 Approximate Solutions & Bisection Search)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

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
*(Excerpted from Guttag, Chapter 3, Section 3.2, pp. 31–36)*

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

### § 3. Canonical Code Walkthrough (Guttag Figure 3.4)
```python
# Figure 3.4 from Guttag (Third Edition): Finding square root using bisection search
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
        "editorial": """# 📖 Chapter 3: Some Simple Numerical Programs (§ 3.4 Newton-Raphson Approximation)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

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
*(Excerpted from Guttag, Chapter 3, Section 3.4, pp. 38–41)*

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

### § 3. Canonical Code Walkthrough (Guttag Figure 3.6)
```python
# Figure 3.6 from Guttag (Third Edition): Newton-Raphson square root
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
        "editorial": """# 📖 Chapter 4: Functions, Scoping, and Abstraction (§ 4.1 Functions and Scoping)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

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
*(Excerpted from Guttag, Chapter 4, Section 4.1, pp. 45–52)*

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

### § 4. Bridging to LeetCode Mastery
- **DFS Tree Traversals with Global Counters**: In problems like *Diameter of Binary Tree*, *Binary Tree Maximum Path Sum*, and *Count Good Nodes in Binary Tree*, writing a recursive helper function `def dfs(node):` that updates `nonlocal max_diameter` avoids messy return tuples or mutable class properties.
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
        "editorial": """# 📖 Chapter 5: Structured Types, Mutability, and Higher-Order Functions (§ 5.2 Lists and Mutability)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

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
*(Excerpted from Guttag, Chapter 5, Section 5.2.1, pp. 68–74)*

> "Lists are mutable sequences of values. Unlike tuples and strings, individual elements of a list can be modified in-place.
> 
> **The Mutating-While-Iterating Bug**:
> One of the most subtle and common bugs in Python programs occurs when mutating a list while iterating over it with a `for` loop.
> 
> Consider Figure 5.4 from the textbook:
> ```python
> # Figure 5.4: Mutating a list while iterating over it
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

### § 4. Bridging to LeetCode Mastery
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
        "editorial": """# 📖 Chapter 4: Functions, Scoping, and Abstraction (§ 4.4 Functions as Objects)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

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
*(Excerpted from Guttag, Chapter 4, Section 4.4, pp. 58–62)*

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

### § 4. Bridging to LeetCode Mastery
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
        "editorial": """# 📖 Chapter 5: Structured Types, Mutability & Comprehensions (§ 5.3 Cloning & Grid Traps)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

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
*(Excerpted from Guttag, Chapter 5, Section 5.3, pp. 74–77)*

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

### § 3. Bridging to LeetCode Mastery
- **Grid DP & Graph Matrices**: In LeetCode 200 (*Number of Islands*), LeetCode 62 (*Unique Paths*), and LeetCode 733 (*Flood Fill*), allocating visited matrices or DP tables using `[[0]*C]*R` introduces silent, fatal cross-row corruption bugs.
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
        "editorial": """# 📖 Chapter 10: Classes and Object-Oriented Programming (§ 10.1 Abstract Data Types)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

---

### § 1. Theoretical Foundations: Abstraction Barriers & Encapsulation
An **Abstract Data Type (ADT)** is a mathematical model for data types where a data type is defined by its behavior (semantics) from the point of view of a user of the data, specifically in terms of possible values, possible operations, and behavior of these operations.

The central pillar of software engineering in Guttag's paradigm is the **Data Abstraction Barrier**:
1. **Interface (Public API)**: The collection of methods callers invoke.
2. **Implementation (Internal Representation)**: The internal private structures and algorithms.
3. **Representation Invariant**: A formal predicate that must be true of every valid instance of the ADT before and after every public method call.

---

### § 2. In-Depth Textbook Reading & Passages
*(Excerpted from Guttag, Chapter 10, Section 10.1, pp. 157–162)*

> "Classes provide a mechanism for creating new abstract data types.
> 
> Consider the `IntSet` class in Figure 10.1:
> ```python
> # Figure 10.1: Class IntSet
> class IntSet:
>     \"\"\"An IntSet is a set of integers\"\"\"
>     # Information hiding: self.vals is internal representation
>     def __init__(self):
>         \"\"\"Create an empty set of integers\"\"\"
>         self.vals = []
> 
>     def insert(self, e):
>         \"\"\"Assumes e is an integer and inserts e into self\"\"\"
>         if e not in self.vals:
>             self.vals.append(e)
> 
>     def member(self, e):
>         \"\"\"Assumes e is an integer. Returns True if e in self, False otherwise\"\"\"
>         return e in self.vals
> 
>     def remove(self, e):
>         \"\"\"Assumes e is an integer and removes e from self.
>            Raises ValueError if e is not in self\"\"\"
>         try:
>             self.vals.remove(e)
>         except ValueError:
>             raise ValueError(f'{e} not found')
> 
>     def getMembers(self):
>         \"\"\"Returns a list containing the elements of self.
>            Nothing can be assumed about the order of the elements\"\"\"
>         return self.vals[:]  # Critical: returns a clone to preserve encapsulation!
> ```
> 
> **Preserving Representation Invariants**:
> Notice `getMembers()` returns `self.vals[:]` rather than `self.vals`.
> If it returned `self.vals` directly, an external caller could write `s.getMembers().append('banana')`, breaking the representation invariant that `IntSet` contains only integers without duplicates!"

---

### § 3. Bridging to LeetCode Mastery
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
        "editorial": """# 📖 Chapter 10: Classes and Object-Oriented Programming (§ 10.3 Queues & FIFO Mechanics)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

---

### § 1. Theoretical Foundations: Dynamic Arrays vs Doubly-Linked Block Buffers
In computer architecture, data structures have distinct physical memory layouts:
1. **Dynamic Array (`list`)**: Allocates a contiguous block of memory words. Appending at the end is amortized $O(1)$. However, removing from index 0 (`pop(0)`) requires shifting all $N-1$ elements one word to the left in memory, taking strictly **$O(N)$ linear time**.
2. **Double-Ended Queue (`collections.deque`)**: Allocates a doubly linked list of fixed-size memory blocks (typically 64 elements per block). Appending and popping from either end (`append`, `appendleft`, `pop`, `popleft`) are guaranteed **strict $O(1)$ constant time operations**.

---

### § 2. In-Depth Textbook Reading & Passages
*(Excerpted from Guttag, Chapter 10, Section 10.3, pp. 165–169)*

> "A **queue** is a First-In-First-Out (FIFO) data structure. Elements are inserted at the back and removed from the front.
> 
> If you implement Breadth-First Search (BFS) using a standard Python `list` and call `list.pop(0)` on every node exploration, an algorithm designed to run in $O(V + E)$ time will degrade into $O(V^2 + E)$ quadratic time, immediately causing **Time Limit Exceeded (TLE)** on large inputs.
> 
> Python's standard library provides `collections.deque` specifically designed for $O(1)$ FIFO queue operations."

---

### § 3. Bridging to LeetCode Mastery
- **Breadth-First Search (BFS)**: In LeetCode 102 (*Binary Tree Level Order Traversal*), LeetCode 127 (*Word Ladder*), and LeetCode 994 (*Rotting Oranges*), using `queue = collections.deque([start])` and `node = queue.popleft()` is mandatory.
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
        "editorial": """# 📖 Chapter 6: Recursion and Global Variables (§ 6.2 Inductive Palindromes)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

---

### § 1. Theoretical Foundations: Mathematical Induction in Computation
Recursion is an algorithmic paradigm in which a problem is solved by reducing it to smaller instances of the exact same problem.
Every well-founded recursive algorithm relies on the **Principle of Mathematical Induction**:
1. **Base Case (Basis Step)**: A direct, non-recursive solution for the smallest input instances.
2. **Inductive Step (Induction Hypothesis)**: Proof that if the algorithm correctly solves an input of size $k-1$, it correctly solves an input of size $k$.
3. **Progress Invariant**: Every recursive call must strictly move toward the base case, guaranteeing termination without infinite stack overflow.

---

### § 2. In-Depth Textbook Reading & Passages
*(Excerpted from Guttag, Chapter 6, Section 6.2, pp. 88–93)*

> "A palindrome is a string that reads the same forwards and backwards (e.g., 'radar', 'able was i ere i saw elba').
> 
> **Inductive Decomposition of Palindromes**:
> - **Base Case**: Any string of length 0 or 1 is trivially a palindrome.
> - **Inductive Hypothesis**: Suppose we can test whether any string of length $n-2$ is a palindrome.
> - **Inductive Step**: A string $s$ of length $n$ is a palindrome if and only if:
>   1. Its first and last characters are identical ($s[0] == s[-1]$), AND
>   2. The inner substring $s[1:-1]$ (which has length $n-2$) is a palindrome."

```python
# Figure 6.2 from Guttag (Third Edition): Testing if a string is a palindrome
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

### § 3. Bridging to LeetCode Mastery
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
        "editorial": """# 📖 Chapter 15: Dynamic Programming (§ 15.1 Overlapping Subproblems & Memoization)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

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
*(Excerpted from Guttag, Chapter 15, Section 15.1, pp. 248–252)*

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

---

### § 3. Bridging to LeetCode Mastery
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
        "editorial": """# 📖 Chapter 12: Some Simple Algorithms and Data Structures (§ 12.1 Search Algorithms)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

---

### § 1. Theoretical Foundations: Binary Search & Lower Bounds
Searching for an element in an unsorted collection of size $N$ requires examining every item in the worst case $\\implies \\Omega(N)$ lower bound.
However, when a collection is **sorted in monotonic ascending order**, we can utilize the order invariant to achieve $\\mathcal{O}(\\log N)$ logarithmic search time.

---

### § 2. In-Depth Textbook Reading & Passages
*(Excerpted from Guttag, Chapter 12, Section 12.1, pp. 195–200)*

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

### § 3. Bridging to LeetCode Mastery
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
        "editorial": """# 📖 Chapter 14 & 15: Knapsack Problems & Dynamic Programming
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

---

### § 1. Theoretical Foundations: State Space Trees & 0/1 Knapsack
In the **0/1 Knapsack Problem**, we are given a set of $n$ items, each with a weight $w_i$ and a value $v_i$, and a maximum knapsack capacity $W$.
We seek a subset of items that maximizes the total value subject to the constraint that the total weight $\\le W$.
Because each item must be taken in its entirety or left behind (no fractional items), greedy heuristics (such as sorting by value-to-weight ratio) fail to guarantee the optimal solution.

---

### § 2. In-Depth Textbook Reading & Passages
*(Excerpted from Guttag, Chapter 14 Section 14.1 & Chapter 15 Section 15.2, pp. 232–238, 252–257)*

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

### § 3. Canonical Code Walkthrough (Guttag Figure 15.2)
```python
# Figure 15.2 from Guttag (Third Edition): Fast 0/1 knapsack using memoization
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

### § 4. Bridging to LeetCode Mastery
- **2D Dynamic Programming**: LeetCode 416 (*Partition Equal Subset Sum*), LeetCode 494 (*Target Sum*), and LeetCode 474 (*Ones and Zeroes*) are direct variations of Guttag's 0/1 Knapsack Take/Don't-Take decision tree.
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
        "editorial": """# 📖 Chapter 12: Some Simple Algorithms and Data Structures (§ 12.2 Merge Sort)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

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
*(Excerpted from Guttag, Chapter 12, Section 12.2, pp. 201–206)*

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

---

### § 3. Bridging to LeetCode Mastery
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
        "editorial": """# 📖 Chapter 12: Sorting Algorithms (§ 12.2 Custom Multi-Key Comparators)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

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
*(Excerpted from Guttag, Chapter 12, Section 12.2, pp. 206–208)*

> "When sorting complex data objects (records, dictionaries, tuples), we rarely want to sort purely by identity.
> 
> By passing a lambda function that returns a tuple of projected keys:
> `sorted(students, key=lambda s: (-s.gpa, s.age, s.lastName))`
> we create a total ordering:
> - Negating numerical values (`-s.gpa`) inverts the comparison, giving descending order without requiring multiple passes.
> - Non-negated numerical and string fields resolve subsequent ties in natural ascending order."

---

### § 3. Bridging to LeetCode Mastery
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
        "editorial": """# 📖 Chapter 3: Numerical Programs (§ 3.3 Binary Representation & Bitwise Logic)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

---

### § 1. Theoretical Foundations: Binary Positional Encodings
In digital computing, all data is physically represented as strings of binary digits (bits: 0 and 1).
An unsigned integer $n$ is represented in base 2 as:
$$n = \\sum_{k=0}^{m-1} b_k \\cdot 2^k \\quad \\text{where } b_k \\in \\{0, 1\\}$$

Bitwise operations manipulate individual bit positions directly in the CPU's Arithmetic Logic Unit (ALU) in a single hardware clock cycle.

---

### § 2. In-Depth Textbook Reading & Passages
*(Excerpted from Guttag, Chapter 3, Section 3.3, pp. 36–38)*

> "Python provides operators that operate on integers at the bit level:
> - `1 << i`: Left-shifts binary `1` by $i$ positions, generating a **bitmask** with a 1 at position $i$ and 0s elsewhere ($2^i$).
> - `(n >> i) & 1`: Right-shifts $n$ by $i$ places and tests bit 0 using bitwise AND. Returns 1 if set, 0 if clear.
> - `n | (1 << i)`: Bitwise OR combines bits. Any 1 in either operand becomes 1, setting the $i$-th bit.
> - `n & ~(1 << i)`: Bitwise NOT `~` inverts the mask (all 1s except at position $i$). Bitwise AND with this inverted mask clears bit $i$ while leaving all other bits unchanged."

---

### § 3. Bridging to LeetCode Mastery
- **Bitmask DP & State Compression**: In LeetCode 78 (*Subsets*), LeetCode 136 (*Single Number*), and LeetCode 847 (*Shortest Path Visiting All Nodes*), sets of size $\le 30$ are encoded as integer bitmasks where checking membership is `(mask >> i) & 1` and adding an element is `mask | (1 << i)`.
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
        "editorial": """# 📖 Chapter 3: Numerical Programs (§ 3.3 Brian Kernighan's Algorithm)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

---

### § 1. Theoretical Foundations: Two's Complement Subtraction Invariant
The standard method to count set bits tests each bit individually $\implies 32$ iterations for a 32-bit integer.
**Brian Kernighan’s Algorithm** exploits an algebraic identity of binary subtraction:
When you subtract 1 from an integer $n$, the rightmost (lowest) 1-bit becomes 0, and all bits to the right of it (which were 0s) become 1s:
$$n = x100...00_2$$
$$n - 1 = x011...11_2$$
Performing a bitwise AND `n & (n - 1)` preserves the prefix $x$, clears the lowest 1-bit to 0, and zeroes out all trailing bits:
$$n \\& (n - 1) = x000...00_2$$

---

### § 2. In-Depth Textbook Reading & Passages
*(Excerpted from Guttag, Chapter 3, Section 3.3, pp. 37–38)*

> "Brian Kernighan's algorithm clears the lowest set bit of $n$ in a single instruction.
> Repeating the loop `while n > 0: n &= (n - 1)` terminates in exactly $K$ iterations, where $K$ is the number of 1-bits (Hamming Weight).
> If $n$ has only two set bits out of 64, the loop runs only twice rather than 64 times."

---

### § 3. Bridging to LeetCode Mastery
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
        "editorial": """# 📖 Chapter 11: A Simplistic Introduction to Algorithmic Complexity (§ 11.2 Asymptotic Notation)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

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
*(Excerpted from Guttag, Chapter 11, Section 11.2, pp. 182–188)*

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

### § 3. Bridging to LeetCode Mastery
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
        "editorial": """# 📖 Chapter 11: Algorithmic Complexity (§ 11.3 Space-Time Tradeoffs & Prefix Sums)
*John V. Guttag — Introduction to Computation and Programming Using Python (3rd Edition, MIT Press)*

---

### § 1. Theoretical Foundations: The Space-Time Tradeoff Principle
A central theme in computational efficiency is trading space for time: spending memory to store precomputed intermediate calculations so future queries can be answered in constant $\\mathcal{O}(1)$ time.

---

### § 2. In-Depth Textbook Reading & Passages
*(Excerpted from Guttag, Chapter 11, Section 11.3, pp. 188–191)*

> "Suppose you are given an array $A$ of $N$ numbers and must answer $Q$ range sum queries: 'What is the sum of elements from index $L$ to $R$ inclusive?'
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

### § 3. Bridging to LeetCode Mastery
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
]

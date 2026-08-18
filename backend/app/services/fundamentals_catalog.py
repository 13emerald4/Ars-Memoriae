"""Pre-LeetCode Fundamentals & Python Basics Catalog.

Provides 35+ micro-drills categorized across 7 tracks to build cognitive
automaticity on Python primitives, data structure mechanics, and algorithmic boilerplate.
"""

from __future__ import annotations

FUNDAMENTALS_CATALOG = [
    # ── Track 0: Python Basics & Core Language Primitives ─────────────────────
    {
        "slug": "py-basics-type-casting",
        "title": "Type Casting & Conversions",
        "kind": "fundamental",
        "track": "track_0_python_basics",
        "difficulty": "Easy",
        "category": "Python Basics",
        "tags": ["Python Basics", "Types", "Type Casting"],
        "description": """Write a function `convert_types(val_str: str, num: int)` that returns a tuple of:
1. `val_str` converted to an integer.
2. `num` converted to a string.
3. `val_str` converted to a float.
4. `bool` truth value of `num` (whether `num != 0`).
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
        "editorial": """### Python Type Casting Basics
- `int(s)` parses a valid numeric string into an integer.
- `str(n)` converts any object to its string representation.
- `float(s)` parses decimals.
- `bool(x)` evaluates Python truthiness (0, '', None, [], {} are `False`, everything else is `True`).
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
        "title": "Floor Division & Modulo Rules",
        "kind": "fundamental",
        "track": "track_0_python_basics",
        "difficulty": "Easy",
        "category": "Python Basics",
        "tags": ["Python Basics", "Arithmetic", "Modulo"],
        "description": """Write a function `div_mod_stats(a: int, b: int)` that returns a tuple of:
1. `float_div`: `a / b` (standard floating point division)
2. `floor_div`: `a // b` (integer floor division — note Python rounds down towards $-\\infty$)
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
        "editorial": """### Division in Python
- `/` always produces a `float` (e.g. `4 / 2 = 2.0`).
- `//` performs floor division (rounds down towards negative infinity, so `-7 // 2 == -4`, NOT `-3`).
- `divmod(a, b)` computes `(a // b, a % b)` in a single bytecode instruction.
""",
        "test_cases": [
            {"input": {"a": 7, "b": 2}, "expected": [3.5, 3, 1, [3, 1]]},
            {"input": {"a": -7, "b": 2}, "expected": [-3.5, -4, 1, [-4, 1]]},
            {"input": {"a": 15, "b": 4}, "expected": [3.75, 3, 3, [3, 3]]},
        ],
        "hints": ["Return (a / b, a // b, a % b, divmod(a, b))."],
    },
    {
        "slug": "py-basics-reverse-range-loop",
        "title": "Reverse Range Loop Mechanics",
        "kind": "fundamental",
        "track": "track_0_python_basics",
        "difficulty": "Easy",
        "category": "Python Basics",
        "tags": ["Python Basics", "Loops", "Range"],
        "description": """Write a function `reverse_range_list(n: int)` that uses `range(...)` with negative step to construct and return a list of integers counting down from `n - 1` down to `0` inclusive.
""",
        "examples": [{"input": "n = 5", "output": "[4, 3, 2, 1, 0]"}],
        "constraints": ["1 <= n <= 100"],
        "starter_codes": {
            "python": """def reverse_range_list(n: int) -> list[int]:
    # Write your solution below
    pass
"""
        },
        "solutions": {
            "python": """def reverse_range_list(n: int) -> list[int]:
    return [i for i in range(n - 1, -1, -1)]
"""
        },
        "editorial": """### Reverse Iteration in Python
To count down from `n-1` to `0`:
`range(start, stop, step)`:
- `start`: `n - 1`
- `stop`: `-1` (because `stop` is exclusive, so it stops after `0`)
- `step`: `-1`
""",
        "test_cases": [
            {"input": {"n": 5}, "expected": [4, 3, 2, 1, 0]},
            {"input": {"n": 1}, "expected": [0]},
            {"input": {"n": 3}, "expected": [2, 1, 0]},
        ],
        "hints": ["Use range(n - 1, -1, -1)."],
    },
    {
        "slug": "py-basics-nonlocal-scope",
        "title": "Nested Helper Scope & Nonlocal",
        "kind": "fundamental",
        "track": "track_0_python_basics",
        "difficulty": "Easy",
        "category": "Python Basics",
        "tags": ["Python Basics", "Scope", "Recursion Helper"],
        "description": """In tree and graph algorithms, helper functions frequently need to update a shared variable (e.g. `max_depth` or `best_score`).
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
        "editorial": """### The `nonlocal` Keyword in Python
In Python, assigning to a variable inside an inner function creates a local variable by default unless declared `nonlocal`.
`nonlocal count` allows the inner function to rebind `count` in the enclosing function scope.
""",
        "test_cases": [
            {"input": {"events": [1, -2, 3, 0, 5]}, "expected": 3},
            {"input": {"events": [-1, -2, -3]}, "expected": 0},
            {"input": {"events": [10, 20]}, "expected": 2},
        ],
        "hints": ["Inside process(), write 'nonlocal count' before modifying count."],
    },
    {
        "slug": "py-basics-f-strings-formatting",
        "title": "F-Strings & Formatted Text",
        "kind": "fundamental",
        "track": "track_0_python_basics",
        "difficulty": "Easy",
        "category": "Python Basics",
        "tags": ["Python Basics", "Strings", "F-Strings"],
        "description": """Write a function `format_benchmark(name: str, score: float, rank: int)` that returns an f-string formatted as:
`"Athlete {name}: Score {score:.2f} (Rank #{rank})"`
where `score` is formatted to exactly 2 decimal places.
""",
        "examples": [
            {
                "input": "name = 'Alice', score = 94.5678, rank = 1",
                "output": "'Athlete Alice: Score 94.57 (Rank #1)'",
            }
        ],
        "constraints": ["name is non-empty", "rank >= 1"],
        "starter_codes": {
            "python": """def format_benchmark(name: str, score: float, rank: int) -> str:
    # Write your solution below
    pass
"""
        },
        "solutions": {
            "python": """def format_benchmark(name: str, score: float, rank: int) -> str:
    return f"Athlete {name}: Score {score:.2f} (Rank #{rank})"
"""
        },
        "editorial": """### Python F-Strings
F-strings `f"..."` evaluate expressions inside `{}` at runtime.
Format specifiers like `{score:.2f}` round and display floating point numbers to 2 decimal places.
""",
        "test_cases": [
            {"input": {"name": "Alice", "score": 94.5678, "rank": 1}, "expected": "Athlete Alice: Score 94.57 (Rank #1)"},
            {"input": {"name": "Bob", "score": 88.0, "rank": 4}, "expected": "Athlete Bob: Score 88.00 (Rank #4)"},
        ],
        "hints": ["Use f'Athlete {name}: Score {score:.2f} (Rank #{rank})'."],
    },

    # ── Track 1: Pythonic Fluency & Collections Gymnastics ───────────────────
    {
        "slug": "py-fluency-list-slicing",
        "title": "List Slicing & In-Place Reversal",
        "kind": "fundamental",
        "track": "track_1_pythonic_fluency",
        "difficulty": "Easy",
        "category": "Python Fluency",
        "tags": ["Slicing", "Lists"],
        "description": """Write a function `slice_operations(arr: list[int])` that returns a tuple of:
1. `reversed_arr`: a new list with elements in reverse order using slice syntax.
2. `even_indices`: elements at even indices (`0, 2, 4, ...`).
3. `middle_three`: elements from index 1 up to index 3 (length 3, indices 1, 2, 3).
""",
        "examples": [
            {
                "input": "arr = [10, 20, 30, 40, 50]",
                "output": "([50, 40, 30, 20, 10], [10, 30, 50], [20, 30, 40])",
            }
        ],
        "constraints": ["len(arr) >= 4"],
        "starter_codes": {
            "python": """def slice_operations(arr: list[int]) -> tuple[list[int], list[int], list[int]]:
    # Write your solution below
    pass
"""
        },
        "solutions": {
            "python": """def slice_operations(arr: list[int]) -> tuple[list[int], list[int], list[int]]:
    return (arr[::-1], arr[::2], arr[1:4])
"""
        },
        "editorial": """### Python Slicing Cheat Sheet
- `arr[::-1]`: Reverses a sequence.
- `arr[::step]`: Takes elements every `step` items.
- `arr[start:end]`: Slices from `start` up to (exclusive) `end`.
""",
        "test_cases": [
            {"input": {"arr": [10, 20, 30, 40, 50]}, "expected": [[50, 40, 30, 20, 10], [10, 30, 50], [20, 30, 40]]},
            {"input": {"arr": [1, 2, 3, 4]}, "expected": [[4, 3, 2, 1], [1, 3], [2, 3, 4]]},
        ],
        "hints": ["Use arr[::-1], arr[::2], and arr[1:4]."],
    },
    {
        "slug": "py-fluency-2d-matrix-init",
        "title": "2D Matrix Comprehension Trap",
        "kind": "fundamental",
        "track": "track_1_pythonic_fluency",
        "difficulty": "Easy",
        "category": "Python Fluency",
        "tags": ["2D Matrix", "List Comprehension", "Trap"],
        "description": """In Python, writing `[[0] * C] * R` creates $R$ references to the **exact same row list in memory** (mutating one changes all rows!).
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
        "editorial": """### The Mutable Reference Trap in 2D Arrays
Writing `[[0] * C] * R` duplicates the list pointer $R$ times. Modifying `grid[0][0] = 1` sets the first element of EVERY row to 1.
The correct, safe pattern is:
`[[default_val] * C for _ in range(R)]` or `[[default_val for _ in range(C)] for _ in range(R)]`.
""",
        "test_cases": [
            {"input": {"R": 2, "C": 3, "default_val": 7}, "expected": [[7, 7, 7], [7, 7, 7]]},
            {"input": {"R": 1, "C": 1, "default_val": 0}, "expected": [[0]]},
        ],
        "hints": ["Use [[default_val] * C for _ in range(R)]."],
    },
    {
        "slug": "py-fluency-counter-frequency",
        "title": "Collections Counter & Frequency Map",
        "kind": "fundamental",
        "track": "track_1_pythonic_fluency",
        "difficulty": "Easy",
        "category": "Python Fluency",
        "tags": ["Counter", "Hash Map", "Frequency"],
        "description": """Write a function `top_frequent_char(s: str)` that uses `collections.Counter` to find the most frequent character in string `s`.
If there's a tie, return the one that appears first alphabetically.
""",
        "examples": [{"input": "s = 'tree'", "output": "'e'"}, {"input": "s = 'ccba'", "output": "'c'"}],
        "constraints": ["1 <= len(s) <= 1000"],
        "starter_codes": {
            "python": """from collections import Counter

def top_frequent_char(s: str) -> str:
    # Write your solution below
    pass
"""
        },
        "solutions": {
            "python": """from collections import Counter

def top_frequent_char(s: str) -> str:
    counts = Counter(s)
    # Sort by frequency descending (-count), then char ascending
    return min(counts.keys(), key=lambda c: (-counts[c], c))
"""
        },
        "editorial": """### Counter & Custom Keys
`Counter(s)` builds an $O(N)$ hash map of frequencies.
Sorting with key `(-counts[c], c)` prioritizes highest count, breaking ties alphabetically.
""",
        "test_cases": [
            {"input": {"s": "tree"}, "expected": "e"},
            {"input": {"s": "ccba"}, "expected": "c"},
            {"input": {"s": "bba"}, "expected": "b"},
        ],
        "hints": ["Use Counter(s) and min(counts.keys(), key=lambda c: (-counts[c], c))."],
    },

    # ── Track 2: Data Structure Mechanics & APIs ──────────────────────────────
    {
        "slug": "py-ds-deque-fifo",
        "title": "Queue & Deque FIFO Mechanics",
        "kind": "fundamental",
        "track": "track_2_data_structures",
        "difficulty": "Easy",
        "category": "Data Structures",
        "tags": ["Deque", "Queue", "FIFO"],
        "description": """`list.pop(0)` takes $O(N)$ time because all remaining elements must shift left in memory.
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
        "editorial": """### Why Deque for BFS and Queues
Standard Python `list` is a dynamic array; `pop(0)` is $O(N)$.
`collections.deque` is a doubly linked list of fixed-size blocks; `append` and `popleft` are both $O(1)$.
""",
        "test_cases": [
            {"input": {"ops": ["push", "push", "pop", "push"], "vals": [10, 20, 0, 30]}, "expected": [20, 30]},
            {"input": {"ops": ["push", "pop"], "vals": [5, 0]}, "expected": []},
        ],
        "hints": ["Use deque.append() and deque.popleft()."],
    },
    {
        "slug": "py-ds-heapq-mechanics",
        "title": "Min-Heap & Max-Heap with Heapq",
        "kind": "fundamental",
        "track": "track_2_data_structures",
        "difficulty": "Easy",
        "category": "Data Structures",
        "tags": ["Heap", "Priority Queue", "Heapq"],
        "description": """Python's `heapq` module implements a **Min-Heap** by default.
Write a function `heap_top_k(nums: list[int], k: int)` that uses `heapq` to return the $k$ largest integers in `nums` sorted in descending order.
""",
        "examples": [{"input": "nums = [3, 2, 1, 5, 6, 4], k = 2", "output": "[6, 5]"}],
        "constraints": ["1 <= k <= len(nums) <= 1000"],
        "starter_codes": {
            "python": """import heapq

def heap_top_k(nums: list[int], k: int) -> list[int]:
    # Write your solution using heapq
    pass
"""
        },
        "solutions": {
            "python": """import heapq

def heap_top_k(nums: list[int], k: int) -> list[int]:
    return heapq.nlargest(k, nums)
"""
        },
        "editorial": """### Heap Mechanics in Python
- `heapq.heapify(arr)`: Converts list to min-heap in $O(N)$ time.
- `heapq.heappush(h, x)`: $O(\\log N)$ insertion.
- `heapq.heappop(h)`: $O(\\log N)$ removal of minimum element.
- `heapq.nlargest(k, arr)`: Efficiently extracts top $k$ elements in $O(N \\log k)$.
""",
        "test_cases": [
            {"input": {"nums": [3, 2, 1, 5, 6, 4], "k": 2}, "expected": [6, 5]},
            {"input": {"nums": [1, 2, 3], "k": 1}, "expected": [3]},
        ],
        "hints": ["Use heapq.nlargest(k, nums)."],
    },

    # ── Track 3: Algorithmic Scaffolds & Templates ────────────────────────────
    {
        "slug": "py-scaffold-binary-search",
        "title": "Binary Search Scaffold (Classic)",
        "kind": "fundamental",
        "track": "track_3_algorithmic_scaffolds",
        "difficulty": "Easy",
        "category": "Algorithmic Scaffolds",
        "tags": ["Binary Search", "Template"],
        "description": """Write a function `binary_search(nums: list[int], target: int) -> int` that implements the classic binary search template on a sorted array `nums`.
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
        "editorial": """### The Classic Binary Search Scaffold
1. `left, right = 0, len(nums) - 1`
2. `while left <= right:` (condition includes `<=`)
3. `mid = (left + right) // 2`
4. If `nums[mid] < target`, move `left = mid + 1`. If `nums[mid] > target`, move `right = mid - 1`.
""",
        "test_cases": [
            {"input": {"nums": [-1, 0, 3, 5, 9, 12], "target": 9}, "expected": 4},
            {"input": {"nums": [-1, 0, 3, 5, 9, 12], "target": 2}, "expected": -1},
            {"input": {"nums": [5], "target": 5}, "expected": 0},
        ],
        "hints": ["Use while left <= right, mid = (left + right) // 2, left = mid + 1, right = mid - 1."],
    },
    {
        "slug": "py-scaffold-two-pointers-palindrome",
        "title": "Two Pointers In-Place Scaffold",
        "kind": "fundamental",
        "track": "track_3_algorithmic_scaffolds",
        "difficulty": "Easy",
        "category": "Algorithmic Scaffolds",
        "tags": ["Two Pointers", "Template"],
        "description": """Write a function `is_palindrome_two_pointers(s: str) -> bool` using opposite-end two pointers (`left = 0, right = len(s) - 1`).
Ignore non-alphanumeric characters and case.
""",
        "examples": [{"input": "s = 'A man, a plan, a canal: Panama'", "output": "True"}],
        "constraints": ["1 <= len(s) <= 2 * 10^5"],
        "starter_codes": {
            "python": """def is_palindrome_two_pointers(s: str) -> bool:
    left, right = 0, len(s) - 1
    # Implement two pointer while left < right
    pass
"""
        },
        "solutions": {
            "python": """def is_palindrome_two_pointers(s: str) -> bool:
    left, right = 0, len(s) - 1
    while left < right:
        while left < right and not s[left].isalnum():
            left += 1
        while left < right and not s[right].isalnum():
            right -= 1
        if s[left].lower() != s[right].lower():
            return False
        left += 1
        right -= 1
    return True
"""
        },
        "editorial": """### Two Pointers Opposite Ends Scaffold
Opposite-end pointers move towards each other until `left >= right`.
Checking `s[left].isalnum()` skips punctuation in $O(N)$ time without allocating new string copies.
""",
        "test_cases": [
            {"input": {"s": "A man, a plan, a canal: Panama"}, "expected": True},
            {"input": {"s": "race a car"}, "expected": False},
            {"input": {"s": " "}, "expected": True},
        ],
        "hints": ["Use while left < right and s[left].isalnum() checks."],
    },
    {
        "slug": "py-scaffold-sliding-window",
        "title": "Sliding Window Scaffold (Dynamic Length)",
        "kind": "fundamental",
        "track": "track_3_algorithmic_scaffolds",
        "difficulty": "Easy",
        "category": "Algorithmic Scaffolds",
        "tags": ["Sliding Window", "Template"],
        "description": """Write a function `max_subarray_sum_k(nums: list[int], k: int) -> int` that finds the maximum sum of any contiguous subarray of fixed size `k`.
Use the standard sliding window pattern.
""",
        "examples": [{"input": "nums = [2, 1, 5, 1, 3, 2], k = 3", "output": "9"}],
        "constraints": ["k <= len(nums)"],
        "starter_codes": {
            "python": """def max_subarray_sum_k(nums: list[int], k: int) -> int:
    # Build window of size k, then slide
    pass
"""
        },
        "solutions": {
            "python": """def max_subarray_sum_k(nums: list[int], k: int) -> int:
    window_sum = sum(nums[:k])
    max_sum = window_sum
    for i in range(k, len(nums)):
        window_sum += nums[i] - nums[i - k]
        max_sum = max(max_sum, window_sum)
    return max_sum
"""
        },
        "editorial": """### Fixed Sliding Window Scaffold
Instead of recomputing the sum of $k$ elements in $O(K)$ time for each position (leading to $O(N \\times K)$), add the new incoming element `nums[i]` and subtract the outgoing element `nums[i - k]` in $O(1)$ per step $\\implies O(N)$ total.
""",
        "test_cases": [
            {"input": {"nums": [2, 1, 5, 1, 3, 2], "k": 3}, "expected": 9},
            {"input": {"nums": [1, 2], "k": 1}, "expected": 2},
        ],
        "hints": ["Calculate initial sum(nums[:k]), then slide by adding nums[i] and subtracting nums[i-k]."],
    },

    # ── Track 4: Custom Sorting & Comparators ─────────────────────────────────
    {
        "slug": "py-sort-multi-key-lambda",
        "title": "Multi-Key Lambda Sorting",
        "kind": "fundamental",
        "track": "track_4_custom_sorting",
        "difficulty": "Easy",
        "category": "Custom Sorting",
        "tags": ["Sorting", "Lambda", "Comparators"],
        "description": """Write a function `sort_students(records: list[tuple[str, int, int]])` where each record is `(name, score, age)`.
Sort the list in-place such that:
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
        "editorial": """### Multi-Key Sorting in Python
Python's Timsort evaluates tuples element-by-element.
`key=lambda x: (-x[1], x[2], x[0])`:
- `-x[1]` inverts the numerical score $\\implies$ descending order.
- `x[2]` keeps age $\\implies$ ascending order.
- `x[0]` alphabetical name.
""",
        "test_cases": [
            {
                "input": {"records": [("Alice", 90, 20), ("Bob", 90, 19), ("Charlie", 85, 22)]},
                "expected": [["Bob", 90, 19], ["Alice", 90, 20], ["Charlie", 85, 22]],
            }
        ],
        "hints": ["Use sorted(records, key=lambda x: (-x[1], x[2], x[0]))."],
    },

    # ── Track 5: Bit Manipulation Fundamentals ────────────────────────────────
    {
        "slug": "py-bit-check-set-clear",
        "title": "Bitwise Check, Set, and Clear",
        "kind": "fundamental",
        "track": "track_5_bit_manipulation",
        "difficulty": "Easy",
        "category": "Bit Manipulation",
        "tags": ["Bitwise", "Masks"],
        "description": """Write a function `bit_operations(n: int, i: int)` that performs 3 operations on the $i$-th bit (0-indexed) of integer `n`:
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
        "editorial": """### Bit Manipulation Formulas
- Check $i$-th bit: `(n >> i) & 1`
- Set $i$-th bit: `n | (1 << i)`
- Clear $i$-th bit: `n & ~(1 << i)`
- Toggle $i$-th bit: `n ^ (1 << i)`
""",
        "test_cases": [
            {"input": {"n": 5, "i": 1}, "expected": [False, 7, 5]},
            {"input": {"n": 5, "i": 0}, "expected": [True, 5, 4]},
        ],
        "hints": ["(n >> i) & 1, n | (1 << i), n & ~(1 << i)."],
    },

    # ── Track 6: Big-O Complexity & Math Idioms ───────────────────────────────
    {
        "slug": "py-math-prefix-sums",
        "title": "Prefix Sum Array Builder",
        "kind": "fundamental",
        "track": "track_6_complexity_math",
        "difficulty": "Easy",
        "category": "Math & Complexity",
        "tags": ["Prefix Sums", "Array"],
        "description": """Prefix sums allow calculating the sum of any subarray `nums[L...R]` in $O(1)$ time after an $O(N)$ precomputation:
$\\text{sum}(L, R) = P[R + 1] - P[L]$
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
        "editorial": """### The Prefix Sum Array Pattern
With $P[i] = P[i-1] + \\text{nums}[i-1]$:
Subarray sum from index $L$ to $R$ inclusive is given in $O(1)$ by:
$P[R + 1] - P[L]$.
""",
        "test_cases": [
            {"input": {"nums": [1, 2, 3, 4]}, "expected": [0, 1, 3, 6, 10]},
            {"input": {"nums": []}, "expected": [0]},
            {"input": {"nums": [5]}, "expected": [0, 5]},
        ],
        "hints": ["Initialize prefix = [0] * (len(nums) + 1), then prefix[i+1] = prefix[i] + num."],
    },
]

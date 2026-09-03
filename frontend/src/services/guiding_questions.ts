/**
 * Curated Core Guiding Questions for MIT 6.0001 Pre-LeetCode Fundamentals.
 *
 * Grounded in MIT 6.0001 (Introduction to Computer Science and Programming in Python)
 * by Profs. John V. Guttag, Eric Grimson, and Dr. Ana Bell.
 *
 * Designed for Active Reading (SQ3R / Socratic priming): Asking targeted,
 * thought-provoking questions before reading focuses attention on critical
 * invariants, computational tradeoffs, and subtle pitfalls.
 */

export const GUIDING_QUESTIONS_MAP: Record<string, string[]> = {
  // Track 0: Python Basics & Numerics (MIT 6.0001 Lec 1–3, Pset 1)
  'py-basics-type-casting': [
    'Why is Python described as both strongly typed and dynamically typed, and how does a variable name differ from the heap object it binds to?',
    'Why does evaluating bool(x) return False for empty containers and 0, but True for strings like "False" or "0"?',
    'Why is testing floating-point numbers with exact equality == dangerous, and how does IEEE 754 precision dictate approximate tolerance (|a - b| < ε)?',
  ],
  'py-basics-floor-div-modulo': [
    'How does Python floor division (//) handle negative numbers differently from languages that truncate toward zero (such as C or Java)?',
    'What fundamental mathematical invariant strictly connects a, b, a // b, and a % b in Python?',
    'Why does Python guarantee that a % b always shares the sign of the divisor b rather than the dividend a?',
  ],
  'py-basics-bisection-sqrt': [
    'What monotonic property must a mathematical function satisfy for bisection search to guarantee convergence?',
    'How does the search space behave when x < 1 versus x ≥ 1, and why does setting high = x fail when x < 1?',
    'What is the decrementing function for bisection search, and how does it guarantee termination in logarithmic O(log((high - low) / ε)) steps?',
  ],
  'py-basics-newton-raphson': [
    'Why does Newton-Raphson converge quadratically (doubling correct precision digits per step) compared to bisection search’s linear convergence?',
    'What derivative computation drives the step y_new = y - f(y)/f\'(y) for square roots (f(y) = y² - k)?',
    'What initial guesses or derivative edge cases could cause Newton-Raphson to oscillate or fail to converge?',
  ],
  'py-basics-nonlocal-scope': [
    'What is the exact search order in Python’s LEGB rule (Local, Enclosing, Global, Built-in)?',
    'Why does assigning to a variable anywhere inside a nested function make it local by default, raising UnboundLocalError if read beforehand?',
    'What semantic difference exists between the global and nonlocal keywords when mutating enclosing state?',
  ],
  'py-basics-loops-range': [
    'Why is range(start, stop, step) a memory-efficient lazy sequence object (O(1) space) rather than a pre-allocated list of integers?',
    'How does testing integer divisors up to √n allow proving primality in O(√n) time instead of O(n)?',
    'What is a loop invariant, and how do you demonstrate that a while loop makes monotonic progress toward its termination condition?',
  ],
  'py-basics-string-indexing-slicing': [
    'Why does Python adopt the half-open interval [start, stop) convention for slicing, and how does len = stop - start simplify boundary arithmetic?',
    'Why does index lookup s[i] raise an IndexError on out-of-bounds indices, while slice extraction s[start:stop] gracefully clamps?',
    'How does negative stride s[::-1] reverse sequences, and what are the time and space costs of creating new slice copies?',
  ],

  // Track 1: Structured Types & Aliasing (MIT 6.0001 Lec 4–5, Pset 2)
  'py-fluency-mutability-aliasing': [
    'What is the fundamental difference between introducing an alias (new_L = L) and creating a shallow copy (new_L = L[:] or L.copy())?',
    'Why does mutating a list (e.g. L.remove(x)) while directly iterating over it (for x in L:) silently skip elements?',
    'How do object identity (id(a) == id(b) / a is b) and structural equality (a == b) differ in Python memory?',
  ],
  'py-fluency-higher-order-functions': [
    'What does it mean for functions to be first-class citizens in Python’s computational model?',
    'How do higher-order functions (like map, filter, or custom decorators) decouple iteration control flow from element transformation?',
    'What syntactic and scoping limitations distinguish lambda expressions from standard def functions?',
  ],
  'py-fluency-2d-matrix-init': [
    'Why does [[0] * cols] * rows create multiple references to the exact same list in memory rather than independent rows?',
    'Why does list comprehension [[0 for _ in range(cols)] for _ in range(rows)] create distinct heap objects for every row?',
    'How can you programmatically verify that two rows in a 2D matrix do not share the same memory address?',
  ],
  'py-fluency-mutable-default-arg': [
    'When are default argument expressions in Python functions evaluated: at function definition time or at invocation time?',
    'Why does using def append_to(val, target=[]) cause mutable state to persist across unrelated function calls?',
    'What is the canonical Python idiom (target=None) used to safely initialize default mutable containers?',
  ],
  'py-fluency-string-immutability': [
    'Why are strings immutable in Python, and what happens to memory allocations during repeated s += char operations in loops?',
    'Why does "".join(list_of_chars) achieve O(n) linear runtime while repeated += string concatenation can degrade to O(n²)?',
    'How does immutability enable strings to be safely used as hashable dictionary keys and set elements?',
  ],
  'py-fluency-tuples-multiple-assign': [
    'What is the semantic difference in Python between a tuple (heterogeneous fixed record) and a list (homogeneous dynamic collection)?',
    'How does Python execute multiple assignment a, b = b, a via implicit tuple packing and unpacking without an explicit temporary variable?',
    'Why can a tuple containing mutable items (like ([1, 2], 3)) NOT be used as a dictionary key or set element?',
  ],
  'py-fluency-sets-dicts': [
    'How do sets and dictionaries achieve O(1) average-time lookup, insertion, and deletion using internal hash tables?',
    'How do mathematical set operations (union |, intersection &, difference -, symmetric difference ^) translate to algorithmic deduplication?',
    'What happens to hash table integrity if an object placed inside a set has its internal state mutated after insertion?',
  ],

  // Track 2: ADTs, Hash Tables & OOP (MIT 6.0001 Lec 8–9, Pset 5)
  'py-ds-custom-intset-adt': [
    'What is the difference between an Abstract Data Type’s public interface and its private internal representation?',
    'What class invariant does Guttag’s Int_set maintain regarding duplicate elements, and how is it preserved during insert and remove?',
    'Why is encapsulation critical for allowing internal data structure refactoring without breaking client code?',
  ],
  'py-ds-deque-fifo': [
    'Why is list.pop(0) an O(n) linear-time operation in Python, and how does collections.deque.popleft() achieve O(1) constant time?',
    'How is a double-ended queue structured internally in memory (doubly linked blocks) to enable fast operations at both ends?',
    'In which algorithmic scaffolds (such as BFS and sliding window maximum) is O(1) queue popping essential to avoid timeouts?',
  ],
  'py-ds-hash-table-dict': [
    'What mathematical contract must __hash__ and __eq__ satisfy for an object to be safely usable as a dictionary key?',
    'How do hash collisions occur, and how does Python resolve collisions internally (open addressing with perturbation probing)?',
    'Why must dictionary keys and set elements be strictly hashable and immutable?',
  ],
  'py-ds-magic-methods-ordering': [
    'How do Python dunder methods (like __lt__, __eq__, __repr__, __str__) enable user-defined classes to integrate with built-in functions like sorted()?',
    'What is the difference between __repr__ (unambiguous developer representation) and __str__ (readable user representation)?',
    'Why is defining __lt__ (less-than) usually sufficient for Python’s TimSort to establish a total ordering?',
  ],
  'py-ds-inheritance-substitution': [
    'What is the Liskov Substitution Principle (LSP), and why must a subclass be usable anywhere its superclass is expected without breaking correctness?',
    'Why is inheritance for code reuse often inferior to object composition ("favor composition over inheritance")?',
    'How does super().__init__() properly initialize inherited state in Python’s class hierarchy?',
  ],

  // Track 3: Recursion & Scaffolds (MIT 6.0001 Lec 6, Pset 3–4)
  'py-scaffold-inductive-palindrome': [
    'What is the inductive base case for verifying whether a sequence is a palindrome?',
    'How does the recursive step reduce problem size: what invariant is checked on the ends before recursing on the interior substring?',
    'What is the call stack depth and memory overhead of recursive slicing versus iterative two-pointer verification?',
  ],
  'py-scaffold-fibonacci-memoization': [
    'Why does the naive recursive Fibonacci implementation exhibit exponential O(ϕⁿ) runtime?',
    'How does memoization transform an overlapping computation tree into a linear Directed Acyclic Graph (DAG) with O(n) work?',
    'What is the key difference in space complexity between top-down memoization (call stack + table) and bottom-up iterative tabulation (O(1) space)?',
  ],
  'py-scaffold-binary-search': [
    'What decrementing function proves that binary search is guaranteed to make progress and terminate?',
    'Why is the loop boundary condition low <= high vs low < high critical, and how does it determine the target insertion point?',
    'How does the wrapper function pattern hide implementation details (like search bounds) from client code?',
  ],
  'py-scaffold-knapsack-01-memo': [
    'What two conditions define optimal substructure and overlapping subproblems in the 0/1 Knapsack problem?',
    'Why does a greedy approach (taking highest value/weight ratio first) fail on 0/1 knapsack problems?',
    'What state parameters are necessary and sufficient to uniquely identify a subproblem in the memoization table?',
  ],
  'py-scaffold-recursive-factorial': [
    'What two essential components are required in every recursive function: base case and recursive progress step?',
    'What happens in the memory call stack during deep recursion, and what causes RecursionError: maximum recursion depth exceeded?',
    'How does an iterative loop compare to recursion in terms of auxiliary space overhead (O(1) vs O(n) call frames)?',
  ],

  // Track 4: Divide-and-Conquer Sorting (MIT 6.0001 Lec 12)
  'py-sort-merge-sort': [
    'Why is merge sort guaranteed O(n log n) worst-case time complexity, and what is its space tradeoff (O(n) auxiliary memory)?',
    'What does algorithm stability mean, and why is left[i] <= right[j] essential during the merge step to preserve stability?',
    'How does the recurrence relation T(n) = 2T(n/2) + O(n) resolve to Θ(n log n) using the Master Theorem?',
  ],
  'py-sort-multi-key-lambda': [
    'How does Python sorted(data, key=...) evaluate sort keys without comparing raw composite objects directly?',
    'How can you sort by multiple criteria (such as secondary score ascending, primary name descending) using tuples and numerical negation?',
    'Because Python’s TimSort is stable, why can you achieve multi-key ordering by sorting successively from least significant to most significant key?',
  ],

  // Track 5: Binary Encodings & Bits (MIT 6.0001 Numerics)
  'py-bit-check-set-clear': [
    'How do bitwise operators (&, |, ^, ~, <<, >>) manipulate raw integer binary representations?',
    'What bitmask expressions check, set, clear, and toggle the k-th bit of an integer in O(1) time?',
    'Why are bitmasks widely used for compact state representations, set operations, and constant-time subset checks?',
  ],
  'py-bit-kernighan-set-bits': [
    'Why does the expression n & (n - 1) always clear the lowest set bit (rightmost 1) of integer n?',
    'How does Brian Kernighan’s algorithm count set bits in O(number of set bits) time rather than O(total bits)?',
    'How can you test whether a number is an exact power of two using a single bitwise operation?',
  ],

  // Track 6: Asymptotic Complexity & Efficiency (MIT 6.0001 Lec 10–11)
  'py-math-asymptotic-complexity': [
    'What is the formal mathematical definition of Big-O notation O(g(n)) as an asymptotic upper bound?',
    'Why do constant multipliers and lower-order terms become negligible as input size n approaches infinity?',
    'How do logarithmic O(log n), linear O(n), quasilinear O(n log n), quadratic O(n²), and exponential O(2ⁿ) growth rates compare when n = 10⁵?',
  ],
  'py-math-prefix-sums': [
    'How does precomputing a cumulative prefix sum array allow arbitrary subarray range sum queries in O(1) constant time?',
    'What is the mathematical relation between range_sum(L, R) and prefix sum array entries P[R + 1] - P[L]?',
    'Why is a 1-indexed prefix sum array (with P[0] = 0) standard for preventing boundary edge case checks at L = 0?',
  ],

  // Track 7: Testing, Debugging & Exceptions (MIT 6.0001 Lec 7)
  'py-verify-black-glass-box-testing': [
    'What is the difference between black-box testing (specification-driven) and glass-box testing (code path/branch-driven)?',
    'Why must testing systematically include boundary conditions, empty inputs, singletons, and extreme values?',
    'Why does 100% statement coverage not guarantee that all logical branch combinations or state bugs are covered?',
  ],
  'py-verify-exceptions-assertions': [
    'What is the difference between using assert for internal programmer invariants vs raising ValueError for client input validation?',
    'Why does Python optimize away assert statements when run with the -O flag, and why should assertions never execute stateful side-effects?',
    'How does the try-except-finally structure guarantee resource cleanup regardless of whether an exception occurs?',
  ],
  'py-modules-files-with': [
    'How does Python’s "with open(...) as f:" context manager guarantee file descriptor closure even when unhandled exceptions occur?',
    'What special dunder methods (__enter__ and __exit__) power Python context managers under the hood?',
    'What is the memory difference between reading a file line-by-line (for line in f:) versus loading the entire content into memory (f.read())?',
  ],

  // Track 8: Graphs & Optimization (MIT 6.0002 / 6.0001 Adv)
  'py-graph-adjacency-build': [
    'What are the space and time tradeoffs between an adjacency list and an adjacency matrix for sparse graphs versus dense graphs?',
    'Why is an adjacency list representation preferred for standard graph traversals where node degree d(u) ≪ V?',
    'How does representing directed graphs differ from undirected graphs during edge insertion?',
  ],
  'py-graph-bfs-shortest-path': [
    'Why does Breadth-First Search (BFS) guarantee finding the shortest path (in number of edges) on unweighted graphs?',
    'Why does BFS fail to minimize path cost on weighted graphs where edge weights are non-uniform?',
    'Why must visited states be recorded immediately upon queue enqueue rather than on dequeue to prevent duplicate node exploration?',
  ],
  'py-graph-dfs-cycle-detect': [
    'Why is a 3-state visited tracking system (WHITE: unvisited, GREY: visiting/ancestor on current stack, BLACK: finished) required to detect cycles in directed graphs?',
    'Why would a simple 2-state visited boolean set falsely report cycles in directed graphs with diamond paths (A → B → D and A → C → D)?',
    'How does DFS recursion relate to an explicit LIFO call stack and back-edge traversal?',
  ],
  'py-graph-greedy-vs-optimal': [
    'What is the greedy choice property, and under what conditions does making locally optimal choices guarantee a global optimum?',
    'In what common scenarios (such as 0/1 knapsack, coin change with arbitrary denominations, or graphs with negative edges) do greedy heuristics fail?',
    'How can you construct a small counterexample to prove that a proposed greedy heuristic is suboptimal?',
  ],
}

/**
 * Returns the curated guiding questions for a given problem slug.
 * Falls back to dynamic general inquiry questions if no custom list is mapped.
 */
export function getGuidingQuestions(
  slug?: string | null,
  title?: string,
  category?: string
): string[] {
  if (slug && GUIDING_QUESTIONS_MAP[slug]) {
    return GUIDING_QUESTIONS_MAP[slug]
  }

  return [
    `What fundamental theoretical concept or computational abstraction is ${title || 'this lesson'} establishing?`,
    `What invariants, edge cases, or common antipatterns should you watch out for in ${category || 'this topic'}?`,
    `How does this core concept transfer directly into algorithmic problem-solving and coding practice?`,
  ]
}

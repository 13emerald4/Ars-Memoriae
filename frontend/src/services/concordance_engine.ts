/**
 * Guttag Computational Strong's Concordance Lexicon & Cross-Reference Engine.
 *
 * Provides a structured dictionary of computational terms from John V. Guttag's
 * 'Introduction to Computation and Programming Using Python' (3rd Edition, MIT Press).
 *
 * Each entry contains:
 * - Strong's ID (e.g. G-101)
 * - Formal MIT 6.0001 definition
 * - Primary chapter & section
 * - All other textbook references and contextual usage excerpts across chapters
 * - LeetCode interview transfer model
 */

export interface ConcordanceOccurrence {
  chapter: string
  section: string
  pageRange?: string
  contextSnippet: string
}

export interface ConcordanceEntry {
  id: string // e.g. "G-101"
  term: string
  category: 'Primitives' | 'Memory & State' | 'Algorithms' | 'Data Structures' | 'Complexity' | 'Optimization'
  patterns: RegExp // Matches word and variations
  definition: string
  primaryLocation: string
  occurrences: ConcordanceOccurrence[]
  leetCodeRelevance: string
}

export const GUTTAG_CONCORDANCE_LEXICON: ConcordanceEntry[] = [
  {
    id: 'G-101',
    term: 'Scalar Object',
    category: 'Primitives',
    patterns: /\b(scalars?|scalar objects?)\b/gi,
    definition: 'An indivisible computational entity that has no accessible internal structure. In Python: int, float, bool, and NoneType.',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 12)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements of Python',
        pageRange: 'pp. 12–15',
        contextSnippet: 'Scalar objects are primitive values. Unlike composite objects, they cannot be subdivided by indexing or slicing.',
      },
      {
        chapter: 'Chapter 3',
        section: '§ 3.1 Exhaustive Enumeration',
        pageRange: 'pp. 28–30',
        contextSnippet: 'Exhaustive enumeration steps through a discrete range of integer scalar values testing candidate roots.',
      },
      {
        chapter: 'Chapter 5',
        section: '§ 5.1 Tuples and Sequences',
        pageRange: 'pp. 65–68',
        contextSnippet: 'Non-scalar structured types (tuples, lists) are ordered collections composed of scalar or other non-scalar references.',
      },
    ],
    leetCodeRelevance: 'Distinguishing immutable scalars from mutable heap structures prevents accidental reference aliasing during recursive state tracking.',
  },
  {
    id: 'G-102',
    term: 'Aliasing',
    category: 'Memory & State',
    patterns: /\b(aliasing|aliases|aliased|alias)\b/gi,
    definition: 'A state in which two or more distinct identifiers refer to the exact same physical object in memory (id(L1) == id(L2)). Modifying the object through one identifier silently mutates it for all aliases.',
    primaryLocation: 'Chapter 5 (§ 5.2.1 Lists and Mutability, p. 70)',
    occurrences: [
      {
        chapter: 'Chapter 5',
        section: '§ 5.2.1 Lists and Mutability',
        pageRange: 'pp. 68–74',
        contextSnippet: 'Because lists are mutable, assignment creates an alias rather than a clone. Any in-place mutation affects all alias pointers.',
      },
      {
        chapter: 'Chapter 5',
        section: '§ 5.3 Cloning & Matrices',
        pageRange: 'pp. 74–77',
        contextSnippet: 'Writing [[0]*C]*R creates R aliases to the same single row buffer, corrupting matrix state on assignment.',
      },
      {
        chapter: 'Chapter 10',
        section: '§ 10.1 Abstract Data Types',
        pageRange: 'pp. 158–162',
        contextSnippet: 'getMembers() must return a cloned list self.vals[:] to prevent caller aliasing of internal representation.',
      },
      {
        chapter: 'Chapter 15',
        section: '§ 15.2 Knapsack & Memoization',
        pageRange: 'pp. 252–257',
        contextSnippet: 'Memo keys must use immutable tuples rather than lists to guarantee hash invariant stability and prevent aliased mutation.',
      },
    ],
    leetCodeRelevance: 'Essential in Backtracking (Subsets, Permutations) where path arrays must be cloned with path[:] before adding to result lists.',
  },
  {
    id: 'G-103',
    term: 'Bisection Search',
    category: 'Algorithms',
    patterns: /\b(bisection search|bisection)\b/gi,
    definition: 'An interval-halving algorithm that finds a root of a monotonic continuous function by iteratively discarding half of the candidate search space in logarithmic time O(log(Range/ε)).',
    primaryLocation: 'Chapter 3 (§ 3.2 Approximate Solutions and Bisection Search, p. 32)',
    occurrences: [
      {
        chapter: 'Chapter 3',
        section: '§ 3.2 Approximate Solutions',
        pageRange: 'pp. 31–36',
        contextSnippet: 'Bisection search cuts the search interval in half on each step, reducing continuous search time exponentially compared to linear scanning.',
      },
      {
        chapter: 'Chapter 11',
        section: '§ 11.2 Asymptotic Notation',
        pageRange: 'pp. 182–185',
        contextSnippet: 'Logarithmic growth O(log n) characterizes bisection algorithms because the number of steps is proportional to the log of the search range.',
      },
      {
        chapter: 'Chapter 12',
        section: '§ 12.1 Search Algorithms',
        pageRange: 'pp. 195–198',
        contextSnippet: 'Binary search is discrete bisection search applied to sorted arrays, partitioning indices left and right around mid.',
      },
    ],
    leetCodeRelevance: 'Direct foundation of "Binary Search on Answer" problems (Koko Eating Bananas, Capacity to Ship Packages, Split Array Largest Sum).',
  },
  {
    id: 'G-104',
    term: 'Newton-Raphson',
    category: 'Algorithms',
    patterns: /\b(newton-raphson|newton\'s method)\b/gi,
    definition: 'A successive approximation algorithm for finding roots of differentiable functions f(y) = 0 using tangent-line linearizations: y_{new} = y - f(y)/f\'(y). Features quadratic convergence where correct digits double each step.',
    primaryLocation: 'Chapter 3 (§ 3.4 Newton-Raphson, p. 38)',
    occurrences: [
      {
        chapter: 'Chapter 3',
        section: '§ 3.4 Newton-Raphson',
        pageRange: 'pp. 38–41',
        contextSnippet: 'For f(y) = y^2 - k, the iterative update y = y - (y^2 - k)/(2y) converges quadratically to sqrt(k).',
      },
      {
        chapter: 'Chapter 11',
        section: '§ 11.1 Thinking About Computational Complexity',
        pageRange: 'pp. 180–182',
        contextSnippet: 'Quadratic convergence algorithms require far fewer iterations than linear bisection to achieve floating-point precision limits.',
      },
    ],
    leetCodeRelevance: 'Tested in LeetCode 69 (Sqrt(x)) and numerical root-finding where integer division successive approximation runs in O(1) iterations.',
  },
  {
    id: 'G-105',
    term: 'Representation Invariant',
    category: 'Memory & State',
    patterns: /\b(representation invariants?|rep invariants?)\b/gi,
    definition: 'A formal structural predicate that must hold true for the internal state representation of an Abstract Data Type (ADT) before and after every public method invocation.',
    primaryLocation: 'Chapter 10 (§ 10.1 Abstract Data Types and Classes, p. 158)',
    occurrences: [
      {
        chapter: 'Chapter 10',
        section: '§ 10.1 Abstract Data Types',
        pageRange: 'pp. 157–163',
        contextSnippet: 'In IntSet, the representation invariant guarantees that self.vals contains strictly sorted, non-duplicate integers.',
      },
      {
        chapter: 'Chapter 10',
        section: '§ 10.3 Object-Oriented Programming',
        pageRange: 'pp. 165–170',
        contextSnippet: 'Subclasses must preserve or strengthen the representation invariants established by their parent classes.',
      },
      {
        chapter: 'Chapter 12',
        section: '§ 12.3 Hash Tables',
        pageRange: 'pp. 208–214',
        contextSnippet: 'A hash table representation invariant requires that key hash buckets maintain collision chain consistency.',
      },
    ],
    leetCodeRelevance: 'Crucial for Design questions (LRU Cache, Monotonic Stack/Queue, Min Stack) where internal invariant integrity guarantees O(1) operations.',
  },
  {
    id: 'G-106',
    term: 'Inductive Step',
    category: 'Algorithms',
    patterns: /\b(inductive step|mathematical induction|inductive hypothesis|base case)\b/gi,
    definition: 'The recursive reduction step that solves a problem of size n by transforming it into a strictly smaller subproblem of size n-1 or n/2, assuming the recursive call correctly solves the subproblem.',
    primaryLocation: 'Chapter 6 (§ 6.1 Fibonacci & § 6.2 Palindromes, pp. 86–92)',
    occurrences: [
      {
        chapter: 'Chapter 6',
        section: '§ 6.2 Palindromes',
        pageRange: 'pp. 88–92',
        contextSnippet: 'The inductive step tests if s[0] == s[-1] and reduces verification to the inner substring s[1:-1].',
      },
      {
        chapter: 'Chapter 12',
        section: '§ 12.2 Merge Sort',
        pageRange: 'pp. 201–206',
        contextSnippet: 'The divide-and-conquer inductive step assumes mergeSort correctly sorts the two halved sublists.',
      },
      {
        chapter: 'Chapter 15',
        section: '§ 15.1 Dynamic Programming',
        pageRange: 'pp. 248–251',
        contextSnippet: 'Dynamic programming formalizes inductive recurrence relations by systematically caching subproblem base cases.',
      },
    ],
    leetCodeRelevance: 'Fundamental pattern for all Tree / Graph / String recursion (Invert Binary Tree, Lowest Common Ancestor, Palindrome Partitioning).',
  },
  {
    id: 'G-107',
    term: 'Abstract Data Type (ADT)',
    category: 'Data Structures',
    patterns: /\b(abstract data types?|ADTs?)\b/gi,
    definition: 'A specification of a set of data objects and operations that completely encapsulates internal representation details behind a public interface barrier.',
    primaryLocation: 'Chapter 10 (§ 10.1 Abstract Data Types and Classes, p. 157)',
    occurrences: [
      {
        chapter: 'Chapter 10',
        section: '§ 10.1 Abstract Data Types',
        pageRange: 'pp. 157–162',
        contextSnippet: 'ADTs enforce a data abstraction barrier between client code and implementation details.',
      },
      {
        chapter: 'Chapter 10',
        section: '§ 10.3 Queues',
        pageRange: 'pp. 165–168',
        contextSnippet: 'A Queue ADT specifies FIFO behavior (push, pop) regardless of whether backed by linked blocks or ring buffers.',
      },
    ],
    leetCodeRelevance: 'Design classes (Implement Stack using Queues, Implement Trie, Design HashMap).',
  },
  {
    id: 'G-108',
    term: 'Nonlocal & Stack Frame Scope',
    category: 'Memory & State',
    patterns: /\b(nonlocal|stack frames?|activation records?|lexical scope)\b/gi,
    definition: 'The execution activation record pushed onto the call stack for a function call. The nonlocal keyword explicitly binds identifier assignments to the nearest enclosing non-global scope.',
    primaryLocation: 'Chapter 4 (§ 4.1 Functions and Scoping, p. 46)',
    occurrences: [
      {
        chapter: 'Chapter 4',
        section: '§ 4.1 Functions and Scoping',
        pageRange: 'pp. 45–52',
        contextSnippet: 'Each function invocation allocates a stack frame storing local bindings according to the LEGB scope rules.',
      },
      {
        chapter: 'Chapter 6',
        section: '§ 6.3 Global and Nonlocal Variables',
        pageRange: 'pp. 94–96',
        contextSnippet: 'Nonlocal bindings allow nested recursive DFS helpers to mutate state variables in the outer coordinator frame.',
      },
    ],
    leetCodeRelevance: 'Enables clean DFS tree traversals that maintain max path sums or diameters without global variables.',
  },
  {
    id: 'G-109',
    term: 'Memoization',
    category: 'Optimization',
    patterns: /\b(memoization|memoized|memoizing|memo table)\b/gi,
    definition: 'An optimization technique in top-down dynamic programming where the results of expensive function calls are stored in a lookup table (dictionary) to prevent redundant recomputations of overlapping subproblems.',
    primaryLocation: 'Chapter 15 (§ 15.1 Fibonacci Numbers Revisited, p. 248)',
    occurrences: [
      {
        chapter: 'Chapter 15',
        section: '§ 15.1 Fibonacci Numbers Revisited',
        pageRange: 'pp. 248–252',
        contextSnippet: 'fastFib records subproblems in memo={0:0, 1:1}, reducing complexity from exponential O(2^n) to linear O(n).',
      },
      {
        chapter: 'Chapter 15',
        section: '§ 15.2 Dynamic Programming and 0/1 Knapsack',
        pageRange: 'pp. 252–258',
        contextSnippet: 'Memoizing (len(toConsider), avail) states prunes duplicate subtrees across the exponential decision tree.',
      },
    ],
    leetCodeRelevance: 'The core mechanic of Top-Down DP (Coin Change, Word Break, House Robber, Partition Equal Subset Sum).',
  },
  {
    id: 'G-110',
    term: 'Divide-and-Conquer',
    category: 'Algorithms',
    patterns: /\b(divide[- ]and[- ]conquer)\b/gi,
    definition: 'An algorithmic paradigm that breaks a problem into two or more independent subproblems of the same type, solves them recursively, and combines their solutions in polynomial time.',
    primaryLocation: 'Chapter 12 (§ 12.2 Sorting Algorithms, p. 201)',
    occurrences: [
      {
        chapter: 'Chapter 12',
        section: '§ 12.2 Sorting Algorithms',
        pageRange: 'pp. 201–206',
        contextSnippet: 'Merge sort divides a list in half, recursively sorts both sublists, and merges them in linear O(n) time.',
      },
      {
        chapter: 'Chapter 11',
        section: '§ 11.2 Asymptotic Notation',
        pageRange: 'pp. 184–186',
        contextSnippet: 'Divide-and-conquer recurrences of the form T(n) = 2T(n/2) + O(n) yield optimal O(n log n) running times.',
      },
    ],
    leetCodeRelevance: 'Powers Merge Intervals, Sort List, Merge k Sorted Lists, and Median of Two Sorted Arrays.',
  },
  {
    id: 'G-111',
    term: 'Asymptotic Complexity (Big-O)',
    category: 'Complexity',
    patterns: /\b(big[- ]o|asymptotic notation|asymptotic complexity|time complexity|space complexity)\b/gi,
    definition: 'A formal mathematical framework describing the limiting behavior of an algorithm\'s running time or memory usage as the input size n tends toward infinity: f(n) <= c * g(n).',
    primaryLocation: 'Chapter 11 (§ 11.2 Asymptotic Notation, p. 182)',
    occurrences: [
      {
        chapter: 'Chapter 11',
        section: '§ 11.2 Asymptotic Notation',
        pageRange: 'pp. 182–188',
        contextSnippet: 'Big-O notation establishes the worst-case upper bound on algorithmic growth classes: O(1) < O(log n) < O(n) < O(n log n) < O(n^2) < O(2^n).',
      },
      {
        chapter: 'Chapter 12',
        section: '§ 12.3 Hash Tables',
        pageRange: 'pp. 208–212',
        contextSnippet: 'Hash table average-case lookup is O(1), but degrades to O(n) under severe hash collision clustering.',
      },
    ],
    leetCodeRelevance: 'Interview standard for evaluating time and space bounds to prevent Time Limit Exceeded (TLE) or Memory Limit Exceeded (MLE).',
  },
  {
    id: 'G-112',
    term: 'FIFO Queue & Deque',
    category: 'Data Structures',
    patterns: /\b(fifo|deque|double[- ]ended queue|queue)\b/gi,
    definition: 'A First-In-First-Out data structure. collections.deque implements a doubly-linked buffer of fixed-size blocks providing O(1) pops and appends from both ends.',
    primaryLocation: 'Chapter 10 (§ 10.3 Object-Oriented Programming, p. 165)',
    occurrences: [
      {
        chapter: 'Chapter 10',
        section: '§ 10.3 Queues',
        pageRange: 'pp. 165–168',
        contextSnippet: 'list.pop(0) shifts all elements in memory taking O(N) time; deque.popleft() operates in O(1) time.',
      },
      {
        chapter: 'Chapter 14',
        section: '§ 14.2 Graph Optimization',
        pageRange: 'pp. 238–244',
        contextSnippet: 'Breadth-First Search (BFS) explores graphs level-by-level using a FIFO queue to guarantee shortest path optimality on unweighted graphs.',
      },
    ],
    leetCodeRelevance: 'Mandatory for BFS and sliding window problems (Word Ladder, Rotting Oranges, Sliding Window Maximum).',
  },
  {
    id: 'G-113',
    term: 'Modulo Invariant',
    category: 'Primitives',
    patterns: /\b(modulo|remainder|floor division|divmod)\b/gi,
    definition: 'The fundamental division identity enforced by Python: a == (a // b) * b + (a % b), where floor division // rounds down towards negative infinity.',
    primaryLocation: 'Chapter 2 (§ 2.1.1 Operators and Expressions, p. 14)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1.1 Operators',
        pageRange: 'pp. 14–16',
        contextSnippet: 'Floor division rounds toward negative infinity, ensuring that a % b always has the same sign as divisor b.',
      },
      {
        chapter: 'Chapter 12',
        section: '§ 12.3 Hash Tables',
        pageRange: 'pp. 209–212',
        contextSnippet: 'Hash functions use modulo hashing h(k) % numBuckets to distribute keys evenly across memory slots.',
      },
    ],
    leetCodeRelevance: 'Circular array indexing ((i + k) % n) and integer digit stripping (n % 10, n //= 10).',
  },
  {
    id: 'G-114',
    term: 'Bitmask & Hamming Weight',
    category: 'Algorithms',
    patterns: /\b(bitmasks?|bitwise|set bits?|hamming weight|popcount)\b/gi,
    definition: 'Compact binary representations where an integer is treated as a set of boolean flags. Brian Kernighan\'s formula n & (n - 1) clears the lowest set bit in O(1) hardware time.',
    primaryLocation: 'Chapter 3 (§ 3.3 Binary Representation, p. 37)',
    occurrences: [
      {
        chapter: 'Chapter 3',
        section: '§ 3.3 Binary Representation',
        pageRange: 'pp. 36–38',
        contextSnippet: 'Bitwise operators manipulate binary registers directly: 1 << i creates a mask, n & (n-1) clears the lowest set bit.',
      },
      {
        chapter: 'Chapter 14',
        section: '§ 14.1 Knapsack Problems',
        pageRange: 'pp. 233–236',
        contextSnippet: 'Generating subsets of n items corresponds to counting from 0 to 2^n - 1 in binary bitmasks.',
      },
    ],
    leetCodeRelevance: 'State compression in Bitmask DP (Shortest Path Visiting All Nodes, Single Number, Subsets).',
  },
  {
    id: 'G-115',
    term: 'Space-Time Tradeoff (Prefix Sums)',
    category: 'Optimization',
    patterns: /\b(space[- ]time tradeoffs?|prefix sums?|precomputation)\b/gi,
    definition: 'The computational design principle of utilizing auxiliary memory to cache precomputed intermediate calculations so future range queries can be evaluated in constant O(1) time.',
    primaryLocation: 'Chapter 11 (§ 11.3 Amortization and Space-Time Tradeoffs, p. 188)',
    occurrences: [
      {
        chapter: 'Chapter 11',
        section: '§ 11.3 Space-Time Tradeoffs',
        pageRange: 'pp. 188–191',
        contextSnippet: 'Prefix sum arrays P[i] = P[i-1] + A[i-1] answer any subarray sum query sum(L, R) = P[R+1] - P[L] in O(1) time.',
      },
      {
        chapter: 'Chapter 15',
        section: '§ 15.1 Dynamic Programming',
        pageRange: 'pp. 248–250',
        contextSnippet: 'Dynamic programming is the ultimate space-time tradeoff: storing subproblems in memory avoids exponential recalculation.',
      },
    ],
    leetCodeRelevance: 'Subarray Sum Equals K, Range Sum Query, Product of Array Except Self.',
  },
  {
    id: 'G-116',
    term: '0/1 Decision Tree',
    category: 'Optimization',
    patterns: /\b(decision trees?|0\/1 knapsack|knapsack problems?)\b/gi,
    definition: 'A binary tree modeling state choices at each item i: branch left to include item i (take), branch right to exclude item i (leave). Pruned to polynomial size O(n*W) via state memoization (i, avail).',
    primaryLocation: 'Chapter 14 (§ 14.1 Knapsack) & Chapter 15 (§ 15.2 DP), pp. 232–257',
    occurrences: [
      {
        chapter: 'Chapter 14',
        section: '§ 14.1 Knapsack Problems',
        pageRange: 'pp. 232–238',
        contextSnippet: 'The 0/1 knapsack decision tree explores 2^n leaves in brute force, but many nodes represent identical subproblems.',
      },
      {
        chapter: 'Chapter 15',
        section: '§ 15.2 Dynamic Programming',
        pageRange: 'pp. 252–257',
        contextSnippet: 'By memoizing (i, available_weight), the decision tree is bounded by O(n * W) states.',
      },
    ],
    leetCodeRelevance: 'Target Sum, Partition Equal Subset Sum, Ones and Zeroes.',
  },
]

/**
 * Finds a matching ConcordanceEntry for a given token string.
 */
export function findConcordanceMatch(text: string): ConcordanceEntry | null {
  const trimmed = text.trim()
  if (!trimmed) return null
  for (const entry of GUTTAG_CONCORDANCE_LEXICON) {
    entry.patterns.lastIndex = 0
    if (entry.patterns.test(trimmed)) {
      return entry
    }
  }
  return null
}

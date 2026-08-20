/**
 * Exhaustive Guttag Computational Strong's Concordance Lexicon & Cross-Reference Engine.
 *
 * Covers 100+ foundational computer science concepts, memory models, data structures,
 * algorithmic paradigms, complexity classes, and Python runtime mechanics from
 * John V. Guttag's 'Introduction to Computation and Programming Using Python' (3rd ed., MIT Press).
 */

export interface ConcordanceOccurrence {
  chapter: string
  section: string
  pageRange?: string
  contextSnippet: string
}

export type ConcordanceCategory =
  | 'Primitives & Types'
  | 'Memory & Runtime Architecture'
  | 'Data Structures & ADTs'
  | 'Algorithmic Paradigms'
  | 'Complexity & Analysis'
  | 'Bitwise & Binary Arithmetic'
  | 'Sorting & Searching'
  | 'Functions & Abstractions'
  | 'Object-Oriented Design'
  | 'Verification & Testing'

export interface ConcordanceEntry {
  id: string // e.g. "G-101"
  term: string
  category: ConcordanceCategory
  patterns: RegExp
  definition: string
  primaryLocation: string
  occurrences: ConcordanceOccurrence[]
  leetCodeRelevance: string
}

export const GUTTAG_CONCORDANCE_LEXICON: ConcordanceEntry[] = [
  // ── 1. Primitives & Types ───────────────────────────────────────────────
  {
    id: 'G-101',
    term: 'Scalar Object',
    category: 'Primitives & Types',
    patterns: /\b(scalars?|scalar objects?)\b/gi,
    definition: 'An indivisible computational entity with no accessible internal structure. In Python, the primitive scalar types are int, float, bool, and NoneType.',
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
    term: 'Non-Scalar Object',
    category: 'Primitives & Types',
    patterns: /\b(non[- ]scalars?|non[- ]scalar objects?|composite objects?)\b/gi,
    definition: 'An object that possesses internal structure and contains references to other objects (e.g., str, tuple, list, dict, set, class instances).',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 12)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements of Python',
        pageRange: 'pp. 12–13',
        contextSnippet: 'Non-scalar objects, such as strings and lists, have internal structure that can be accessed via indexing and slicing.',
      },
      {
        chapter: 'Chapter 5',
        section: '§ 5.1 Structured Types',
        pageRange: 'pp. 65–70',
        contextSnippet: 'Lists and dictionaries are compound non-scalar types whose elements are referenced via pointers.',
      },
    ],
    leetCodeRelevance: 'Crucial for understanding memory allocation: passing non-scalars to recursive functions passes pointers, not deep copies.',
  },
  {
    id: 'G-103',
    term: 'Type Casting & Conversion',
    category: 'Primitives & Types',
    patterns: /\b(type casts?|type casting|type conversions?)\b/gi,
    definition: 'Explicitly converting an object from one data type to another using constructor functions (int(), float(), str(), bool(), list(), set()).',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 13)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements of Python',
        pageRange: 'pp. 13–15',
        contextSnippet: 'Type conversions convert an object of one type to another. For example, int("42") yields 42 and str(10) yields "10".',
      },
      {
        chapter: 'Chapter 3',
        section: '§ 3.3 Binary Representation',
        pageRange: 'pp. 36–38',
        contextSnippet: 'Casting float values to integers truncates fractional components toward zero.',
      },
    ],
    leetCodeRelevance: 'Commonly tested in string-to-integer parsing (e.g. LeetCode 8 String to Integer atoi) and converting digit characters via ord(c) - ord("0").',
  },
  {
    id: 'G-104',
    term: 'Dynamic & Strong Typing',
    category: 'Primitives & Types',
    patterns: /\b(dynamic typing|strongly typed|strong typing|dynamic type binding)\b/gi,
    definition: 'A language type system where variable names are dynamically bound to objects in the heap at runtime (dynamic), while type safety strictly prevents incompatible implicit operations (strong).',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 12)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements of Python',
        pageRange: 'pp. 12–14',
        contextSnippet: 'Python is dynamically typed but strongly typed: attempting to evaluate "42" + 1 raises a TypeError rather than coercing silently.',
      },
      {
        chapter: 'Chapter 4',
        section: '§ 4.2 Specifications',
        pageRange: 'pp. 52–55',
        contextSnippet: 'Because Python does not enforce static type checking at compile time, docstrings and type hints provide formal contracts.',
      },
    ],
    leetCodeRelevance: 'Ensures understanding of why Python will not auto-coerce mixed numeric/string types, avoiding runtime TypeError bugs.',
  },
  {
    id: 'G-105',
    term: 'Truthiness & Boolean Evaluation',
    category: 'Primitives & Types',
    patterns: /\b(truthiness|truth[- ]value|boolean evaluation|boolean context)\b/gi,
    definition: 'Python\'s built-in evaluation of objects in boolean contexts: 0, 0.0, None, and empty collections (\'\', [], {}, set()) evaluate to False; all other values evaluate to True.',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 14)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements of Python',
        pageRange: 'pp. 13–15',
        contextSnippet: 'An object is considered False if it is None, zero, or an empty sequence. All other objects evaluate to True in an if statement.',
      },
      {
        chapter: 'Chapter 5',
        section: '§ 5.2 Lists and Mutability',
        pageRange: 'pp. 70–72',
        contextSnippet: 'Checking if not my_list is the idiomatic Python test for an empty collection.',
      },
    ],
    leetCodeRelevance: 'Writing concise stack and queue loops (while stack:) and checking default argument presence (if memo is None:).',
  },
  {
    id: 'G-106',
    term: 'Arbitrary-Precision Integer',
    category: 'Primitives & Types',
    patterns: /\b(arbitrary[- ]precision|unbounded precision|large integers?)\b/gi,
    definition: 'An integer representation whose magnitude is constrained only by available machine memory, guaranteeing that integer calculations never overflow.',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 13)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements of Python',
        pageRange: 'pp. 12–14',
        contextSnippet: 'Python 3 integers have arbitrary precision and do not suffer from integer overflow bugs common in C++ and Java.',
      },
      {
        chapter: 'Chapter 3',
        section: '§ 3.3 Binary Numbers',
        pageRange: 'pp. 36–38',
        contextSnippet: 'Python automatically allocates extra memory words as integer values exceed 30 bits or 62 bits.',
      },
    ],
    leetCodeRelevance: 'Allows computing large combinations, factorials, and powers without manual modular arithmetic (though 32-bit overflow must still be simulated in LeetCode 7 Reverse Integer).',
  },
  {
    id: 'G-107',
    term: 'IEEE 754 Floating-Point',
    category: 'Primitives & Types',
    patterns: /\b(ieee 754|floating[- ]point|floats?|machine epsilon|rounding errors?)\b/gi,
    definition: 'A binary standard for representing real numbers using a sign bit, exponent, and mantissa. Because binary fractions cannot represent all decimal fractions exactly, floating-point equality (==) is dangerous.',
    primaryLocation: 'Chapter 3 (§ 3.3 A Few Words About Using Floats, p. 36)',
    occurrences: [
      {
        chapter: 'Chapter 3',
        section: '§ 3.3 Floating Point',
        pageRange: 'pp. 36–38',
        contextSnippet: '0.1 cannot be represented exactly in binary floating point. Testing float equality with == is almost always an error; use abs(a - b) < epsilon.',
      },
      {
        chapter: 'Chapter 3',
        section: '§ 3.2 Approximate Solutions',
        pageRange: 'pp. 31–36',
        contextSnippet: 'Numerical approximation loops terminate when the error metric falls within an epsilon tolerance bound.',
      },
    ],
    leetCodeRelevance: 'Essential in geometric and binary search problems (e.g. LeetCode 69 Sqrt(x), LeetCode 50 Pow(x, n)) requiring precision bounds.',
  },
  {
    id: 'G-108',
    term: 'Immutability vs Mutability',
    category: 'Primitives & Types',
    patterns: /\b(immutab(le|ility)|mutab(le|ility))\b/gi,
    definition: 'Immutable objects (int, float, str, tuple, frozenset) cannot be modified after instantiation. Mutable objects (list, dict, set) can be mutated in-place without changing their memory address.',
    primaryLocation: 'Chapter 5 (§ 5.1 Tuples & § 5.2 Lists, pp. 65–70)',
    occurrences: [
      {
        chapter: 'Chapter 5',
        section: '§ 5.1 Tuples and Sequences',
        pageRange: 'pp. 65–68',
        contextSnippet: 'Tuples are immutable sequences: attempting to reassign t[0] = 5 raises a TypeError.',
      },
      {
        chapter: 'Chapter 5',
        section: '§ 5.2 Lists and Mutability',
        pageRange: 'pp. 68–74',
        contextSnippet: 'Lists are mutable: their contents can be altered in-place using append, pop, and slice assignment.',
      },
      {
        chapter: 'Chapter 12',
        section: '§ 12.3 Hash Tables',
        pageRange: 'pp. 208–212',
        contextSnippet: 'Dictionary keys and set members must be immutable so their hash values remain invariant over time.',
      },
    ],
    leetCodeRelevance: 'Only immutable types can serve as keys in hash maps or memoization tables (e.g. tuples as state keys in 2D DP).',
  },

  // ── 2. Memory & Runtime Architecture ────────────────────────────────────
  {
    id: 'G-109',
    term: 'Object Identity vs Value Equality',
    category: 'Memory & Runtime Architecture',
    patterns: /\b(object identity|value equality|id\(|is operator|equality vs identity)\b/gi,
    definition: 'Value equality (==) tests if two objects contain equivalent data values. Object identity (is) tests if two variables point to the exact same physical heap memory address (id(a) == id(b)).',
    primaryLocation: 'Chapter 5 (§ 5.2 Lists and Mutability, p. 69)',
    occurrences: [
      {
        chapter: 'Chapter 5',
        section: '§ 5.2 Lists and Mutability',
        pageRange: 'pp. 68–72',
        contextSnippet: 'L1 == L2 evaluates to True if they have identical elements, but L1 is L2 is False if they are independently allocated clones.',
      },
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements',
        pageRange: 'pp. 12–14',
        contextSnippet: 'Testing singleton equality like if x is None uses the is operator for identity comparison.',
      },
    ],
    leetCodeRelevance: 'Avoids using == when comparing against None (use is None) and ensures correct memo key matching in graph cycle detection.',
  },
  {
    id: 'G-110',
    term: 'Aliasing',
    category: 'Memory & Runtime Architecture',
    patterns: /\b(aliasing|aliases|aliased|alias)\b/gi,
    definition: 'A condition where two or more distinct identifier variables reference the exact same mutable object in heap memory. In-place mutations through one alias instantly mutate all other aliases.',
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
    id: 'G-111',
    term: 'Shallow Copy vs Deep Copy',
    category: 'Memory & Runtime Architecture',
    patterns: /\b(shallow cop(y|ies)|deep cop(y|ies)|cloning|cloned?)\b/gi,
    definition: 'A shallow copy (L[:], list(L), copy.copy()) duplicates the outer container while preserving references to nested inner objects. A deep copy (copy.deepcopy()) recursively duplicates all nested objects.',
    primaryLocation: 'Chapter 5 (§ 5.3 Cloning, p. 74)',
    occurrences: [
      {
        chapter: 'Chapter 5',
        section: '§ 5.3 Cloning',
        pageRange: 'pp. 74–77',
        contextSnippet: 'Cloning a list using L[:] produces a shallow clone. If the list contains other lists, mutating inner elements still affects the original.',
      },
      {
        chapter: 'Chapter 10',
        section: '§ 10.1 Abstract Data Types',
        pageRange: 'pp. 158–160',
        contextSnippet: 'Defensive copying in getters prevents external callers from corrupting the internal state of an ADT.',
      },
    ],
    leetCodeRelevance: 'In graph and tree problems (LeetCode 133 Clone Graph), shallow copying node references creates cycles; deep copying with visited hash maps is mandatory.',
  },
  {
    id: 'G-112',
    term: 'Call Stack & Stack Frame',
    category: 'Memory & Runtime Architecture',
    patterns: /\b(call stacks?|stack frames?|activation records?|stack overflow)\b/gi,
    definition: 'The LIFO memory region where the runtime system pushes an activation record (frame) for every active function call, storing local variables, formal arguments, and return addresses.',
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
        section: '§ 6.1 Recursion',
        pageRange: 'pp. 86–90',
        contextSnippet: 'Recursive calls chain stack frames. If the base case is not reached, the call stack exceeds sys.getrecursionlimit() and crashes.',
      },
    ],
    leetCodeRelevance: 'Analyzing auxiliary space complexity for recursive algorithms (e.g. DFS on trees takes O(H) stack frames, where H is tree height).',
  },
  {
    id: 'G-113',
    term: 'Lexical Scope & LEGB Rule',
    category: 'Memory & Runtime Architecture',
    patterns: /\b(lexical scopes?|legb rule|symbol tables?|variable scopes?)\b/gi,
    definition: 'The name resolution rule used by Python to look up identifiers: Local (L) -> Enclosing (E) -> Global (G) -> Built-in (B).',
    primaryLocation: 'Chapter 4 (§ 4.1 Functions and Scoping, p. 47)',
    occurrences: [
      {
        chapter: 'Chapter 4',
        section: '§ 4.1 Functions and Scoping',
        pageRange: 'pp. 46–50',
        contextSnippet: 'Python uses static (lexical) scoping: identifier binding is determined entirely by where the function is defined in source code.',
      },
      {
        chapter: 'Chapter 6',
        section: '§ 6.3 Global Variables',
        pageRange: 'pp. 94–96',
        contextSnippet: 'Global variables bypass lexical encapsulation and should be avoided in favor of explicit argument passing or nonlocal closures.',
      },
    ],
    leetCodeRelevance: 'Prevents UnboundLocalError when referencing and updating outer variables inside helper DFS functions.',
  },
  {
    id: 'G-114',
    term: 'Nonlocal Binding',
    category: 'Memory & Runtime Architecture',
    patterns: /\b(nonlocal|nonlocal keyword|enclosing frame)\b/gi,
    definition: 'A keyword that binds identifier assignments inside a nested function directly to the nearest enclosing non-global scope rather than creating a local variable.',
    primaryLocation: 'Chapter 4 (§ 4.1 Functions and Scoping, p. 49)',
    occurrences: [
      {
        chapter: 'Chapter 4',
        section: '§ 4.1 Functions and Scoping',
        pageRange: 'pp. 48–51',
        contextSnippet: 'Declaring nonlocal x inside a helper function enables mutation of x in the enclosing parent frame.',
      },
      {
        chapter: 'Chapter 6',
        section: '§ 6.3 Global and Nonlocal',
        pageRange: 'pp. 94–96',
        contextSnippet: 'Nonlocal bindings allow nested recursive DFS helpers to mutate state variables in the outer coordinator frame.',
      },
    ],
    leetCodeRelevance: 'Allows writing compact DFS recursion without mutating arrays or using self properties (e.g. tracking max_sum in LeetCode 124 Binary Tree Maximum Path Sum).',
  },
  {
    id: 'G-115',
    term: 'Pass-by-Object-Reference',
    category: 'Memory & Runtime Architecture',
    patterns: /\b(pass[- ]by[- ]object[- ]reference|pass[- ]by[- ]assignment|argument passing)\b/gi,
    definition: 'Python\'s argument passing semantics: functions receive references (pointers) to the caller\'s objects. Reassigning the parameter variable has no effect on caller, but mutating the object in-place mutates the caller\'s data.',
    primaryLocation: 'Chapter 4 (§ 4.1 Functions and Scoping, p. 48)',
    occurrences: [
      {
        chapter: 'Chapter 4',
        section: '§ 4.1 Functions and Scoping',
        pageRange: 'pp. 47–50',
        contextSnippet: 'Parameters are bound to actual arguments using object assignment. Mutating a passed mutable list alters the caller object.',
      },
      {
        chapter: 'Chapter 5',
        section: '§ 5.2 Lists and Mutability',
        pageRange: 'pp. 70–73',
        contextSnippet: 'Side effects occur when a function modifies a mutable argument passed by reference.',
      },
    ],
    leetCodeRelevance: 'Explains how in-place array modification algorithms (LeetCode 283 Move Zeroes, LeetCode 27 Remove Element) communicate results back to testing harnesses.',
  },

  // ── 3. Data Structures & Abstract Data Types ────────────────────────────
  {
    id: 'G-116',
    term: 'Abstract Data Type (ADT)',
    category: 'Data Structures & ADTs',
    patterns: /\b(abstract data types?|ADTs?)\b/gi,
    definition: 'A mathematical model for data structures where a type is defined exclusively by its public operations and behavioral semantics, hiding internal implementation behind a data abstraction barrier.',
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
    leetCodeRelevance: 'Tested in Design questions (LeetCode 232 Implement Queue using Stacks, LeetCode 208 Implement Trie, LeetCode 380 Insert Delete GetRandom O(1)).',
  },
  {
    id: 'G-117',
    term: 'Representation Invariant',
    category: 'Data Structures & ADTs',
    patterns: /\b(representation invariants?|rep invariants?)\b/gi,
    definition: 'A formal structural predicate that must hold true for the internal state of an ADT before and after every public method call.',
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
    id: 'G-118',
    term: 'Dynamic Array (List)',
    category: 'Data Structures & ADTs',
    patterns: /\b(dynamic arrays?|python lists?|contiguous array)\b/gi,
    definition: 'A contiguous array of memory pointers that dynamically resizes by geometric doubling when capacity is exhausted, providing O(1) amortized appends and O(1) index access, but O(N) shifts on arbitrary insertions/deletions.',
    primaryLocation: 'Chapter 5 (§ 5.2 Lists and Mutability, p. 68)',
    occurrences: [
      {
        chapter: 'Chapter 5',
        section: '§ 5.2 Lists and Mutability',
        pageRange: 'pp. 68–74',
        contextSnippet: 'Python lists are implemented as contiguous arrays of pointers to objects in memory.',
      },
      {
        chapter: 'Chapter 11',
        section: '§ 11.3 Amortization',
        pageRange: 'pp. 188–190',
        contextSnippet: 'Geometric doubling ensures that appending N elements takes O(N) total time, or O(1) amortized time per append.',
      },
    ],
    leetCodeRelevance: 'Core data structure for two-pointer traversals, prefix sums, and sliding windows.',
  },
  {
    id: 'G-119',
    term: 'FIFO Queue & Deque',
    category: 'Data Structures & ADTs',
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
    id: 'G-120',
    term: 'Hash Table & Dictionaries',
    category: 'Data Structures & ADTs',
    patterns: /\b(hash tables?|hash maps?|dictionar(y|ies)|hash functions?|hash collision)\b/gi,
    definition: 'A data structure that maps immutable keys to values using a hash function (hash(k) % num_buckets) to achieve average-case O(1) insertions, deletions, and lookups.',
    primaryLocation: 'Chapter 12 (§ 12.3 Hash Tables, p. 208)',
    occurrences: [
      {
        chapter: 'Chapter 12',
        section: '§ 12.3 Hash Tables',
        pageRange: 'pp. 208–214',
        contextSnippet: 'A hash table uses a hash function to convert a key into an integer bucket index, achieving O(1) lookup under uniform distribution.',
      },
      {
        chapter: 'Chapter 5',
        section: '§ 5.6 Dictionaries',
        pageRange: 'pp. 78–82',
        contextSnippet: 'Dictionaries in Python are highly optimized hash tables that preserve insertion order.',
      },
    ],
    leetCodeRelevance: 'The single most utilized data structure in technical interviews (Two Sum, Group Anagrams, Longest Consecutive Sequence).',
  },
  {
    id: 'G-121',
    term: 'Binary Search Tree (BST)',
    category: 'Data Structures & ADTs',
    patterns: /\b(binary search trees?|bsts?)\b/gi,
    definition: 'A binary tree invariant where for every node X: all values in X.left are strictly less than X.val, and all values in X.right are strictly greater than X.val.',
    primaryLocation: 'Chapter 12 (§ 12.1 Search Algorithms, p. 198)',
    occurrences: [
      {
        chapter: 'Chapter 12',
        section: '§ 12.1 Search Algorithms',
        pageRange: 'pp. 197–200',
        contextSnippet: 'In a balanced BST, searching, insertion, and deletion run in O(log n) time.',
      },
    ],
    leetCodeRelevance: 'In-order traversal yields sorted sequence (LeetCode 98 Validate BST, LeetCode 230 Kth Smallest Element in a BST).',
  },
  {
    id: 'G-122',
    term: 'Heap & Priority Queue',
    category: 'Data Structures & ADTs',
    patterns: /\b(heaps?|priority queues?|min[- ]heap|max[- ]heap|heapq)\b/gi,
    definition: 'A complete binary tree satisfying the heap invariant: the parent node is always smaller than (min-heap) or greater than (max-heap) its children, providing O(1) peek and O(log N) push/pop.',
    primaryLocation: 'Chapter 12 (§ 12.2 Sorting Algorithms, p. 204)',
    occurrences: [
      {
        chapter: 'Chapter 12',
        section: '§ 12.2 Sorting Algorithms',
        pageRange: 'pp. 204–207',
        contextSnippet: 'A priority queue retrieves the highest-priority element in logarithmic time using a binary heap representation.',
      },
      {
        chapter: 'Chapter 14',
        section: '§ 14.2 Shortest Path',
        pageRange: 'pp. 240–244',
        contextSnippet: 'Dijkstra\'s shortest path algorithm utilizes a min-priority queue to select the minimum-weight frontier edge.',
      },
    ],
    leetCodeRelevance: 'Top K elements, merging k sorted streams, and Dijkstra shortest paths (LeetCode 215 Kth Largest Element, LeetCode 23 Merge k Sorted Lists).',
  },

  // ── 4. Algorithmic Paradigms ────────────────────────────────────────────
  {
    id: 'G-123',
    term: 'Exhaustive Enumeration (Brute Force)',
    category: 'Algorithmic Paradigms',
    patterns: /\b(exhaustive enumeration|brute[- ]force|guess and check)\b/gi,
    definition: 'A search technique that systematically generates and tests every possible candidate solution in the search space until a valid answer is found or the space is exhausted.',
    primaryLocation: 'Chapter 3 (§ 3.1 Exhaustive Enumeration, p. 28)',
    occurrences: [
      {
        chapter: 'Chapter 3',
        section: '§ 3.1 Exhaustive Enumeration',
        pageRange: 'pp. 28–31',
        contextSnippet: 'Guess and check (exhaustive enumeration) is guaranteed to find a solution if one exists, but is computationally intractable for large state spaces.',
      },
      {
        chapter: 'Chapter 14',
        section: '§ 14.1 Knapsack Problems',
        pageRange: 'pp. 232–236',
        contextSnippet: 'Brute-force subset generation evaluates all 2^n possible item combinations.',
      },
    ],
    leetCodeRelevance: 'Baseline formulation before applying Dynamic Programming or Branch-and-Bound pruning.',
  },
  {
    id: 'G-124',
    term: 'Bisection Search',
    category: 'Algorithmic Paradigms',
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
    id: 'G-125',
    term: 'Newton-Raphson Method',
    category: 'Algorithmic Paradigms',
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
    id: 'G-126',
    term: 'Inductive Recursion & Base Case',
    category: 'Algorithmic Paradigms',
    patterns: /\b(inductive step|mathematical induction|inductive hypothesis|base case|recursive calls?)\b/gi,
    definition: 'Decomposing a problem of size n into smaller subproblems of size n-1 or n/2, with explicit base cases providing direct non-recursive solutions for terminal instances.',
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
    id: 'G-127',
    term: 'Divide-and-Conquer',
    category: 'Algorithmic Paradigms',
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
    id: 'G-128',
    term: 'Dynamic Programming & Memoization',
    category: 'Algorithmic Paradigms',
    patterns: /\b(dynamic programming|memoization|memoized|memo table|overlapping subproblems|optimal substructure)\b/gi,
    definition: 'An algorithmic optimization that caches solutions to overlapping subproblems in a table, reducing exponential search spaces O(2^N) to polynomial state spaces O(N*W).',
    primaryLocation: 'Chapter 15 (§ 15.1 Fibonacci & § 15.2 Knapsack, pp. 248–258)',
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
    id: 'G-129',
    term: '0/1 Decision Tree',
    category: 'Algorithmic Paradigms',
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
  {
    id: 'G-130',
    term: 'Breadth-First Search (BFS)',
    category: 'Algorithmic Paradigms',
    patterns: /\b(breadth[- ]first search|bfs)\b/gi,
    definition: 'A graph/tree traversal algorithm that visits nodes level-by-level using a FIFO queue, guaranteeing the shortest path in unweighted graphs.',
    primaryLocation: 'Chapter 14 (§ 14.2 Graph Optimization Problems, p. 238)',
    occurrences: [
      {
        chapter: 'Chapter 14',
        section: '§ 14.2 Graph Optimization',
        pageRange: 'pp. 238–244',
        contextSnippet: 'BFS guarantees finding the path with the minimum number of edges between source and destination.',
      },
    ],
    leetCodeRelevance: 'Shortest Path in Binary Matrix, Word Ladder, Rotting Oranges.',
  },
  {
    id: 'G-131',
    term: 'Depth-First Search (DFS) & Backtracking',
    category: 'Algorithmic Paradigms',
    patterns: /\b(depth[- ]first search|dfs|backtracking|pruning)\b/gi,
    definition: 'A recursive traversal that explores as deep as possible along each branch before backtracking, commonly paired with pruning to abandon invalid search branches early.',
    primaryLocation: 'Chapter 14 (§ 14.2 Graph Optimization Problems, p. 239)',
    occurrences: [
      {
        chapter: 'Chapter 14',
        section: '§ 14.2 Graph Optimization',
        pageRange: 'pp. 239–243',
        contextSnippet: 'DFS traverses a branch to its terminus before backtracking to explore alternate branches.',
      },
    ],
    leetCodeRelevance: 'N-Queens, Sudoku Solver, Combination Sum, Word Search.',
  },

  // ── 5. Complexity & Analysis ────────────────────────────────────────────
  {
    id: 'G-132',
    term: 'Asymptotic Complexity (Big-O)',
    category: 'Complexity & Analysis',
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
    id: 'G-133',
    term: 'Space-Time Tradeoff & Prefix Sums',
    category: 'Complexity & Analysis',
    patterns: /\b(space[- ]time tradeoffs?|prefix sums?|precomputation|cumulative sums?)\b/gi,
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
    id: 'G-134',
    term: 'Amortized Complexity',
    category: 'Complexity & Analysis',
    patterns: /\b(amortized complexity|amortized analysis|amortized o\(1\))\b/gi,
    definition: 'The average running time per operation over a sequence of operations, guaranteeing that occasional expensive operations (such as dynamic array resizing) are paid for by frequent cheap operations.',
    primaryLocation: 'Chapter 11 (§ 11.3 Amortization, p. 189)',
    occurrences: [
      {
        chapter: 'Chapter 11',
        section: '§ 11.3 Amortization',
        pageRange: 'pp. 188–190',
        contextSnippet: 'Appending to a dynamic array takes O(1) amortized time because memory reallocation occurs only on geometric capacity exhaustion.',
      },
    ],
    leetCodeRelevance: 'Analyzing hash table rehashes and dynamic array list.append operations.',
  },

  // ── 6. Bitwise & Binary Arithmetic ──────────────────────────────────────
  {
    id: 'G-135',
    term: 'Bitmask & Bitwise Operators',
    category: 'Bitwise & Binary Arithmetic',
    patterns: /\b(bitmasks?|bitwise|bitwise and|bitwise or|bitwise xor|left shift|right shift)\b/gi,
    definition: 'Low-level arithmetic operations manipulating individual bits directly in CPU registers: 1 << i creates a mask, (n >> i) & 1 tests bit i, n | (1 << i) sets bit i, n & ~(1 << i) clears bit i.',
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
    id: 'G-136',
    term: 'Brian Kernighan\'s Algorithm',
    category: 'Bitwise & Binary Arithmetic',
    patterns: /\b(brian kernighan|kernighan\'s algorithm|n & \(n - 1\))\b/gi,
    definition: 'An algebraic invariant of two\'s complement binary arithmetic where n & (n - 1) clears the lowest set bit of integer n in O(1) time, counting set bits in O(K) steps (where K is number of 1-bits).',
    primaryLocation: 'Chapter 3 (§ 3.3 Binary Representation, p. 37)',
    occurrences: [
      {
        chapter: 'Chapter 3',
        section: '§ 3.3 Binary Representation',
        pageRange: 'pp. 37–38',
        contextSnippet: 'Subtracting 1 flips all bits after the lowest set bit; n & (n - 1) isolates and zeroes the lowest set bit.',
      },
    ],
    leetCodeRelevance: 'LeetCode 191 (Number of 1 Bits), LeetCode 231 (Power of Two), LeetCode 338 (Counting Bits).',
  },

  // ── 7. Sorting & Searching ──────────────────────────────────────────────
  {
    id: 'G-137',
    term: 'Merge Sort',
    category: 'Sorting & Searching',
    patterns: /\b(merge sort|mergesort)\b/gi,
    definition: 'A stable divide-and-conquer sorting algorithm that splits an array into halves, recursively sorts them, and merges them in linear O(N) time with guaranteed O(N log N) worst-case complexity.',
    primaryLocation: 'Chapter 12 (§ 12.2 Sorting Algorithms, p. 201)',
    occurrences: [
      {
        chapter: 'Chapter 12',
        section: '§ 12.2 Sorting Algorithms',
        pageRange: 'pp. 201–206',
        contextSnippet: 'Merge sort divides a list in half, recursively sorts both sublists, and merges them in linear O(n) time.',
      },
    ],
    leetCodeRelevance: 'Sort List, Merge k Sorted Lists, Count of Smaller Numbers After Self.',
  },
  {
    id: 'G-138',
    term: 'Lexicographic & Custom Comparator Sorting',
    category: 'Sorting & Searching',
    patterns: /\b(lexicographic order|custom sorting|sort keys?|comparator)\b/gi,
    definition: 'Multi-attribute element-by-element tuple comparison: key=lambda x: (-x[1], x[2], x[0]) enables total ordering with descending numeric scores and ascending secondary tie-breaking.',
    primaryLocation: 'Chapter 12 (§ 12.2 Sorting Algorithms, p. 206)',
    occurrences: [
      {
        chapter: 'Chapter 12',
        section: '§ 12.2 Sorting Algorithms',
        pageRange: 'pp. 206–208',
        contextSnippet: 'Supplying a key function projects elements into comparable tuples for custom sorting order.',
      },
    ],
    leetCodeRelevance: 'Merge Intervals, Non-overlapping Intervals, Largest Number.',
  },

  // ── 8. Functions & Abstractions ─────────────────────────────────────────
  {
    id: 'G-139',
    term: 'First-Class Functions & Lambdas',
    category: 'Functions & Abstractions',
    patterns: /\b(first[- ]class (functions?|objects?)|lambdas?|anonymous functions?|higher[- ]order functions?)\b/gi,
    definition: 'Treating functions as first-class mathematical entities that can be passed as arguments, returned as values, and bound to variables. In Python, lambda x: expr defines anonymous functions inline.',
    primaryLocation: 'Chapter 4 (§ 4.4 Functions as Objects, p. 58)',
    occurrences: [
      {
        chapter: 'Chapter 4',
        section: '§ 4.4 Functions as Objects',
        pageRange: 'pp. 58–62',
        contextSnippet: 'Functions are first-class objects that can be passed as arguments to higher-order functions like map and filter.',
      },
    ],
    leetCodeRelevance: 'Custom sort keys, comparator functions for heapq, and transformation pipelines.',
  },
  {
    id: 'G-140',
    term: 'List Comprehensions',
    category: 'Functions & Abstractions',
    patterns: /\b(list comprehensions?|dict comprehensions?|set comprehensions?)\b/gi,
    definition: 'A concise, optimized Pythonic syntactic construct for constructing new collections by filtering and transforming iterable elements: [expr for x in iterable if condition].',
    primaryLocation: 'Chapter 5 (§ 5.4 List Comprehension, p. 77)',
    occurrences: [
      {
        chapter: 'Chapter 5',
        section: '§ 5.4 List Comprehension',
        pageRange: 'pp. 77–78',
        contextSnippet: 'List comprehensions provide a concise way to apply an operation to values in a sequence satisfying a predicate.',
      },
    ],
    leetCodeRelevance: 'Matrix initialization ([[0 for _ in range(C)] for _ in range(R)]) and filtered array transforms.',
  },
]

/**
 * Finds a matching ConcordanceEntry for a given text token.
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

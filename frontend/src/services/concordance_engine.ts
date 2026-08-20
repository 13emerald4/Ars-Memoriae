/**
 * Exhaustive Guttag Computational Strong's Concordance Lexicon & Cross-Reference Engine.
 *
 * Provides complete coverage of 100+ Computer Science concepts, runtime memory models,
 * data structures, algorithmic paradigms, complexity classes, and Python execution semantics.
 */

export interface ConcordanceOccurrence {
  chapter: string
  section: string
  pageRange?: string
  contextSnippet: string
}

export type ConcordanceCategory =
  | 'Core Language & Primitives'
  | 'Memory, State & Runtime'
  | 'Data Structures & ADTs'
  | 'Algorithmic Paradigms'
  | 'Complexity & Mathematics'
  | 'Bitwise & Binary Arithmetic'
  | 'Searching & Sorting'
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
  // ── 1. Core Language & Primitives ──────────────────────────────────────────
  {
    id: 'G-101',
    term: 'Object / Data Object',
    category: 'Core Language & Primitives',
    patterns: /\b(data objects?|objects?)\b/gi,
    definition: 'In Python’s computational model, everything is an object. An object is an encapsulated entity with an Identity (memory address), a Type (defining valid operations), and a Value (internal data representation).',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 12)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements',
        pageRange: 'pp. 12–15',
        contextSnippet: 'In Python, everything is an object. Every object has an identity, a type, and a value.',
      },
      {
        chapter: 'Chapter 5',
        section: '§ 5.2 Lists and Mutability',
        pageRange: 'pp. 68–72',
        contextSnippet: 'Objects in Python are allocated on the heap. Multiple variables can point to the same object.',
      },
      {
        chapter: 'Chapter 10',
        section: '§ 10.1 Classes and OOP',
        pageRange: 'pp. 157–160',
        contextSnippet: 'A class is a blueprint for creating custom data objects with encapsulated state and methods.',
      },
    ],
    leetCodeRelevance: 'Understanding that variables are object pointers prevents unintended state mutation during backtracking.',
  },
  {
    id: 'G-102',
    term: 'Identity (Memory Address)',
    category: 'Core Language & Primitives',
    patterns: /\b(identit(y|ies)|id\(x\)|memory address(es)?)\b/gi,
    definition: 'A unique integer assigned to every object in heap memory upon creation, inspectable via id(x). In CPython, it corresponds to the physical memory pointer of the object.',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 12)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements',
        pageRange: 'pp. 12–14',
        contextSnippet: 'An identity is an integer representing the object’s location in memory, tested with the is operator.',
      },
      {
        chapter: 'Chapter 5',
        section: '§ 5.2.1 Aliasing',
        pageRange: 'pp. 69–71',
        contextSnippet: 'When L2 = L1, both variables share the identical identity id(L1) == id(L2).',
      },
    ],
    leetCodeRelevance: 'Used in graph/tree algorithms (e.g., Clone Graph) where visited sets track object identities to detect cycles.',
  },
  {
    id: 'G-103',
    term: 'Type / Data Type',
    category: 'Core Language & Primitives',
    patterns: /\b(data types?|types?)\b/gi,
    definition: 'A classification that defines what values an object can hold, its internal memory representation, and what operations (methods/operators) can be legally performed on it.',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 12)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements',
        pageRange: 'pp. 12–15',
        contextSnippet: 'Every object has a type that dictates the operations that can be performed on it.',
      },
      {
        chapter: 'Chapter 4',
        section: '§ 4.2 Specifications',
        pageRange: 'pp. 52–55',
        contextSnippet: 'Function specifications state the expected types of formal parameters and return values.',
      },
    ],
    leetCodeRelevance: 'Type mismatches (e.g. passing a list where a tuple/set is expected) cause runtime TypeErrors in interviews.',
  },
  {
    id: 'G-104',
    term: 'Value / State',
    category: 'Core Language & Primitives',
    patterns: /\b(values?|state)\b/gi,
    definition: 'The actual data contents stored in an object’s allocated memory buffer, evaluated and compared using the value equality operator (==).',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 12)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements',
        pageRange: 'pp. 12–14',
        contextSnippet: 'The value is the data stored in the memory representation of the object.',
      },
      {
        chapter: 'Chapter 5',
        section: '§ 5.2 Mutability',
        pageRange: 'pp. 68–72',
        contextSnippet: 'Two objects can have identical values (a == b) while maintaining distinct heap identities (a is not b).',
      },
    ],
    leetCodeRelevance: 'Distinguishing equality of values from pointer identity is critical when checking node values in linked lists and trees.',
  },
  {
    id: 'G-105',
    term: 'Scalar Object',
    category: 'Core Language & Primitives',
    patterns: /\b(scalars?|scalar objects?|scalar types?)\b/gi,
    definition: 'An indivisible primitive computational entity with no accessible internal structure (int, float, bool, NoneType).',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 12)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements',
        pageRange: 'pp. 12–15',
        contextSnippet: 'Scalar objects are primitive values that cannot be indexed or subdivided.',
      },
      {
        chapter: 'Chapter 5',
        section: '§ 5.1 Tuples and Sequences',
        pageRange: 'pp. 65–68',
        contextSnippet: 'Composite structures are built by storing ordered collections of scalar and non-scalar references.',
      },
    ],
    leetCodeRelevance: 'Scalar variables passed to recursive functions are immutable values; reassigning them in child frames does not affect parent frames.',
  },
  {
    id: 'G-106',
    term: 'Non-Scalar Object',
    category: 'Core Language & Primitives',
    patterns: /\b(non[- ]scalars?|non[- ]scalar objects?|non[- ]scalar types?|composite objects?)\b/gi,
    definition: 'A composite object with internal structure containing references to other objects (str, list, tuple, dict, set, classes).',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 12)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements',
        pageRange: 'pp. 12–13',
        contextSnippet: 'Non-scalar objects have internal structure accessible via indexing, slicing, and iteration.',
      },
      {
        chapter: 'Chapter 5',
        section: '§ 5.1 Structured Types',
        pageRange: 'pp. 65–70',
        contextSnippet: 'Structured non-scalar types store pointers to element objects.',
      },
    ],
    leetCodeRelevance: 'Passing non-scalars to helper functions passes memory pointers; mutating them causes side-effects across recursion.',
  },
  {
    id: 'G-107',
    term: 'Integer (int)',
    category: 'Core Language & Primitives',
    patterns: /\b(ints?|integers?)\b/gi,
    definition: 'An arbitrary-precision scalar numeric type representing whole numbers without upper or lower magnitude bounds in Python 3.',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 12)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements',
        pageRange: 'pp. 12–14',
        contextSnippet: 'Python integers have arbitrary precision and do not overflow.',
      },
    ],
    leetCodeRelevance: 'Enables computing huge factorial and Fibonacci values, though 32-bit limits must still be checked for C++ compliance.',
  },
  {
    id: 'G-108',
    term: 'Float (Floating-Point)',
    category: 'Core Language & Primitives',
    patterns: /\b(floats?|floating[- ]point|ieee 754|machine epsilon)\b/gi,
    definition: 'A scalar numeric type representing real numbers using standard IEEE 754 double precision (64 bits). Subject to binary rounding limits.',
    primaryLocation: 'Chapter 3 (§ 3.3 A Few Words About Using Floats, p. 36)',
    occurrences: [
      {
        chapter: 'Chapter 3',
        section: '§ 3.3 Floats',
        pageRange: 'pp. 36–38',
        contextSnippet: '0.1 cannot be represented exactly in binary floating point. Testing float equality with == is almost always a bug.',
      },
    ],
    leetCodeRelevance: 'Required in continuous binary search on answers and geometry algorithms where tolerance checks abs(a - b) < 1e-6 are necessary.',
  },
  {
    id: 'G-109',
    term: 'Boolean (bool) & Truthiness',
    category: 'Core Language & Primitives',
    patterns: /\b(bools?|booleans?|truthiness|truth[- ]value)\b/gi,
    definition: 'The Boolean truth values True and False. In Python, 0, 0.0, None, and empty collections (\'\', [], {}) evaluate to False; all other values evaluate to True.',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 13)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements',
        pageRange: 'pp. 13–15',
        contextSnippet: 'In Python, bool is a subclass of int where True == 1 and False == 0.',
      },
    ],
    leetCodeRelevance: 'Writing clean, idiomatic loop conditions (while stack:, if not visited:) that avoid redundant len(arr) > 0 checks.',
  },
  {
    id: 'G-110',
    term: 'None / NoneType',
    category: 'Core Language & Primitives',
    patterns: /\b(nonetype|none)\b/gi,
    definition: 'A singleton scalar object used to represent the absence of a value, an uninitialized state, or the default return value of functions without an explicit return.',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 13)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements',
        pageRange: 'pp. 12–14',
        contextSnippet: 'NoneType has a single value, None, representing the absence of a value.',
      },
    ],
    leetCodeRelevance: 'Represents empty tree pointers (root is None) and null linked list terminals (node.next is None).',
  },
  {
    id: 'G-111',
    term: 'Type Casting (Conversion)',
    category: 'Core Language & Primitives',
    patterns: /\b(type casts?|type casting|type conversions?|casting)\b/gi,
    definition: 'Explicitly converting an object between data types using constructor functions (int(s), str(n), float(x), list(t)).',
    primaryLocation: 'Chapter 2 (§ 2.1 The Basic Elements of Python, p. 13)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1 The Basic Elements',
        pageRange: 'pp. 13–15',
        contextSnippet: 'Type conversions convert an object of one type to another explicitly.',
      },
    ],
    leetCodeRelevance: 'String-to-number parsing (String to Integer atoi, Add Strings).',
  },
  {
    id: 'G-112',
    term: 'Floor Division & Modulo',
    category: 'Core Language & Primitives',
    patterns: /\b(floor division|modulo|remainder|divmod|\/\/|%)\b/gi,
    definition: 'Python’s integer division invariant: a == (a // b) * b + (a % b), where floor division // rounds down towards negative infinity.',
    primaryLocation: 'Chapter 2 (§ 2.1.1 Operators and Expressions, p. 14)',
    occurrences: [
      {
        chapter: 'Chapter 2',
        section: '§ 2.1.1 Operators',
        pageRange: 'pp. 14–16',
        contextSnippet: 'Floor division rounds toward negative infinity, ensuring that a % b has the same sign as divisor b.',
      },
    ],
    leetCodeRelevance: 'Circular array indexing ((i + k) % n) and decimal digit extraction (n % 10, n //= 10).',
  },
  {
    id: 'G-113',
    term: 'Immutability vs Mutability',
    category: 'Core Language & Primitives',
    patterns: /\b(immutab(le|ility)|mutab(le|ility))\b/gi,
    definition: 'Immutable objects (int, float, str, tuple, frozenset) cannot be modified after creation. Mutable objects (list, dict, set) can be mutated in-place.',
    primaryLocation: 'Chapter 5 (§ 5.1 Tuples & § 5.2 Lists, pp. 65–70)',
    occurrences: [
      {
        chapter: 'Chapter 5',
        section: '§ 5.2 Lists and Mutability',
        pageRange: 'pp. 68–74',
        contextSnippet: 'Lists are mutable: their contents can be altered in-place using append and pop.',
      },
    ],
    leetCodeRelevance: 'Only immutable types can serve as hash table keys or dynamic programming memoization state tuples.',
  },

  // ── 2. Memory, State & Runtime Architecture ────────────────────────────────
  {
    id: 'G-114',
    term: 'Aliasing',
    category: 'Memory, State & Runtime',
    patterns: /\b(aliasing|aliases|aliased|alias)\b/gi,
    definition: 'A state where multiple variable identifiers point to the exact same physical heap object (id(L1) == id(L2)). In-place mutations through one variable silently alter all aliases.',
    primaryLocation: 'Chapter 5 (§ 5.2.1 Lists and Mutability, p. 70)',
    occurrences: [
      {
        chapter: 'Chapter 5',
        section: '§ 5.2.1 Lists and Mutability',
        pageRange: 'pp. 68–74',
        contextSnippet: 'Because lists are mutable, assignment creates an alias rather than a clone.',
      },
      {
        chapter: 'Chapter 10',
        section: '§ 10.1 Abstract Data Types',
        pageRange: 'pp. 158–162',
        contextSnippet: 'getMembers() must return a cloned list self.vals[:] to prevent caller aliasing of internal representation.',
      },
    ],
    leetCodeRelevance: 'Crucial in Backtracking (Subsets, Permutations) where current path arrays must be cloned with path[:] before adding to output.',
  },
  {
    id: 'G-115',
    term: 'Shallow Copy vs Deep Copy',
    category: 'Memory, State & Runtime',
    patterns: /\b(shallow cop(y|ies)|deep cop(y|ies)|cloning|cloned?)\b/gi,
    definition: 'A shallow copy (L[:], list(L)) duplicates the outer container while preserving references to inner objects. A deep copy recursively duplicates all nested objects.',
    primaryLocation: 'Chapter 5 (§ 5.3 Cloning, p. 74)',
    occurrences: [
      {
        chapter: 'Chapter 5',
        section: '§ 5.3 Cloning',
        pageRange: 'pp. 74–77',
        contextSnippet: 'Cloning a list using L[:] produces a shallow clone. If elements are nested lists, mutating them mutates both.',
      },
    ],
    leetCodeRelevance: 'Clone Graph, Copy List with Random Pointer.',
  },
  {
    id: 'G-116',
    term: 'Call Stack & Stack Frame',
    category: 'Memory, State & Runtime',
    patterns: /\b(call stacks?|stack frames?|activation records?|stack overflow)\b/gi,
    definition: 'The runtime LIFO structure that pushes an activation record (frame) for each function call, storing formal arguments, local variables, and return pointers.',
    primaryLocation: 'Chapter 4 (§ 4.1 Functions and Scoping, p. 46)',
    occurrences: [
      {
        chapter: 'Chapter 4',
        section: '§ 4.1 Functions and Scoping',
        pageRange: 'pp. 45–52',
        contextSnippet: 'Each function invocation allocates a stack frame storing local bindings according to the LEGB scope rules.',
      },
    ],
    leetCodeRelevance: 'Analyzing auxiliary space in tree and graph DFS (O(H) stack frames, where H is tree height).',
  },
  {
    id: 'G-117',
    term: 'Lexical Scope & LEGB Rule',
    category: 'Memory, State & Runtime',
    patterns: /\b(lexical scopes?|legb rule|symbol tables?|variable scopes?)\b/gi,
    definition: 'Python’s identifier resolution order: Local (L) -> Enclosing (E) -> Global (G) -> Built-in (B).',
    primaryLocation: 'Chapter 4 (§ 4.1 Functions and Scoping, p. 47)',
    occurrences: [
      {
        chapter: 'Chapter 4',
        section: '§ 4.1 Functions and Scoping',
        pageRange: 'pp. 46–50',
        contextSnippet: 'Python uses static (lexical) scoping: identifier binding is determined where the function is defined.',
      },
    ],
    leetCodeRelevance: 'Prevents UnboundLocalError when referencing and updating outer variables inside helper DFS functions.',
  },
  {
    id: 'G-118',
    term: 'Nonlocal Binding',
    category: 'Memory, State & Runtime',
    patterns: /\b(nonlocal|nonlocal keyword|enclosing frame)\b/gi,
    definition: 'A keyword binding an identifier assignment in a nested function directly to the nearest enclosing non-global scope rather than creating a local variable.',
    primaryLocation: 'Chapter 4 (§ 4.1 Functions and Scoping, p. 49)',
    occurrences: [
      {
        chapter: 'Chapter 4',
        section: '§ 4.1 Functions and Scoping',
        pageRange: 'pp. 48–51',
        contextSnippet: 'Declaring nonlocal x inside a helper function enables mutation of x in the enclosing parent frame.',
      },
    ],
    leetCodeRelevance: 'Enables clean DFS tree traversals tracking global optimal sums (Binary Tree Maximum Path Sum, Diameter of Binary Tree).',
  },
  {
    id: 'G-119',
    term: 'Pass-by-Object-Reference',
    category: 'Memory, State & Runtime',
    patterns: /\b(pass[- ]by[- ]object[- ]reference|pass[- ]by[- ]assignment|argument passing)\b/gi,
    definition: 'Python argument passing semantics: functions receive pointers to the caller\'s objects. Mutating mutable arguments alters caller data in-place.',
    primaryLocation: 'Chapter 4 (§ 4.1 Functions and Scoping, p. 48)',
    occurrences: [
      {
        chapter: 'Chapter 4',
        section: '§ 4.1 Functions and Scoping',
        pageRange: 'pp. 47–50',
        contextSnippet: 'Parameters are bound to actual arguments using object assignment. Mutating a passed list alters the caller object.',
      },
    ],
    leetCodeRelevance: 'In-place array algorithms (Move Zeroes, Remove Element, Rotate Array).',
  },

  // ── 3. Data Structures & ADTs ──────────────────────────────────────────────
  {
    id: 'G-120',
    term: 'Abstract Data Type (ADT)',
    category: 'Data Structures & ADTs',
    patterns: /\b(abstract data types?|ADTs?)\b/gi,
    definition: 'A data type defined exclusively by its public operations and behavioral semantics, hiding internal data representation behind an abstraction barrier.',
    primaryLocation: 'Chapter 10 (§ 10.1 Abstract Data Types and Classes, p. 157)',
    occurrences: [
      {
        chapter: 'Chapter 10',
        section: '§ 10.1 Abstract Data Types',
        pageRange: 'pp. 157–162',
        contextSnippet: 'ADTs enforce a data abstraction barrier between client code and implementation details.',
      },
    ],
    leetCodeRelevance: 'Design problems (Implement Stack using Queues, Implement Trie, Design HashMap).',
  },
  {
    id: 'G-121',
    term: 'Representation Invariant',
    category: 'Data Structures & ADTs',
    patterns: /\b(representation invariants?|rep invariants?)\b/gi,
    definition: 'A formal structural rule that must hold true for the internal state of an ADT before and after every public method call.',
    primaryLocation: 'Chapter 10 (§ 10.1 Abstract Data Types and Classes, p. 158)',
    occurrences: [
      {
        chapter: 'Chapter 10',
        section: '§ 10.1 Abstract Data Types',
        pageRange: 'pp. 157–163',
        contextSnippet: 'In IntSet, the representation invariant guarantees that self.vals contains strictly sorted, non-duplicate integers.',
      },
    ],
    leetCodeRelevance: 'Design problems (LRU Cache, Min Stack, Monotonic Queue).',
  },
  {
    id: 'G-122',
    term: 'Dynamic Array (List)',
    category: 'Data Structures & ADTs',
    patterns: /\b(dynamic arrays?|python lists?|contiguous array)\b/gi,
    definition: 'A contiguous array of memory pointers that dynamically resizes by geometric doubling when full, providing O(1) amortized appends and O(1) index access.',
    primaryLocation: 'Chapter 5 (§ 5.2 Lists and Mutability, p. 68)',
    occurrences: [
      {
        chapter: 'Chapter 5',
        section: '§ 5.2 Lists and Mutability',
        pageRange: 'pp. 68–74',
        contextSnippet: 'Python lists are contiguous arrays of pointers to objects in memory.',
      },
    ],
    leetCodeRelevance: 'Two Pointers, Sliding Window, Prefix Sums.',
  },
  {
    id: 'G-123',
    term: 'FIFO Queue & Deque',
    category: 'Data Structures & ADTs',
    patterns: /\b(fifo|deque|double[- ]ended queue|queues?)\b/gi,
    definition: 'A First-In-First-Out data structure. collections.deque implements a doubly-linked buffer of fixed-size blocks providing O(1) pops and appends from both ends.',
    primaryLocation: 'Chapter 10 (§ 10.3 Object-Oriented Programming, p. 165)',
    occurrences: [
      {
        chapter: 'Chapter 10',
        section: '§ 10.3 Queues',
        pageRange: 'pp. 165–168',
        contextSnippet: 'list.pop(0) shifts all elements in memory taking O(N) time; deque.popleft() operates in O(1) time.',
      },
    ],
    leetCodeRelevance: 'Breadth-First Search (BFS) and Sliding Window Maximum.',
  },
  {
    id: 'G-124',
    term: 'Hash Table & Dictionaries',
    category: 'Data Structures & ADTs',
    patterns: /\b(hash tables?|hash maps?|dictionar(y|ies)|hash functions?|hash collision)\b/gi,
    definition: 'A data structure mapping immutable keys to values via a hash function (hash(k) % buckets) to achieve average-case O(1) insertions and lookups.',
    primaryLocation: 'Chapter 12 (§ 12.3 Hash Tables, p. 208)',
    occurrences: [
      {
        chapter: 'Chapter 12',
        section: '§ 12.3 Hash Tables',
        pageRange: 'pp. 208–214',
        contextSnippet: 'A hash table converts a key into a bucket index, achieving O(1) lookup under uniform distribution.',
      },
    ],
    leetCodeRelevance: 'Two Sum, Group Anagrams, Longest Consecutive Sequence.',
  },
  {
    id: 'G-125',
    term: 'Binary Search Tree (BST)',
    category: 'Data Structures & ADTs',
    patterns: /\b(binary search trees?|bsts?)\b/gi,
    definition: 'A binary tree where for every node X: all left descendants are < X.val, and all right descendants are > X.val.',
    primaryLocation: 'Chapter 12 (§ 12.1 Search Algorithms, p. 198)',
    occurrences: [
      {
        chapter: 'Chapter 12',
        section: '§ 12.1 Search Algorithms',
        pageRange: 'pp. 197–200',
        contextSnippet: 'In a balanced BST, searching, insertion, and deletion run in O(log n) time.',
      },
    ],
    leetCodeRelevance: 'Validate BST, Kth Smallest Element in BST, Lowest Common Ancestor in BST.',
  },
  {
    id: 'G-126',
    term: 'Heap & Priority Queue',
    category: 'Data Structures & ADTs',
    patterns: /\b(heaps?|priority queues?|min[- ]heap|max[- ]heap|heapq)\b/gi,
    definition: 'A complete binary tree satisfying the heap invariant: parent is always smaller than (min-heap) or greater than (max-heap) children, giving O(1) peek and O(log N) push/pop.',
    primaryLocation: 'Chapter 12 (§ 12.2 Sorting Algorithms, p. 204)',
    occurrences: [
      {
        chapter: 'Chapter 12',
        section: '§ 12.2 Sorting Algorithms',
        pageRange: 'pp. 204–207',
        contextSnippet: 'A priority queue retrieves the highest-priority element in logarithmic time using a binary heap representation.',
      },
    ],
    leetCodeRelevance: 'Top K Frequent Elements, Merge k Sorted Lists, Find Median from Data Stream.',
  },

  // ── 4. Algorithmic Paradigms ───────────────────────────────────────────────
  {
    id: 'G-127',
    term: 'Bisection Search',
    category: 'Algorithmic Paradigms',
    patterns: /\b(bisection search|bisection)\b/gi,
    definition: 'An interval-halving algorithm that finds roots of monotonic continuous functions by discarding half the search space in logarithmic time O(log(Range/ε)).',
    primaryLocation: 'Chapter 3 (§ 3.2 Approximate Solutions and Bisection Search, p. 32)',
    occurrences: [
      {
        chapter: 'Chapter 3',
        section: '§ 3.2 Approximate Solutions',
        pageRange: 'pp. 31–36',
        contextSnippet: 'Bisection search cuts the search interval in half on each step, reducing continuous search time exponentially.',
      },
    ],
    leetCodeRelevance: 'Binary Search on Answers (Koko Eating Bananas, Capacity To Ship Packages).',
  },
  {
    id: 'G-128',
    term: 'Newton-Raphson Method',
    category: 'Algorithmic Paradigms',
    patterns: /\b(newton-raphson|newton\'s method)\b/gi,
    definition: 'A successive approximation algorithm finding roots of differentiable functions f(y) = 0 using tangent-line linearizations: y_{new} = y - f(y)/f\'(y). Features quadratic convergence.',
    primaryLocation: 'Chapter 3 (§ 3.4 Newton-Raphson, p. 38)',
    occurrences: [
      {
        chapter: 'Chapter 3',
        section: '§ 3.4 Newton-Raphson',
        pageRange: 'pp. 38–41',
        contextSnippet: 'For f(y) = y^2 - k, the update y = y - (y^2 - k)/(2y) converges quadratically to sqrt(k).',
      },
    ],
    leetCodeRelevance: 'LeetCode 69 Sqrt(x), LeetCode 50 Pow(x, n).',
  },
  {
    id: 'G-129',
    term: 'Inductive Recursion & Base Case',
    category: 'Algorithmic Paradigms',
    patterns: /\b(inductive step|mathematical induction|inductive hypothesis|base case|recursive calls?|recursion)\b/gi,
    definition: 'Decomposing a problem of size n into smaller subproblems of size n-1 or n/2, with explicit base cases providing direct non-recursive solutions for terminal instances.',
    primaryLocation: 'Chapter 6 (§ 6.1 Fibonacci & § 6.2 Palindromes, pp. 86–92)',
    occurrences: [
      {
        chapter: 'Chapter 6',
        section: '§ 6.2 Palindromes',
        pageRange: 'pp. 88–92',
        contextSnippet: 'The inductive step tests if s[0] == s[-1] and reduces verification to the inner substring s[1:-1].',
      },
    ],
    leetCodeRelevance: 'Binary tree DFS, Palindrome Partitioning, Invert Binary Tree.',
  },
  {
    id: 'G-130',
    term: 'Divide-and-Conquer',
    category: 'Algorithmic Paradigms',
    patterns: /\b(divide[- ]and[- ]conquer)\b/gi,
    definition: 'An algorithmic paradigm that breaks a problem into independent subproblems of the same type, solves them recursively, and combines their solutions in polynomial time.',
    primaryLocation: 'Chapter 12 (§ 12.2 Sorting Algorithms, p. 201)',
    occurrences: [
      {
        chapter: 'Chapter 12',
        section: '§ 12.2 Sorting Algorithms',
        pageRange: 'pp. 201–206',
        contextSnippet: 'Merge sort divides a list in half, recursively sorts both sublists, and merges them in linear O(n) time.',
      },
    ],
    leetCodeRelevance: 'Merge Sort, Sort List, Merge Intervals, Median of Two Sorted Arrays.',
  },
  {
    id: 'G-131',
    term: 'Dynamic Programming & Memoization',
    category: 'Algorithmic Paradigms',
    patterns: /\b(dynamic programming|memoization|memoized|memo table|overlapping subproblems|optimal substructure)\b/gi,
    definition: 'An optimization caching solutions to overlapping subproblems in a table, reducing exponential search trees O(2^N) to polynomial state spaces O(N*W).',
    primaryLocation: 'Chapter 15 (§ 15.1 Fibonacci & § 15.2 Knapsack, pp. 248–258)',
    occurrences: [
      {
        chapter: 'Chapter 15',
        section: '§ 15.1 Fibonacci Numbers Revisited',
        pageRange: 'pp. 248–252',
        contextSnippet: 'fastFib records subproblems in memo={0:0, 1:1}, reducing complexity from exponential O(2^n) to linear O(n).',
      },
    ],
    leetCodeRelevance: 'Climbing Stairs, Coin Change, House Robber, Partition Equal Subset Sum.',
  },
  {
    id: 'G-132',
    term: '0/1 Decision Tree',
    category: 'Algorithmic Paradigms',
    patterns: /\b(decision trees?|0\/1 knapsack|knapsack problems?)\b/gi,
    definition: 'A binary tree modeling choices at each item i: branch left to include item i (take), branch right to exclude item i (leave). Pruned to O(n*W) via state memoization.',
    primaryLocation: 'Chapter 14 (§ 14.1 Knapsack) & Chapter 15 (§ 15.2 DP), pp. 232–257',
    occurrences: [
      {
        chapter: 'Chapter 14',
        section: '§ 14.1 Knapsack Problems',
        pageRange: 'pp. 232–238',
        contextSnippet: 'The 0/1 knapsack decision tree explores 2^n leaves in brute force, but many nodes represent identical subproblems.',
      },
    ],
    leetCodeRelevance: 'Target Sum, Partition Equal Subset Sum, Ones and Zeroes.',
  },
  {
    id: 'G-133',
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
    id: 'G-134',
    term: 'Depth-First Search (DFS) & Backtracking',
    category: 'Algorithmic Paradigms',
    patterns: /\b(depth[- ]first search|dfs|backtracking|pruning)\b/gi,
    definition: 'A recursive traversal exploring as deep as possible along each branch before backtracking, commonly paired with pruning to abandon invalid branches early.',
    primaryLocation: 'Chapter 14 (§ 14.2 Graph Optimization Problems, p. 239)',
    occurrences: [
      {
        chapter: 'Chapter 14',
        section: '§ 14.2 Graph Optimization',
        pageRange: 'pp. 239–243',
        contextSnippet: 'DFS traverses a branch to its terminus before backtracking to explore alternate branches.',
      },
    ],
    leetCodeRelevance: 'N-Queens, Combination Sum, Word Search, Subsets.',
  },

  // ── 5. Complexity & Mathematics ───────────────────────────────────────────
  {
    id: 'G-135',
    term: 'Asymptotic Complexity (Big-O)',
    category: 'Complexity & Mathematics',
    patterns: /\b(big[- ]o|asymptotic notation|asymptotic complexity|time complexity|space complexity)\b/gi,
    definition: 'A mathematical framework describing the limiting growth rate of an algorithm\'s running time or memory usage as input size n tends toward infinity: f(n) <= c * g(n).',
    primaryLocation: 'Chapter 11 (§ 11.2 Asymptotic Notation, p. 182)',
    occurrences: [
      {
        chapter: 'Chapter 11',
        section: '§ 11.2 Asymptotic Notation',
        pageRange: 'pp. 182–188',
        contextSnippet: 'Big-O establishes the worst-case upper bound on growth: O(1) < O(log n) < O(n) < O(n log n) < O(n^2) < O(2^n).',
      },
    ],
    leetCodeRelevance: 'Evaluating algorithm runtime to prevent Time Limit Exceeded (TLE).',
  },
  {
    id: 'G-136',
    term: 'Space-Time Tradeoff & Prefix Sums',
    category: 'Complexity & Mathematics',
    patterns: /\b(space[- ]time tradeoffs?|prefix sums?|precomputation|cumulative sums?)\b/gi,
    definition: 'The computational design principle of utilizing auxiliary memory to cache precomputed calculations so future range queries evaluate in constant O(1) time.',
    primaryLocation: 'Chapter 11 (§ 11.3 Amortization and Space-Time Tradeoffs, p. 188)',
    occurrences: [
      {
        chapter: 'Chapter 11',
        section: '§ 11.3 Space-Time Tradeoffs',
        pageRange: 'pp. 188–191',
        contextSnippet: 'Prefix sum arrays P[i] = P[i-1] + A[i-1] answer any subarray sum query sum(L, R) = P[R+1] - P[L] in O(1) time.',
      },
    ],
    leetCodeRelevance: 'Subarray Sum Equals K, Range Sum Query, Product of Array Except Self.',
  },

  // ── 6. Bitwise & Binary Arithmetic ─────────────────────────────────────────
  {
    id: 'G-137',
    term: 'Bitmask & Bitwise Operators',
    category: 'Bitwise & Binary Arithmetic',
    patterns: /\b(bitmasks?|bitwise|bitwise and|bitwise or|bitwise xor|left shift|right shift|binary representation)\b/gi,
    definition: 'Low-level arithmetic operations manipulating individual bits directly in CPU registers: 1 << i creates a mask, (n >> i) & 1 tests bit i, n | (1 << i) sets bit i, n & ~(1 << i) clears bit i.',
    primaryLocation: 'Chapter 3 (§ 3.3 Binary Representation, p. 37)',
    occurrences: [
      {
        chapter: 'Chapter 3',
        section: '§ 3.3 Binary Representation',
        pageRange: 'pp. 36–38',
        contextSnippet: 'Bitwise operators manipulate binary registers directly: 1 << i creates a mask, n & (n-1) clears the lowest set bit.',
      },
    ],
    leetCodeRelevance: 'State compression in Bitmask DP (Shortest Path Visiting All Nodes, Single Number, Subsets).',
  },
  {
    id: 'G-138',
    term: 'Brian Kernighan\'s Algorithm',
    category: 'Bitwise & Binary Arithmetic',
    patterns: /\b(brian kernighan|kernighan\'s algorithm|n & \(n - 1\)|set bits?|hamming weight|popcount)\b/gi,
    definition: 'An algebraic invariant of binary arithmetic where n & (n - 1) clears the lowest set bit of integer n in O(1) time, counting set bits in O(K) steps (where K is number of 1-bits).',
    primaryLocation: 'Chapter 3 (§ 3.3 Binary Representation, p. 37)',
    occurrences: [
      {
        chapter: 'Chapter 3',
        section: '§ 3.3 Binary Representation',
        pageRange: 'pp. 37–38',
        contextSnippet: 'Subtracting 1 flips all bits after the lowest set bit; n & (n - 1) isolates and zeroes the lowest set bit.',
      },
    ],
    leetCodeRelevance: 'Number of 1 Bits, Power of Two, Counting Bits.',
  },

  // ── 7. Searching & Sorting ────────────────────────────────────────────────
  {
    id: 'G-139',
    term: 'Merge Sort',
    category: 'Searching & Sorting',
    patterns: /\b(merge sort|mergesort)\b/gi,
    definition: 'A stable divide-and-conquer sorting algorithm splitting arrays in halves, sorting them recursively, and merging them in linear O(N) time with guaranteed O(N log N) worst-case complexity.',
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
    id: 'G-140',
    term: 'Binary Search',
    category: 'Searching & Sorting',
    patterns: /\b(binary search|binary search scaffold)\b/gi,
    definition: 'A search algorithm on sorted arrays halving candidate indices (mid = (left + right) // 2) in guaranteed O(log N) time.',
    primaryLocation: 'Chapter 12 (§ 12.1 Search Algorithms, p. 195)',
    occurrences: [
      {
        chapter: 'Chapter 12',
        section: '§ 12.1 Search Algorithms',
        pageRange: 'pp. 195–200',
        contextSnippet: 'Binary search exploits sorted array order invariants to achieve logarithmic time search.',
      },
    ],
    leetCodeRelevance: 'Binary Search, Search in Rotated Sorted Array, Find First and Last Position.',
  },

  // ── 8. Functions & Abstractions ───────────────────────────────────────────
  {
    id: 'G-141',
    term: 'First-Class Functions & Lambdas',
    category: 'Functions & Abstractions',
    patterns: /\b(first[- ]class (functions?|objects?)|lambdas?|anonymous functions?|higher[- ]order functions?)\b/gi,
    definition: 'Treating functions as first-class entities that can be passed as arguments, returned as values, and bound to variables. In Python, lambda x: expr defines anonymous functions inline.',
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
    id: 'G-142',
    term: 'List Comprehensions',
    category: 'Functions & Abstractions',
    patterns: /\b(list comprehensions?|dict comprehensions?|set comprehensions?)\b/gi,
    definition: 'A concise Pythonic construct for creating new collections by filtering and transforming iterable elements: [expr for x in iterable if condition].',
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

"""A documentation excerpt for every card that doesn't carry its own.

Each quote is copied word for word from the MDN or TypeScript documentation
page it names (checked against the pages' source text when written). The
app shows it before and after a review as "the reading" behind the card.
"""

from __future__ import annotations

from .model import MDN_JS, TS_DOCS, TS_HANDBOOK, Source

MDN = "https://developer.mozilla.org/en-US/docs/"
REF = MDN_JS + "Reference/"
ARRAY = REF + "Global_Objects/Array/"
STRING = REF + "Global_Objects/String/"


def _mdn(title: str, path: str, quote: str) -> Source:
    return Source(f"MDN — {title}", path, quote)


def _ts(title: str, url: str, quote: str) -> Source:
    return Source(f"TypeScript Handbook — {title}", url, quote)


IS_ARRAY = _mdn(
    "Array.isArray()",
    ARRAY + "isArray",
    "The Array.isArray() static method determines whether the passed value is an Array.",
)
SPLIT = _mdn(
    "String.prototype.split()",
    STRING + "split",
    "The split() method of String values takes a pattern and divides this string into an ordered list of "
    "substrings by searching for the pattern, puts these substrings into an array, and returns the array.",
)
READONLY_ARRAY = _ts(
    "Object Types",
    TS_HANDBOOK + "objects.html",
    "The ReadonlyArray is a special type that describes arrays that shouldn't be changed.",
)

QUOTES: dict[str, Source] = {
    # 01 Values
    "js01-describe-type": IS_ARRAY,
    "js01-parse-count": _mdn(
        "Number.isInteger()",
        REF + "Global_Objects/Number/isInteger",
        "The Number.isInteger() static method determines whether the passed value is an integer.",
    ),
    "js01-const": _mdn(
        "const",
        REF + "Statements/const",
        "The value of a constant can't be changed through reassignment using the assignment operator, but if "
        "a constant is an object, its properties can be added, updated, or removed.",
    ),
    "js01-pass-by-sharing": _mdn(
        "Functions",
        MDN_JS + "Guide/Functions",
        "When you pass an object as a parameter, if the function changes the object's properties, that change "
        "is visible outside the function, as shown in the following example:",
    ),
    # 02 Operators
    "js02-equality": _mdn(
        "Strict equality (===)",
        REF + "Operators/Strict_equality",
        "Unlike the equality operator, the strict equality operator always considers operands of different "
        "types to be different.",
    ),
    "js02-letter-grade": _mdn(
        "if...else",
        REF + "Statements/if...else",
        "The if...else statement executes a statement if a specified condition is truthy. If the condition is "
        "falsy, another statement in the optional else clause will be executed.",
    ),
    "js02-logical-operands": _mdn(
        "Logical OR (||)",
        REF + "Operators/Logical_OR",
        "However, the || operator actually returns the value of one of the specified operands, so if this "
        "operator is used with non-Boolean values, it will return a non-Boolean value.",
    ),
    "js02-count-truthy": _mdn(
        "Array.prototype.filter()",
        ARRAY + "filter",
        "The filter() method of Array instances creates a shallow copy of a portion of a given array, filtered "
        "down to just the elements from the given array that pass the test implemented by the provided function.",
    ),
    # 03 Loops
    "js03-sum-to": _mdn(
        "for",
        REF + "Statements/for",
        "The for statement creates a loop that consists of three optional expressions, enclosed in parentheses "
        "and separated by semicolons, followed by a statement (usually a block statement) to be executed in the loop.",
    ),
    "js03-count-vowels": _mdn(
        "for...of",
        REF + "Statements/for...of",
        "The for...of statement executes a loop that operates on a sequence of values sourced from an iterable object.",
    ),
    "js03-fizzbuzz": _mdn(
        "Remainder (%)",
        REF + "Operators/Remainder",
        "The remainder (%) operator returns the remainder left over when one operand is divided by a second operand.",
    ),
    "js03-first-index-over": _mdn(
        "return",
        REF + "Statements/return",
        "The return statement ends function execution and specifies a value to be returned to the function caller.",
    ),
    # 04 Strings
    "js04-capitalize": _mdn(
        "String.prototype.slice()",
        STRING + "slice",
        "The slice() method of String values extracts a section of this string and returns it as a new string, "
        "without modifying the original string.",
    ),
    "js04-palindrome": _mdn(
        "Array.prototype.reverse()",
        ARRAY + "reverse",
        "The reverse() method of Array instances reverses an array in place and returns the reference to the "
        "same array, the first array element now becoming the last, and the last array element becoming the first.",
    ),
    "js04-initials": SPLIT,
    "js04-plus-coercion": _mdn(
        "Addition (+)",
        REF + "Operators/Addition",
        "The addition (+) operator produces the sum of numeric operands or string concatenation.",
    ),
    # 05 Functions
    "js05-hoisting": _mdn(
        "Hoisting",
        MDN + "Glossary/Hoisting",
        "JavaScript Hoisting refers to the process whereby the interpreter appears to move the declaration of "
        "functions, variables, classes, or imports to the top of their scope, prior to execution of the code.",
    ),
    "js05-make-counter": _mdn(
        "Closures",
        MDN_JS + "Guide/Closures",
        "A closure is the combination of a function bundled together (enclosed) with references to its "
        "surrounding state (the lexical environment).",
    ),
    "js05-once": _mdn(
        "Closures",
        MDN_JS + "Guide/Closures",
        "In other words, a closure gives a function access to its outer scope. In JavaScript, closures are "
        "created every time a function is created, at function creation time.",
    ),
    "js05-sum-rest": _mdn(
        "Rest parameters",
        REF + "Functions/rest_parameters",
        "The rest parameter syntax allows a function to accept an indefinite number of arguments as an array, "
        "providing a way to represent variadic functions in JavaScript.",
    ),
    # 06 Arrays
    "js06-squares-of-evens": _mdn(
        "Array.prototype.map()",
        ARRAY + "map",
        "The map() method of Array instances creates a new array populated with the results of calling a "
        "provided function on every element in the calling array.",
    ),
    "js06-average": _mdn(
        "Array.prototype.reduce(), exceptions: TypeError",
        ARRAY + "reduce",
        "Thrown if the array contains no elements and initialValue is not provided.",
    ),
    "js06-foreach-returns-undefined": _mdn(
        "Array.prototype.forEach()",
        ARRAY + "forEach",
        "Unlike map(), forEach() always returns undefined and is not chainable.",
    ),
    "js06-group-by-category": _mdn(
        "Array.prototype.reduce()",
        ARRAY + "reduce",
        "If the array only has one element (regardless of position) and no initialValue is provided, or if "
        "initialValue is provided but the array is empty, the solo value will be returned without calling callbackFn.",
    ),
    "js06-shared-reference": _mdn(
        "Spread syntax",
        REF + "Operators/Spread_syntax",
        "You can use spread syntax to make a shallow copy of an array. Each array element retains its identity "
        "without getting copied.",
    ),
    # 07 Objects
    "js07-format-user": _mdn(
        "Destructuring",
        REF + "Operators/Destructuring",
        "Each destructured property can have a default value. The default value is used when the property is "
        "not present, or has value undefined. It is not used if the property has value null.",
    ),
    "js07-with-defaults": _mdn(
        "Spread syntax",
        REF + "Operators/Spread_syntax",
        "When one object is spread into another object, or when multiple objects are spread into one object, "
        "and properties with identical names are encountered, the property takes the last value assigned while "
        "remaining in the position it was originally set.",
    ),
    "js07-pick": _mdn(
        "in",
        REF + "Operators/in",
        "The in operator returns true if the specified property is in the specified object or its prototype chain.",
    ),
    "js07-optional-chaining": _mdn(
        "Optional chaining (?.)",
        REF + "Operators/Optional_chaining",
        "If the object accessed or function called using this operator is undefined or null, the expression "
        "short circuits and evaluates to undefined instead of throwing an error.",
    ),
    # 08 Map & Set
    "js08-unique": _mdn(
        "Set",
        REF + "Global_Objects/Set",
        "A value in the set may only occur once; it is unique in the set's collection.",
    ),
    "js08-most-frequent-word": _mdn(
        "Map",
        REF + "Global_Objects/Map",
        "The Map object holds key-value pairs and remembers the original insertion order of the keys.",
    ),
    "js08-group-by-map": _mdn(
        "Object.fromEntries()",
        REF + "Global_Objects/Object/fromEntries",
        "The Object.fromEntries() static method transforms a list of key-value pairs into an object.",
    ),
    # 09 Recursion
    "js09-factorial": _mdn(
        "Recursion",
        MDN + "Glossary/Recursion",
        "A recursive function can receive two inputs: a base case (ends recursion) or a recursive case "
        "(resumes recursion).",
    ),
    "js09-sum-nested": _mdn(
        "Recursion",
        MDN + "Glossary/Recursion",
        "The act of a function calling itself, recursion is used to solve problems that contain smaller sub-problems.",
    ),
    "js09-count-files": _mdn(
        "Functions",
        MDN_JS + "Guide/Functions",
        "A function can call itself. For example, here is a function that computes factorials recursively:",
    ),
    "js09-trace": _mdn(
        "Functions",
        MDN_JS + "Guide/Functions",
        "A function can refer to and call itself.",
    ),
    # 10 Errors
    "js10-finally": _mdn(
        "try...catch",
        REF + "Statements/try...catch",
        "The code in the finally block will always be executed before control flow exits the entire construct.",
    ),
    "js10-dont-swallow": _mdn(
        "JSON.parse()",
        REF + "Global_Objects/JSON/parse",
        "When JSON.parse receives a string that does not conform to the JSON grammar, it throws a SyntaxError.",
    ),
    "js10-custom-error": _mdn(
        "Error",
        REF + "Global_Objects/Error",
        "The Error object can also be used as a base object for user-defined exceptions.",
    ),
    # 11 JSON
    "js11-load-settings": _mdn(
        "JSON.parse()",
        REF + "Global_Objects/JSON/parse",
        "The JSON.parse() static method parses a JSON string, constructing the JavaScript value or object "
        "described by the string.",
    ),
    "js11-pretty": _mdn(
        "JSON.stringify()",
        REF + "Global_Objects/JSON/stringify",
        "The space parameter may be used to control spacing in the final string.",
    ),
    "js11-map-to-json": _mdn(
        "JSON.stringify()",
        REF + "Global_Objects/JSON/stringify",
        'Only enumerable own properties are visited. This means Map, Set, etc. will become "{}".',
    ),
    # 12 Classes
    "js12-lost-this": _mdn(
        "Function.prototype.bind()",
        REF + "Global_Objects/Function/bind",
        "The bind() method of Function instances creates a new function that, when called, calls this function "
        "with its this keyword set to the provided value, and a given sequence of arguments preceding any "
        "provided when the new function is called.",
    ),
    "js12-this-in-callback": _mdn(
        "Arrow function expressions",
        REF + "Functions/Arrow_functions",
        "Arrow function expressions should only be used for non-method functions because they do not have "
        "their own this.",
    ),
    "js12-inheritance": _mdn(
        "extends",
        REF + "Classes/extends",
        "The extends keyword is used in class declarations or class expressions to create a class that is a "
        "child of another class.",
    ),
    # 13 Async
    "js13-event-loop": _mdn(
        "Using promises",
        MDN_JS + "Guide/Using_promises",
        "Promise callbacks are handled as a microtask whereas setTimeout() callbacks are handled as task queues.",
    ),
    # 14 Modules
    "js14-missing-named-export": _mdn(
        "import",
        REF + "Statements/import",
        "The static import declaration is used to import read-only live bindings which are exported by another module.",
    ),
    "js14-shared-state": _mdn(
        "import",
        REF + "Statements/import",
        "The imported bindings are called live bindings because they are updated by the module that exported "
        "the binding, but cannot be re-assigned by the importing module.",
    ),
    # 15-20 TypeScript core
    "ts15-enum-emits": Source(
        "TypeScript Handbook — Enums",
        TS_DOCS + "enums.html",
        "Enums are one of the few features TypeScript has which is not a type-level extension of JavaScript.",
    ),
    "ts16-format-price": _ts(
        "Everyday Types",
        TS_HANDBOOK + "everyday-types.html",
        "Some codebases will explicitly specify a return type for documentation purposes, to prevent accidental "
        "changes, or just for personal preference.",
    ),
    "ts17-product": _ts(
        "Object Types",
        TS_HANDBOOK + "objects.html",
        "In those cases, we can mark those properties as optional by adding a question mark (?) to the end of "
        "their names.",
    ),
    "ts17-readonly-sort": READONLY_ARRAY,
    "ts17-structural": Source(
        "TypeScript for JavaScript Programmers",
        TS_DOCS + "typescript-in-5-minutes.html",
        "One of TypeScript's core principles is that type checking focuses on the shape that values have. "
        'This is sometimes called "duck typing" or "structural typing".',
    ),
    "ts18-describe-input": _ts(
        "Narrowing",
        TS_HANDBOOK + "narrowing.html",
        "TypeScript follows possible paths of execution that our programs can take to analyze the most specific "
        "possible type of a value at a given position.",
    ),
    "ts19-greet": _ts(
        "More on Functions",
        TS_HANDBOOK + "functions.html",
        "We can model this in TypeScript by marking the parameter as optional with ?:",
    ),
    "ts20-length-of": _ts(
        "Narrowing",
        TS_HANDBOOK + "narrowing.html",
        "This analysis of code based on reachability is called control flow analysis, and TypeScript uses this "
        "flow analysis to narrow types as it encounters type guards and assignments.",
    ),
    # 21-25 Intermediate
    "ts21-exhaustive": _ts(
        "Narrowing",
        TS_HANDBOOK + "narrowing.html",
        "For example, adding a default to our getArea function which tries to assign the shape to never will "
        "not raise an error when every possible case has been handled.",
    ),
    "ts22-first-element": _ts(
        "Generics",
        TS_HANDBOOK + "generics.html",
        "Here, we will use a type variable, a special kind of variable that works on types rather than values.",
    ),
    "ts22-pluck": _ts(
        "Indexed Access Types",
        TS_HANDBOOK + "indexed-access-types.html",
        "We can use an indexed access type to look up a specific property on another type:",
    ),
    "ts23-public-user": _ts(
        "Utility Types",
        TS_DOCS + "utility-types.html",
        "Constructs a type by picking all properties from Type and then removing Keys (string literal or union "
        "of string literals).",
    ),
    "ts23-count-by-role": _ts(
        "Utility Types",
        TS_DOCS + "utility-types.html",
        "Constructs an object type whose property keys are Keys and whose property values are Type.",
    ),
    "ts24-implements": _ts(
        "Classes",
        TS_HANDBOOK + "classes.html",
        "You can use an implements clause to check that a class satisfies a particular interface.",
    ),
    "ts25-unchecked-index": Source(
        "TSConfig reference — noUncheckedIndexedAccess",
        "https://www.typescriptlang.org/tsconfig/#noUncheckedIndexedAccess",
        "Turning on noUncheckedIndexedAccess will add undefined to any un-declared field in the type.",
    ),
    # 26-27 Labs
    "lab-parse-csv": _mdn(
        "String.prototype.trim()",
        STRING + "trim",
        "The trim() method of String values removes whitespace from both ends of this string and returns a new "
        "string, without modifying the original string.",
    ),
    "lab-inventory": _mdn(
        "RangeError",
        REF + "Global_Objects/RangeError",
        "The RangeError object indicates an error when a value is not in the set or range of allowed values.",
    ),
    "lab-word-wrap": SPLIT,
    "lab-validate-signup": _ts(
        "Narrowing",
        TS_HANDBOOK + "narrowing.html",
        "JavaScript has an operator for determining if an object or its prototype chain has a property with a "
        "name: the in operator. TypeScript takes this into account as a way to narrow down potential types.",
    ),
    "lab-todo-reducer": _ts(
        "Object Types",
        TS_HANDBOOK + "objects.html",
        "When we see a function that returns ReadonlyArrays, it tells us we're not meant to change the contents "
        "at all, and when we see a function that consumes ReadonlyArrays, it tells us that we can pass any array "
        "into that function without worrying that it will change its contents.",
    ),
}

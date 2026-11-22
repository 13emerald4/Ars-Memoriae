"""Concise Socratic lessons and key points for all 105 course cards.

Used in Learn & Practice priming to teach mental models before testing.
"""

LESSONS: dict[str, dict] = {
    "js01-typeof": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\ntypeof null is \"object\" (a bug kept for compatibility), so test for null with === null. Arrays are objects, so use Array.isArray to spot them. 10n is a BigInt.",
        "key_points": [
            "typeof null is \"object\" (a bug kept for compatibility), so test for null with === null.",
            "Arrays are objects, so use Array.isArray to spot them.",
            "10n is a BigInt.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js01-describe-type": {
        "body": "When implementing `describeType(value)` in JavaScript, what core invariants must you satisfy?\n\nWrite `describeType(value)`: return `\"null\"` for `null`, `\"array\"` for arrays, and what `typeof` says for everything else.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`=== null` is the only reliable null check, and `Array.isArray` the only reliable array check. `!value` would also catch 0, \"\" and undefined; `== null` would also catch undefined.",
        "key_points": [
            "`=== null` is the only reliable null check, and `Array.isArray` the only reliable array check.",
            "`!value` would also catch 0, \"\" and undefined; `== null` would also catch undefined.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js01-parse-count": {
        "body": "When implementing `parseCount(text)` in JavaScript, what core invariants must you satisfy?\n\nWrite `parseCount(text)`: return the whole number written in `text`, or `null` if it isn't one. `\"007\"` is 7, `\"-4\"` is -4; `\"\"`, `\"   \"`, `\"3.5\"` and `\"12abc\"` are all `null`.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`parseInt(\"12abc\")` stops at the first bad character and returns 12; `Number(\"12abc\")` is NaN. But `Number(\"\")` and `Number(\"   \")` are 0, so empty input needs its own check.",
        "key_points": [
            "`parseInt(\"12abc\")` stops at the first bad character and returns 12; `Number(\"12abc\")` is NaN.",
            "But `Number(\"\")` and `Number(\"   \")` are 0, so empty input needs its own check.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js01-const": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nconst stops the variable from being reassigned (a TypeError at run time), but the object it points to can still change.",
        "key_points": [
            "const stops the variable from being reassigned (a TypeError at run time), but the object it points to can still change.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js01-pass-by-sharing": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nJavaScript passes every argument by value. For an object that value is a reference, so changing a property through it is seen by the caller, but pointing the parameter at a new object is not.",
        "key_points": [
            "JavaScript passes every argument by value.",
            "For an object that value is a reference, so changing a property through it is seen by the caller, but pointing the parameter at a new object is not.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js01-tdz": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nA var exists (as undefined) from the top of its function. A let or const exists too, but reading it before its declaration line throws: it is in the temporal dead zone.",
        "key_points": [
            "A var exists (as undefined) from the top of its function.",
            "A let or const exists too, but reading it before its declaration line throws: it is in the temporal dead zone.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js02-equality": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\n== converts \"\" to 0 before comparing; === does not convert. null == undefined is true, but null is not == 0. NaN is not equal to anything, itself included: use Number.isNaN.",
        "key_points": [
            "== converts \"\" to 0 before comparing; === does not convert.",
            "null == undefined is true, but null is not == 0.",
            "NaN is not equal to anything, itself included: use Number.isNaN.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js02-port-default": {
        "body": "When implementing `Fix getPort(config)` in JavaScript, what core invariants must you satisfy?\n\n`getPort(config)` should return `config.port`, or `3000` when the port is missing (`undefined` or `null`). Port `0` is valid and must be kept. Fix the bug.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`||` replaces every falsy value, 0 included; `??` replaces only null and undefined.",
        "key_points": [
            "`||` replaces every falsy value, 0 included; `??` replaces only null and undefined.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js02-letter-grade": {
        "body": "When implementing `letterGrade(score)` in JavaScript, what core invariants must you satisfy?\n\nWrite `letterGrade(score)`: `\"A\"` for 90 and up, `\"B\"` for 80\u201389, `\"C\"` for 70\u201379, `\"F\"` below 70.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nCheck the highest band first and return early: each later `if` then only sees scores below the previous threshold. Test every boundary (90, 89, 80, \u2026).",
        "key_points": [
            "Check the highest band first and return early: each later `if` then only sees scores below the previous threshold.",
            "Test every boundary (90, 89, 80, \u2026).",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js02-logical-operands": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\na || b returns a if it is truthy, else b. a && b returns a if it is falsy, else b. a ?? b returns b only when a is null or undefined, so 0 ?? \"zero\" is 0.",
        "key_points": [
            "a || b returns a if it is truthy, else b.",
            "a && b returns a if it is falsy, else b.",
            "b returns b only when a is null or undefined, so 0 ??",
            "\"zero\" is 0."
        ]
    },
    "js02-count-truthy": {
        "body": "When implementing `countTruthy(values)` in JavaScript, what core invariants must you satisfy?\n\nWrite `countTruthy(values)`: how many items in the array are truthy?\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nThe falsy values are false, 0, -0, 0n, \"\", null, undefined and NaN. Everything else is truthy, including [], {} and the strings \"0\" and \"false\".",
        "key_points": [
            "The falsy values are false, 0, -0, 0n, \"\", null, undefined and NaN.",
            "Everything else is truthy, including [], {} and the strings \"0\" and \"false\".",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js03-sum-to": {
        "body": "When implementing `sumTo(n)` in JavaScript, what core invariants must you satisfy?\n\nWrite `sumTo(n)` with a `for` loop: return 1 + 2 + \u2026 + n. `sumTo(0)` is 0.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`i <= n` includes n itself; `i < n` is the classic off-by-one that stops one short.",
        "key_points": [
            "`i <= n` includes n itself; `i < n` is the classic off-by-one that stops one short.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js03-count-vowels": {
        "body": "When implementing `countVowels(text)` in JavaScript, what core invariants must you satisfy?\n\nWrite `countVowels(text)` using `for...of`: count a, e, i, o and u in either case.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`for...of` gives each character of a string. Lower-case once so one check covers both cases.",
        "key_points": [
            "`for...of` gives each character of a string.",
            "Lower-case once so one check covers both cases.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js03-fizzbuzz": {
        "body": "When implementing `fizzBuzz(n)` in JavaScript, what core invariants must you satisfy?\n\nWrite `fizzBuzz(n)`: return an array of strings for 1..n \u2014 `\"Fizz\"` for multiples of 3, `\"Buzz\"` for multiples of 5, `\"FizzBuzz\"` for both, otherwise the number as a string.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nTest the most specific case (divisible by both) first, or 15 is caught by the 3 check. The remainder operator % tells you divisibility.",
        "key_points": [
            "Test the most specific case (divisible by both) first, or 15 is caught by the 3 check.",
            "The remainder operator % tells you divisibility.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js03-first-index-over": {
        "body": "When implementing `firstIndexOver(nums, limit)` in JavaScript, what core invariants must you satisfy?\n\nWrite `firstIndexOver(nums, limit)`: return the index of the first number greater than `limit`, or -1 if there is none. Stop as soon as you find it.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`return` inside the loop ends it at the first match. Without it you would keep overwriting the answer and end up with the last match.",
        "key_points": [
            "`return` inside the loop ends it at the first match.",
            "Without it you would keep overwriting the answer and end up with the last match.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js03-closure-in-loop": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nvar makes one i for the whole loop, so every function sees its final value, 3. let makes a fresh j for each iteration, so each function keeps its own.",
        "key_points": [
            "var makes one i for the whole loop, so every function sees its final value, 3.",
            "let makes a fresh j for each iteration, so each function keeps its own.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js03-for-in-vs-of": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nfor...in visits every enumerable string key, extra and inherited properties included, and gives indexes as strings. Use for...of for the values of an array.",
        "key_points": [
            "for...in visits every enumerable string key, extra and inherited properties included, and gives indexes as strings.",
            "Use for...of for the values of an array.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js04-capitalize": {
        "body": "When implementing `capitalize(word)` in JavaScript, what core invariants must you satisfy?\n\nWrite `capitalize(word)`: first letter upper-case, the rest lower-case. `\"\"` stays `\"\"`.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`word[0]` is undefined for \"\", and calling a method on undefined throws. `slice(1)` returns everything after the first character.",
        "key_points": [
            "`word[0]` is undefined for \"\", and calling a method on undefined throws.",
            "`slice(1)` returns everything after the first character.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js04-palindrome": {
        "body": "When implementing `isPalindrome(text)` in JavaScript, what core invariants must you satisfy?\n\nWrite `isPalindrome(text)`: true if `text` reads the same backwards, ignoring case, spaces and punctuation.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nClean the text first, then compare it with its reverse. Strings have no reverse(): spread into an array, reverse, and join back.",
        "key_points": [
            "Clean the text first, then compare it with its reverse.",
            "Strings have no reverse(): spread into an array, reverse, and join back.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js04-initials": {
        "body": "When implementing `initials(fullName)` in JavaScript, what core invariants must you satisfy?\n\nWrite `initials(fullName)`: `\"Ada Lovelace\"` \u2192 `\"A.L.\"`. Names may be lower-case and have extra spaces.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`split(\" \")` leaves empty strings between repeated spaces; trim first and split on the pattern /\\s+/ (one or more whitespace characters).",
        "key_points": [
            "`split(\" \")` leaves empty strings between repeated spaces; trim first and split on the pattern /\\s+/ (one or more whitespace characters).",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js04-plus-coercion": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\n+ concatenates as soon as either side is a string; -, * and / convert to numbers. Evaluation runs left to right: 1 + 2 is 3 before \"3\" is joined on.",
        "key_points": [
            "+ concatenates as soon as either side is a string; -, * and / convert to numbers.",
            "Evaluation runs left to right: 1 + 2 is 3 before \"3\" is joined on.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js04-immutable": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nString methods return new strings; the original never changes.",
        "key_points": [
            "String methods return new strings; the original never changes.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js05-hoisting": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nA function declaration is created before any code runs. A const is not usable until its line runs, so calling it earlier throws a ReferenceError.",
        "key_points": [
            "A function declaration is created before any code runs.",
            "A const is not usable until its line runs, so calling it earlier throws a ReferenceError.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js05-make-counter": {
        "body": "When implementing `makeCounter(start)` in JavaScript, what core invariants must you satisfy?\n\nWrite `makeCounter(start)`: return an object with `increment()` (adds 1, returns the new count) and `current()`. Each counter must keep its own private count. Don't change `check`.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nEach call to makeCounter creates a new `count`, and the returned methods close over that one. A variable outside the function would be shared by every counter.",
        "key_points": [
            "Each call to makeCounter creates a new `count`, and the returned methods close over that one.",
            "A variable outside the function would be shared by every counter.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js05-once": {
        "body": "When implementing `once(fn)` in JavaScript, what core invariants must you satisfy?\n\nWrite `once(fn)`: return a function that calls `fn` the first time only and returns that first result on every later call \u2014 even when the result is `undefined`. Don't change `check`.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nTrack \"already called\" in its own flag. Using the result itself as the flag breaks for a function that returns undefined: it gets called again.",
        "key_points": [
            "Track \"already called\" in its own flag.",
            "Using the result itself as the flag breaks for a function that returns undefined: it gets called again.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js05-sum-rest": {
        "body": "When implementing `sum(...numbers)` in JavaScript, what core invariants must you satisfy?\n\nWrite `sum(...numbers)`: add up any number of arguments. `sum()` is 0.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`...numbers` gathers all arguments into a real array. reduce needs the initial value 0, or an empty array throws a TypeError.",
        "key_points": [
            "`...numbers` gathers all arguments into a real array.",
            "reduce needs the initial value 0, or an empty array throws a TypeError.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js06-sort-default": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nWithout a compare function, sort compares the items as strings, and \"100\" comes before \"9\". (a, b) => a - b sorts numbers ascending. sort also changes the array in place.",
        "key_points": [
            "Without a compare function, sort compares the items as strings, and \"100\" comes before \"9\".",
            "(a, b) => a - b sorts numbers ascending.",
            "sort also changes the array in place.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js06-squares-of-evens": {
        "body": "When implementing `squaresOfEvens(nums)` in JavaScript, what core invariants must you satisfy?\n\nWrite `squaresOfEvens(nums)` with `filter` and `map`: the squares of the even numbers, in order.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nfilter keeps the items whose callback returns true; map returns a new array of the same length.",
        "key_points": [
            "filter keeps the items whose callback returns true; map returns a new array of the same length.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js06-average": {
        "body": "When implementing `average(nums)` in JavaScript, what core invariants must you satisfy?\n\nWrite `average(nums)` using `reduce`: the mean of the numbers, or 0 for an empty array.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nreduce without a starting value throws on an empty array, and 0 / 0 is NaN, so an empty array needs its own answer.",
        "key_points": [
            "reduce without a starting value throws on an empty array, and 0 / 0 is NaN, so an empty array needs its own answer.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js06-foreach-returns-undefined": {
        "body": "When implementing `Fix doubled(nums)` in JavaScript, what core invariants must you satisfy?\n\n`doubled(nums)` should return a new array with every number doubled, but it returns `undefined`. Fix it.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nforEach runs the callback for its side effects and always returns undefined. To build a new array from the results, use map.",
        "key_points": [
            "forEach runs the callback for its side effects and always returns undefined.",
            "To build a new array from the results, use map.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js06-group-by-category": {
        "body": "When implementing `groupByCategory(items)` in JavaScript, what core invariants must you satisfy?\n\nWrite `groupByCategory(items)` with `reduce`: given `{ name, category }` objects, return an object mapping each category to the names in it, in order.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nThe accumulator starts as {} and must be returned from every callback. Create the category's array the first time you see it, then push.",
        "key_points": [
            "The accumulator starts as {} and must be returned from every callback.",
            "Create the category's array the first time you see it, then push.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js06-shared-reference": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nalias = original copies the reference, so both names point at one array. [...original] builds a new array with the same items.",
        "key_points": [
            "alias = original copies the reference, so both names point at one array.",
            "[...original] builds a new array with the same items.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js07-format-user": {
        "body": "When implementing `formatUser(user)` in JavaScript, what core invariants must you satisfy?\n\nWrite `formatUser(user)`: given `{ firstName, lastName, role }`, return `\"LastName, FirstName (ROLE)\"` with the role in upper case. A missing role means `\"GUEST\"`. Use destructuring with a default.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nA destructuring default applies when the property is missing or undefined (not for null or \"\").",
        "key_points": [
            "A destructuring default applies when the property is missing or undefined (not for null or \"\").",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js07-shallow-spread": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nSpread copies the top-level properties. copy.name is its own string, but copy.skills is the same array as original.skills. For a deep copy use structuredClone.",
        "key_points": [
            "Spread copies the top-level properties.",
            "copy.name is its own string, but copy.skills is the same array as original.skills.",
            "For a deep copy use structuredClone.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js07-with-defaults": {
        "body": "When implementing `withDefaults(options)` in JavaScript, what core invariants must you satisfy?\n\nWrite `withDefaults(options)`: return a new object starting from `{ theme: \"light\", fontSize: 14, autosave: true }`, overridden by whatever `options` sets. Use spread.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nLater properties win, so spread the defaults first and the overrides second.",
        "key_points": [
            "Later properties win, so spread the defaults first and the overrides second.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js07-pick": {
        "body": "When implementing `pick(obj, keys)` in JavaScript, what core invariants must you satisfy?\n\nWrite `pick(obj, keys)`: a new object with only the listed keys that `obj` actually has. Keep keys whose value is `null`.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`key in obj` asks whether the property exists. Testing its value instead drops real properties that hold null, 0 or \"\", and copying blindly adds undefined keys.",
        "key_points": [
            "`key in obj` asks whether the property exists.",
            "Testing its value instead drops real properties that hold null, 0 or \"\", and copying blindly adds undefined keys.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js07-optional-chaining": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\n?. returns undefined as soon as the value on its left is null or undefined. Plain . on null throws a TypeError.",
        "key_points": [
            "returns undefined as soon as the value on its left is null or undefined.",
            "on null throws a TypeError.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js08-unique": {
        "body": "When implementing `unique(values)` in JavaScript, what core invariants must you satisfy?\n\nWrite `unique(values)` with a `Set`: the values without duplicates, in first-seen order.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nA Set keeps one of each value, compared with ===, in insertion order. Spread it back into an array.",
        "key_points": [
            "A Set keeps one of each value, compared with ===, in insertion order.",
            "Spread it back into an array.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js08-most-frequent-word": {
        "body": "When implementing `mostFrequentWord(text)` in JavaScript, what core invariants must you satisfy?\n\nWrite `mostFrequentWord(text)` with a `Map`: the most common word, lower-cased. On a tie, return the word that appeared first. Empty text gives `\"\"`.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nA Map iterates in insertion order, so a strict > keeps the first word on a tie. `counts.get(word) ?? 0` starts a new word at zero.",
        "key_points": [
            "A Map iterates in insertion order, so a strict > keeps the first word on a tie.",
            "`counts.get(word) ??",
            "0` starts a new word at zero.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js08-map-keys": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nObject keys are strings, so 1 and \"1\" are the same key and the second write replaces the first. A Map keeps the number 1 and the string \"1\" apart.",
        "key_points": [
            "Object keys are strings, so 1 and \"1\" are the same key and the second write replaces the first.",
            "A Map keeps the number 1 and the string \"1\" apart.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js08-group-by-map": {
        "body": "When implementing `Fix groupByCategory for any category` in JavaScript, what core invariants must you satisfy?\n\nThis `groupByCategory(items)` crashes when a category is called `\"constructor\"` or `\"toString\"`. Fix it by grouping in a `Map`, then return a plain object with `Object.fromEntries`.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nEvery plain object inherits properties like constructor and toString, so `groups[\"constructor\"]` already exists and isn't an array. A Map starts truly empty.",
        "key_points": [
            "Every plain object inherits properties like constructor and toString, so `groups[\"constructor\"]` already exists and isn't an array.",
            "A Map starts truly empty.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js09-factorial": {
        "body": "When implementing `factorial(n)` in JavaScript, what core invariants must you satisfy?\n\nWrite `factorial(n)` recursively: n \u00d7 (n \u2212 1) \u00d7 \u2026 \u00d7 1, with `factorial(0)` = 1.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nWithout a base case that covers 0, factorial(0) recurses forever and overflows the stack.",
        "key_points": [
            "Without a base case that covers 0, factorial(0) recurses forever and overflows the stack.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js09-sum-nested": {
        "body": "When implementing `sumNested(items)` in JavaScript, what core invariants must you satisfy?\n\nWrite `sumNested(items)`: add every number in an array whose items can be arrays, nested to any depth.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nEach array is the same problem, smaller. `flat()` only removes one level of nesting.",
        "key_points": [
            "Each array is the same problem, smaller.",
            "`flat()` only removes one level of nesting.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js09-count-files": {
        "body": "When implementing `countFiles(folder)` in JavaScript, what core invariants must you satisfy?\n\nA folder is `{ name, files: string[], folders: Folder[] }`. Write `countFiles(folder)`: the number of files in it and every folder below it.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nThe base case is a folder with no sub-folders: the loop doesn't run and it returns its own file count.",
        "key_points": [
            "The base case is a folder with no sub-folders: the loop doesn't run and it returns its own file count.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js09-trace": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nEach call waits for the smaller call to return, then puts its own number in front.",
        "key_points": [
            "Each call waits for the smaller call to return, then puts its own number in front.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js10-parse-age": {
        "body": "When implementing `parseAge(text)` in JavaScript, what core invariants must you satisfy?\n\nWrite `parseAge(text)`: return the age as a number. For anything that isn't a whole number from 0 to 150 (including empty text), throw a `RangeError` with the message `\"age must be a whole number from 0 to 150\"`.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nThrow the most specific built-in error (RangeError for out-of-range values) so callers can tell failures apart. Number(\"\") is 0, so empty input needs its own check.",
        "key_points": [
            "Throw the most specific built-in error (RangeError for out-of-range values) so callers can tell failures apart.",
            "Number(\"\") is 0, so empty input needs its own check.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js10-finally": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nfinally runs on every exit from the try block, return included, before the caller gets the value.",
        "key_points": [
            "finally runs on every exit from the try block, return included, before the caller gets the value.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js10-dont-swallow": {
        "body": "When implementing `Fix readConfig(json)` in JavaScript, what core invariants must you satisfy?\n\n`readConfig(json)` hides broken input by returning `{}`, so callers never find out the config is invalid. Let a parse error reach the caller, but keep returning `{}` for empty or blank text.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nSwallowing an error turns \"your file is broken\" into \"you have no settings\". Handle the case you expect (empty text) and let real errors propagate.",
        "key_points": [
            "Swallowing an error turns \"your file is broken\" into \"you have no settings\".",
            "Handle the case you expect (empty text) and let real errors propagate.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js10-custom-error": {
        "body": "When implementing `ValidationError` in JavaScript, what core invariants must you satisfy?\n\nMake `ValidationError` an error whose `name` is `\"ValidationError\"`. Then make `validateUser(user)` throw one with the message `\"name is required\"` or `\"email is required\"` when that field is missing or empty, and return `true` otherwise.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nA subclass of Error inherits message and stack, but its name stays \"Error\" unless you set it. Callers can then check `error instanceof ValidationError`.",
        "key_points": [
            "A subclass of Error inherits message and stack, but its name stays \"Error\" unless you set it.",
            "Callers can then check `error instanceof ValidationError`.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js11-stringify-drops": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nundefined and functions are not JSON: they are left out of objects and become null in arrays. A Date is written as its ISO string (and comes back as a string, not a Date).",
        "key_points": [
            "undefined and functions are not JSON: they are left out of objects and become null in arrays.",
            "A Date is written as its ISO string (and comes back as a string, not a Date).",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js11-load-settings": {
        "body": "When implementing `loadSettings(json)` in JavaScript, what core invariants must you satisfy?\n\nWrite `loadSettings(json)`: parse the JSON text and return `{ volume, muted }`, with `volume` 50 and `muted` false when missing. A saved 0 or false must be kept. Ignore any other fields.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nBuild the result from just the fields you want, with `??` so real 0 and false values survive.",
        "key_points": [
            "Build the result from just the fields you want, with `??` so real 0 and false values survive.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js11-pretty": {
        "body": "When implementing `prettyJson(text)` in JavaScript, what core invariants must you satisfy?\n\nWrite `prettyJson(text)`: reformat compact JSON text with 2-space indentation.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nThe third argument of JSON.stringify is the indentation. Stringifying the text itself (without parsing) just wraps it in quotes.",
        "key_points": [
            "The third argument of JSON.stringify is the indentation.",
            "Stringifying the text itself (without parsing) just wraps it in quotes.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js11-map-to-json": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nJSON.stringify only writes an object's own enumerable properties, and a Map has none. Convert it first.",
        "key_points": [
            "JSON.stringify only writes an object's own enumerable properties, and a Map has none.",
            "Convert it first.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js12-bank-account": {
        "body": "When implementing `class BankAccount` in JavaScript, what core invariants must you satisfy?\n\nFinish `BankAccount`: keep the balance in a private `#balance` field starting at 0. `deposit(amount)` and `withdraw(amount)` return the new balance; `getBalance()` returns it. Throw `RangeError(\"deposit must be positive\")` for a deposit of 0 or less and `RangeError(\"insufficient funds\")` when withdrawing more than the balance. Don't change `run`.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nA # field can only be read inside the class: `account.balance` from outside is undefined. Validate before changing state so a failed call leaves it untouched.",
        "key_points": [
            "A # field can only be read inside the class: `account.balance` from outside is undefined.",
            "Validate before changing state so a failed call leaves it untouched.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js12-lost-this": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nthis is set by how a function is called, not where it was defined. Called on its own, greet gets this = undefined (class code is strict), so this.name throws. call() passes this for one call; bind() makes a copy with this fixed.",
        "key_points": [
            "this is set by how a function is called, not where it was defined.",
            "Called on its own, greet gets this = undefined (class code is strict), so this.name throws.",
            "call() passes this for one call; bind() makes a copy with this fixed.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js12-this-in-callback": {
        "body": "When implementing `Fix Cart.total()` in JavaScript, what core invariants must you satisfy?\n\n`total()` throws a TypeError: inside the `function` callback, `this` is not the cart. Fix it. Don't change `check`.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nA `function` callback gets its own `this` (undefined here). An arrow function has no `this` of its own, so it uses the method's.",
        "key_points": [
            "A `function` callback gets its own `this` (undefined here).",
            "An arrow function has no `this` of its own, so it uses the method's.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js12-inheritance": {
        "body": "When implementing `Circle and Rectangle extend Shape` in JavaScript, what core invariants must you satisfy?\n\nWrite `Circle` (constructor `radius`, name `\"circle\"`, area \u03c0r\u00b2) and `Rectangle` (constructor `width, height`, name `\"rectangle\"`) so both extend `Shape`, call `super(name)`, and implement `area()`. Don't change `check` or `Shape`.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nA subclass must call super() before it uses `this`. It inherits describe() and overrides area(), so Shape's describe() calls the right area for each shape.",
        "key_points": [
            "A subclass must call super() before it uses `this`.",
            "It inherits describe() and overrides area(), so Shape's describe() calls the right area for each shape.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js13-event-loop": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nSynchronous code runs first (A, D). Then the microtask queue \u2014 promise callbacks \u2014 is emptied (C). Timers run after that, even with a 0 ms delay (B).",
        "key_points": [
            "Synchronous code runs first (A, D).",
            "Then the microtask queue \u2014 promise callbacks \u2014 is emptied (C).",
            "Timers run after that, even with a 0 ms delay (B).",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js13-load-names": {
        "body": "When implementing `Make loadNames(ids) concurrent` in JavaScript, what core invariants must you satisfy?\n\n`loadNames(ids)` returns the right names but fetches one user at a time. Make all the `getUser` calls run at once with `Promise.all`, keeping the names in the order of `ids`. Don't change `check` or `getUser`.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`await` in a loop waits for each request before starting the next. Start them all with map, then await Promise.all, which keeps results in input order.",
        "key_points": [
            "`await` in a loop waits for each request before starting the next.",
            "Start them all with map, then await Promise.all, which keeps results in input order.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js13-fetch-ok": {
        "body": "When implementing `Fix getJson(url)` in JavaScript, what core invariants must you satisfy?\n\n`getJson(url)` returns the error page's body when the server answers 404 or 500. Throw `new Error(`HTTP ${status}`)` (e.g. `\"HTTP 404\"`) when the response isn't ok. Don't change the fake `fetch`.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nAn HTTP error is still a successful fetch: the promise resolves with the response. `response.ok` is true only for 200\u2013299, so check it before reading the body.",
        "key_points": [
            "An HTTP error is still a successful fetch: the promise resolves with the response.",
            "`response.ok` is true only for 200\u2013299, so check it before reading the body.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "js13-all-vs-allsettled": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nPromise.all rejects with the first rejection. Promise.allSettled always fulfills, with a status for each promise. Neither one starts the work: the promises were already running when created.",
        "key_points": [
            "Promise.all rejects with the first rejection.",
            "Promise.allSettled always fulfills, with a status for each promise.",
            "Neither one starts the work: the promises were already running when created.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js14-default-and-named": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nThe default export is imported without braces, under any name you choose. Named exports go in braces and must match the exported name.",
        "key_points": [
            "The default export is imported without braces, under any name you choose.",
            "Named exports go in braces and must match the exported name.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js14-missing-named-export": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nadd is the default export, not a named one. Imports are checked before any code runs, so nothing is printed. Write `import add from \"./math.js\"`.",
        "key_points": [
            "add is the default export, not a named one.",
            "Imports are checked before any code runs, so nothing is printed.",
            "Write `import add from \"./math.js\"`.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "js14-shared-state": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the JavaScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nA module is evaluated once. Both imports are the same function, closing over the same count.",
        "key_points": [
            "A module is evaluated once.",
            "Both imports are the same function, closing over the same count.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "ts15-emits-anyway": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the TypeScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nTypes are erased before the code runs, so they cannot convert or check values. count is really the string \"3\" (so + concatenates) and label the number 42. Fix type errors; don't silence them with any.",
        "key_points": [
            "Types are erased before the code runs, so they cannot convert or check values.",
            "count is really the string \"3\" (so + concatenates) and label the number 42.",
            "Fix type errors; don't silence them with any.",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "ts15-enum-emits": {
        "body": "Before predicting the runtime outcome, trace execution step-by-step through the TypeScript engine:\n\nAsk yourself: How does the runtime resolve binding, scope, or evaluation in this scenario? Where might intuition differ from the ECMAScript specification?\n\nenum is one of the few TypeScript features that is not erased: it compiles to a real object. A numeric enum also maps numbers back to names, so it has four keys: \"0\", \"1\", \"Up\" and \"Down\".",
        "key_points": [
            "enum is one of the few TypeScript features that is not erased: it compiles to a real object.",
            "A numeric enum also maps numbers back to names, so it has four keys: \"0\", \"1\", \"Up\" and \"Down\".",
            "Verify language evaluation order and object identity rather than assumptions."
        ]
    },
    "ts15-parse-user": {
        "body": "When implementing `parseUser(data: unknown)` in TypeScript, what core invariants must you satisfy?\n\n`data` came from `JSON.parse`, so its type is `unknown`. Return a `User` (only its `name` and `age`) when `data` is an object with a string `name` and a number `age`; otherwise return `null`. The `as User` in the starter checks nothing.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nA type annotation or `as` only tells the compiler what to assume. For data from outside, check it with typeof and `in`; TypeScript narrows `unknown` as you go.",
        "key_points": [
            "A type annotation or `as` only tells the compiler what to assume.",
            "For data from outside, check it with typeof and `in`; TypeScript narrows `unknown` as you go.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts16-total-price": {
        "body": "When implementing `Add types to totalPrice` in TypeScript, what core invariants must you satisfy?\n\nThis JavaScript doesn't compile under `strict`: its parameters are implicitly `any`. Add types \u2014 items are `{ price: number; quantity: number }` \u2014 so it compiles and rejects bad calls.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nParameters are where types matter most: inside the function TypeScript infers the rest (`sum`, `item`, `subtotal`). Typing them `any` compiles but checks nothing.",
        "key_points": [
            "Parameters are where types matter most: inside the function TypeScript infers the rest (`sum`, `item`, `subtotal`).",
            "Typing them `any` compiles but checks nothing.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts16-inferred-type": {
        "body": "When the TypeScript compiler checks this code under `--strict`, what safety invariants does it verify?\n\nExamine each statement through the eyes of the type checker: Does the compiler have enough information to guarantee soundness? Ask yourself: Where does a potential type hole or unproven contract trigger a compile diagnostic?\n\ncount was inferred as number from its initial value, and that type sticks. label had no initial value, so its type follows each assignment.",
        "key_points": [
            "count was inferred as number from its initial value, and that type sticks.",
            "label had no initial value, so its type follows each assignment.",
            "Under strict mode, unverified indexing or missing cases produce compile errors."
        ]
    },
    "ts16-format-price": {
        "body": "When implementing `Fix formatPrice(cents)` in TypeScript, what core invariants must you satisfy?\n\nThis doesn't compile: the return type says `string` but the body returns a number. Return the price as dollars with two decimals, e.g. 1250 \u2192 `\"$12.50\"`.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nA return type annotation turns \"returns the wrong kind of value\" into a compile error at the function, instead of a bug wherever it is used. toFixed(2) keeps \"12.50\".",
        "key_points": [
            "A return type annotation turns \"returns the wrong kind of value\" into a compile error at the function, instead of a bug wherever it is used.",
            "toFixed(2) keeps \"12.50\".",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts17-product": {
        "body": "When implementing `interface Product` in TypeScript, what core invariants must you satisfy?\n\nWrite an interface `Product` with `id` and `name` (strings), `price` (number) and an optional numeric `discount`, then type `finalPrice` with it.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`discount?: number` means the property may be missing, so its type inside the function is number | undefined \u2014 which is why `?? 0` is needed.",
        "key_points": [
            "`discount?: number` means the property may be missing, so its type inside the function is number | undefined \u2014 which is why `??",
            "0` is needed.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts17-excess-property": {
        "body": "When the TypeScript compiler checks this code under `--strict`, what safety invariants does it verify?\n\nExamine each statement through the eyes of the type checker: Does the compiler have enough information to guarantee soundness? Ask yourself: Where does a potential type hole or unproven contract trigger a compile diagnostic?\n\nAn object literal written straight into a call gets an excess property check, since an unknown property there is probably a typo. A variable is just checked for having x and y.",
        "key_points": [
            "An object literal written straight into a call gets an excess property check, since an unknown property there is probably a typo.",
            "A variable is just checked for having x and y.",
            "Under strict mode, unverified indexing or missing cases produce compile errors."
        ]
    },
    "ts17-readonly-sort": {
        "body": "When implementing `Fix sortedCopy(nums)` in TypeScript, what core invariants must you satisfy?\n\n`sortedCopy` must not change its input, so its parameter is `readonly number[]` \u2014 and now it doesn't compile, because `sort` sorts in place. Fix it.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nA readonly array type has no mutating methods (push, sort, splice\u2026), so the compiler catches the accidental mutation. Copy first, or use toSorted().",
        "key_points": [
            "A readonly array type has no mutating methods (push, sort, splice\u2026), so the compiler catches the accidental mutation.",
            "Copy first, or use toSorted().",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts17-structural": {
        "body": "When the TypeScript compiler checks this code under `--strict`, what safety invariants does it verify?\n\nExamine each statement through the eyes of the type checker: Does the compiler have enough information to guarantee soundness? Ask yourself: Where does a potential type hole or unproven contract trigger a compile diagnostic?\n\nTypeScript compares shapes, not class names: a Dog has a string name, so it is a Named. The literal has no name (and an unknown title).",
        "key_points": [
            "TypeScript compares shapes, not class names: a Dog has a string name, so it is a Named.",
            "The literal has no name (and an unknown title).",
            "Under strict mode, unverified indexing or missing cases produce compile errors."
        ]
    },
    "ts18-format-id": {
        "body": "When implementing `Fix formatId(id)` in TypeScript, what core invariants must you satisfy?\n\nThis doesn't compile: `toUpperCase` doesn't exist on numbers. Narrow the union: numbers become 6 digits with leading zeros (`42` \u2192 `\"000042\"`), strings are upper-cased.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nAfter `typeof id === \"number\"` returns, TypeScript knows id is a string on the next line.",
        "key_points": [
            "After `typeof id === \"number\"` returns, TypeScript knows id is a string on the next line.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts18-describe-input": {
        "body": "When implementing `describeInput(value)` in TypeScript, what core invariants must you satisfy?\n\nWrite `describeInput(value: string | string[] | null): string` \u2014 `\"nothing\"` for null, `\"text: <value>\"` for a string, `\"list of <n>\"` for an array.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nCheck null and arrays first; whatever is left must be a string. An empty string is not null.",
        "key_points": [
            "Check null and arrays first; whatever is left must be a string.",
            "An empty string is not null.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts18-is-string": {
        "body": "When implementing `Type guard isString` in TypeScript, what core invariants must you satisfy?\n\n`isString` works at run time, but `[\"a\", 1].filter(isString)` still has the type `(string | number)[]`. Change its return type to a type predicate so the filter result is `string[]`.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`value is string` tells TypeScript that true means \"value is a string\", and filter uses that to narrow its result. The compiler does not check that your body really tests for a string: a wrong guard lies to it.",
        "key_points": [
            "`value is string` tells TypeScript that true means \"value is a string\", and filter uses that to narrow its result.",
            "The compiler does not check that your body really tests for a string: a wrong guard lies to it.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts18-union-access": {
        "body": "When the TypeScript compiler checks this code under `--strict`, what safety invariants does it verify?\n\nExamine each statement through the eyes of the type checker: Does the compiler have enough information to guarantee soundness? Ask yourself: Where does a potential type hole or unproven contract trigger a compile diagnostic?\n\nWithout narrowing you may only use what every member of the union has. Both strings and arrays have length; numbers have no toUpperCase.",
        "key_points": [
            "Without narrowing you may only use what every member of the union has.",
            "Both strings and arrays have length; numbers have no toUpperCase.",
            "Under strict mode, unverified indexing or missing cases produce compile errors."
        ]
    },
    "ts19-greet": {
        "body": "When implementing `greet(name, greeting?, punctuation?)` in TypeScript, what core invariants must you satisfy?\n\nWrite `greet`: `greeting` defaults to `\"Hello\"` and `punctuation` is optional (`\"!\"` when missing). `greet(\"Ada\")` \u2192 `\"Hello, Ada!\"`.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nA default value also gives the parameter its type (string) and makes it optional; passing undefined uses the default.",
        "key_points": [
            "A default value also gives the parameter its type (string) and makes it optional; passing undefined uses the default.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts19-undefined-return": {
        "body": "When the TypeScript compiler checks this code under `--strict`, what safety invariants does it verify?\n\nExamine each statement through the eyes of the type checker: Does the compiler have enough information to guarantee soundness? Ask yourself: Where does a potential type hole or unproven contract trigger a compile diagnostic?\n\nSince TypeScript 5.1, a function that returns undefined needs no return statement, just like JavaScript. A function promising a string must return one.",
        "key_points": [
            "Since TypeScript 5.1, a function that returns undefined needs no return statement, just like JavaScript.",
            "A function promising a string must return one.",
            "Under strict mode, unverified indexing or missing cases produce compile errors."
        ]
    },
    "ts19-overloads": {
        "body": "When implementing `Overloads for parse(value)` in TypeScript, what core invariants must you satisfy?\n\n`parse` turns a string into a number and a number into a 2-decimal string, but callers always get `string | number`. Add overload signatures so `parse(\"42\")` is a number and `parse(3)` a string.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nCallers see only the overload signatures; the last signature is the implementation's and must be compatible with all of them.",
        "key_points": [
            "Callers see only the overload signatures; the last signature is the implementation's and must be compatible with all of them.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts20-any-vs-unknown": {
        "body": "When the TypeScript compiler checks this code under `--strict`, what safety invariants does it verify?\n\nExamine each statement through the eyes of the type checker: Does the compiler have enough information to guarantee soundness? Ask yourself: Where does a potential type hole or unproven contract trigger a compile diagnostic?\n\nany turns checking off; unknown keeps it on and asks you to prove the type first.",
        "key_points": [
            "any turns checking off; unknown keeps it on and asks you to prove the type first.",
            "Under strict mode, unverified indexing or missing cases produce compile errors."
        ]
    },
    "ts20-length-of": {
        "body": "When implementing `Fix lengthOf(value: unknown)` in TypeScript, what core invariants must you satisfy?\n\nThis doesn't compile: `value` is `unknown`. Return the length of a string or array, and 0 for anything else \u2014 including objects that happen to have a `length` property.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nNarrow unknown with real checks. Switching to any compiles, but then anything with a length gets through.",
        "key_points": [
            "Narrow unknown with real checks.",
            "Switching to any compiles, but then anything with a length gets through.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts21-area": {
        "body": "When implementing `area(shape)` in TypeScript, what core invariants must you satisfy?\n\nFinish `area` for every `Shape`, switching on `kind`, and add a `default` branch that assigns `shape` to a `never` variable so a new shape can't be forgotten.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nInside `case \"rect\"`, TypeScript knows shape has width and height. In default every variant has been handled, so shape is `never`; add a variant without a case and that assignment stops compiling.",
        "key_points": [
            "Inside `case \"rect\"`, TypeScript knows shape has width and height.",
            "In default every variant has been handled, so shape is `never`; add a variant without a case and that assignment stops compiling.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts21-exhaustive": {
        "body": "When the TypeScript compiler checks this code under `--strict`, what safety invariants does it verify?\n\nExamine each statement through the eyes of the type checker: Does the compiler have enough information to guarantee soundness? Ask yourself: Where does a potential type hole or unproven contract trigger a compile diagnostic?\n\nAfter the circle and square cases, the only thing shape can still be is a triangle, so it isn't never. Add the missing case and it compiles.",
        "key_points": [
            "After the circle and square cases, the only thing shape can still be is a triangle, so it isn't never.",
            "Add the missing case and it compiles.",
            "Under strict mode, unverified indexing or missing cases produce compile errors."
        ]
    },
    "ts21-counter-actions": {
        "body": "When implementing `Type the counter's actions` in TypeScript, what core invariants must you satisfy?\n\n`Action` is too loose: the compiler accepts `{ type: \"add\" }` with no amount, and actions that don't exist. Replace it with a discriminated union of the three real actions.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nWith one object type per action, \"add\" must carry an amount and unknown types are rejected where the action is created \u2014 and the switch needs no default.",
        "key_points": [
            "With one object type per action, \"add\" must carry an amount and unknown types are rejected where the action is created \u2014 and the switch needs no default.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts22-first-element": {
        "body": "When implementing `firstElement<T>(arr)` in TypeScript, what core invariants must you satisfy?\n\nWrite the generic `firstElement<T>(arr: T[]): T | undefined`: the first item, or `undefined` for an empty array. Callers must keep the item type and be told it might be missing.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nT is filled in from the argument (string[] gives T = string). The `| undefined` is honest about empty arrays: arr[0] has type T, but at run time it can be undefined.",
        "key_points": [
            "T is filled in from the argument (string[] gives T = string).",
            "The `| undefined` is honest about empty arrays: arr[0] has type T, but at run time it can be undefined.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts22-longest": {
        "body": "When implementing `longest<T>(a, b)` in TypeScript, what core invariants must you satisfy?\n\nWrite `longest(a, b)`: return whichever argument is longer (the first on a tie). It must accept anything with a numeric `length` \u2014 strings, arrays \u2014 keep the argument type, and reject numbers.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`T extends { length: number }` lets the body use .length and makes the compiler reject arguments without it, while T still remembers the exact type passed in.",
        "key_points": [
            "`T extends { length: number }` lets the body use .length and makes the compiler reject arguments without it, while T still remembers the exact type passed in.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts22-get-property": {
        "body": "When implementing `getProperty(obj, key)` in TypeScript, what core invariants must you satisfy?\n\nWrite `getProperty(obj, key)` so the key must be one of `obj`'s keys and the result has that property's type.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nkeyof T is the union of T's keys (\"id\" | \"name\"); K extends it, so only real keys are allowed, and T[K] is the type stored under that key.",
        "key_points": [
            "keyof T is the union of T's keys (\"id\" | \"name\"); K extends it, so only real keys are allowed, and T[K] is the type stored under that key.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts22-pluck": {
        "body": "When implementing `pluck(items, key)` in TypeScript, what core invariants must you satisfy?\n\nWrite `pluck(items, key)`: the value of `key` from every item, as an array. Type it so the key must exist on the items and the result has the right element type.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nThe same keyof pattern as getProperty, applied to every item: T[K][] is \"an array of whatever is under K\".",
        "key_points": [
            "The same keyof pattern as getProperty, applied to every item: T[K][] is \"an array of whatever is under K\".",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts23-update-todo": {
        "body": "When implementing `updateTodo(todo, changes)` in TypeScript, what core invariants must you satisfy?\n\nWrite `updateTodo(todo, changes)`: return a new todo with `changes` applied. `changes` may contain any subset of a todo's fields \u2014 and nothing else.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nPartial<Todo> is Todo with every property optional, which is exactly what a patch is.",
        "key_points": [
            "Partial<Todo> is Todo with every property optional, which is exactly what a patch is.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts23-public-user": {
        "body": "When implementing `toPublicUser(user)` in TypeScript, what core invariants must you satisfy?\n\nWrite `toPublicUser(user)`: return the user without `passwordHash`, typed with `Omit` so the compiler also knows the hash is gone.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nRemoving the property at run time (rest destructuring) and in the type (Omit) go together: either one alone leaves a gap.",
        "key_points": [
            "Removing the property at run time (rest destructuring) and in the type (Omit) go together: either one alone leaves a gap.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts23-count-by-role": {
        "body": "When implementing `countByRole(roles)` in TypeScript, what core invariants must you satisfy?\n\nWrite `countByRole(roles)`: how many times each role appears, with every role present (0 if absent). Type the result as `Record<Role, number>`.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nRecord<Role, number> requires every key of Role, so the compiler makes you start each count at 0 \u2014 and rejects roles that don't exist.",
        "key_points": [
            "Record<Role, number> requires every key of Role, so the compiler makes you start each count at 0 \u2014 and rejects roles that don't exist.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts23-readonly-shallow": {
        "body": "When the TypeScript compiler checks this code under `--strict`, what safety invariants does it verify?\n\nExamine each statement through the eyes of the type checker: Does the compiler have enough information to guarantee soundness? Ask yourself: Where does a potential type hole or unproven contract trigger a compile diagnostic?\n\nReadonly only stops reassigning the object's own properties. The array inside can still be changed, and nothing is enforced at run time.",
        "key_points": [
            "Readonly only stops reassigning the object's own properties.",
            "The array inside can still be changed, and nothing is enforced at run time.",
            "Under strict mode, unverified indexing or missing cases produce compile errors."
        ]
    },
    "ts24-temperature": {
        "body": "When implementing `class Temperature` in TypeScript, what core invariants must you satisfy?\n\nRewrite `Temperature` with a private, readonly parameter property `celsius`, a `fahrenheit` getter, and `describe()` returning e.g. `\"100\u00b0C\"`. Don't change `check`.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`constructor(private readonly celsius: number) {}` declares and assigns the field in one go. A getter with no setter is read-only to callers.",
        "key_points": [
            "`constructor(private readonly celsius: number) {}` declares and assigns the field in one go.",
            "A getter with no setter is read-only to callers.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts24-private-vs-hash": {
        "body": "When the TypeScript compiler checks this code under `--strict`, what safety invariants does it verify?\n\nExamine each statement through the eyes of the type checker: Does the compiler have enough information to guarantee soundness? Ask yourself: Where does a potential type hole or unproven contract trigger a compile diagnostic?\n\nTypeScript's private is only checked by the compiler, and bracket access is allowed as an escape hatch. At run time pin is an ordinary property. A #field can't be reached from outside at all.",
        "key_points": [
            "TypeScript's private is only checked by the compiler, and bracket access is allowed as an escape hatch.",
            "At run time pin is an ordinary property.",
            "A #field can't be reached from outside at all.",
            "Under strict mode, unverified indexing or missing cases produce compile errors."
        ]
    },
    "ts24-implements": {
        "body": "When implementing `class MemoryLogger implements Logger` in TypeScript, what core invariants must you satisfy?\n\nWrite `MemoryLogger` so it `implements Logger`: `log` stores messages in a private array and `history()` returns a copy, so callers can't change the stored log. Don't change `check` or `Logger`.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`implements` makes the compiler check the class against the interface. Returning the private array itself would let any caller change it; return a copy.",
        "key_points": [
            "`implements` makes the compiler check the class against the interface.",
            "Returning the private array itself would let any caller change it; return a copy.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "ts25-strict-null": {
        "body": "When the TypeScript compiler checks this code under `--strict`, what safety invariants does it verify?\n\nExamine each statement through the eyes of the type checker: Does the compiler have enough information to guarantee soundness? Ask yourself: Where does a potential type hole or unproven contract trigger a compile diagnostic?\n\nWith strictNullChecks, string | null must be narrowed before use. ?. stops at null and ?? supplies the fallback, so every path returns a string.",
        "key_points": [
            "With strictNullChecks, string | null must be narrowed before use.",
            "stops at null and ??",
            "supplies the fallback, so every path returns a string.",
            "Under strict mode, unverified indexing or missing cases produce compile errors."
        ]
    },
    "ts25-unchecked-index": {
        "body": "When the TypeScript compiler checks this code under `--strict`, what safety invariants does it verify?\n\nExamine each statement through the eyes of the type checker: Does the compiler have enough information to guarantee soundness? Ask yourself: Where does a potential type hole or unproven contract trigger a compile diagnostic?\n\nWith noUncheckedIndexedAccess, scores[0] is number | undefined, because an index may be past the end. Without the flag the same code compiles and would crash on an empty array.",
        "key_points": [
            "With noUncheckedIndexedAccess, scores[0] is number | undefined, because an index may be past the end.",
            "Without the flag the same code compiles and would crash on an empty array.",
            "Under strict mode, unverified indexing or missing cases produce compile errors."
        ]
    },
    "ts25-satisfies": {
        "body": "When the TypeScript compiler checks this code under `--strict`, what safety invariants does it verify?\n\nExamine each statement through the eyes of the type checker: Does the compiler have enough information to guarantee soundness? Ask yourself: Where does a potential type hole or unproven contract trigger a compile diagnostic?\n\nAn annotation replaces the value's type, so annotated.red is just Color. satisfies checks the object against the type but keeps what it inferred: checked.red is a string.",
        "key_points": [
            "An annotation replaces the value's type, so annotated.red is just Color.",
            "satisfies checks the object against the type but keeps what it inferred: checked.red is a string.",
            "Under strict mode, unverified indexing or missing cases produce compile errors."
        ]
    },
    "lab-parse-csv": {
        "body": "When implementing `parseCsv(text)` in JavaScript, what core invariants must you satisfy?\n\nWrite `parseCsv(text)`: the first line holds the column names; turn every other line into an object keyed by them. Trim spaces around cells, skip blank lines, and turn cells that are numbers into numbers (`\"36\"` \u2192 36). No lines at all \u2192 `[]`.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nNumber(\"\") is 0, so test for empty cells before converting. Splitting, trimming and filtering the lines first keeps the row logic simple.",
        "key_points": [
            "Number(\"\") is 0, so test for empty cells before converting.",
            "Splitting, trimming and filtering the lines first keeps the row logic simple.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "lab-inventory": {
        "body": "When implementing `class Inventory` in JavaScript, what core invariants must you satisfy?\n\nFinish `Inventory`, storing quantities in a private `Map`. `add(item, qty)` and `remove(item, qty)` return the new quantity; `count(item)` is 0 for unknown items; `items()` lists items in stock, sorted. Throw `RangeError(\"quantity must be positive\")` for a quantity of 0 or less and `RangeError(\"not enough <item>\")` when removing more than you have. An item that reaches 0 is no longer in stock. Don't change `run`.\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nValidate before changing anything, so a rejected call leaves the stock as it was. Deleting empty items keeps items() honest.",
        "key_points": [
            "Validate before changing anything, so a rejected call leaves the stock as it was.",
            "Deleting empty items keeps items() honest.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "lab-word-wrap": {
        "body": "When implementing `wordWrap(text, width)` in JavaScript, what core invariants must you satisfy?\n\nWrite `wordWrap(text, width)`: split `text` into lines of at most `width` characters, breaking only at spaces. A word longer than `width` gets a line of its own. Return the lines as an array (`[]` for empty text).\n\nConsider how JavaScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nKeep a current line and decide per word whether it fits (+1 for the space). Don't forget to push the last line after the loop.",
        "key_points": [
            "Keep a current line and decide per word whether it fits (+1 for the space).",
            "Don't forget to push the last line after the loop.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "lab-validate-signup": {
        "body": "When implementing `validateSignup(input: unknown)` in TypeScript, what core invariants must you satisfy?\n\nChange `Result` to a discriminated union \u2014 `{ ok: true; value: Signup }` or `{ ok: false; errors: string[] }` \u2014 and write `validateSignup`. Not an object \u2192 `[\"input must be an object\"]`. Otherwise collect, in this order, `\"email is invalid\"` (email must be a string containing \"@\") and `\"age must be 13 or older\"` (a whole number \u2265 13). A valid signup returns only its email and age.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\nWith `ok` as the discriminant, code that checks r.ok gets r.value; code that doesn't can't touch either field. Collect every error before returning, so the user can fix them all at once.",
        "key_points": [
            "With `ok` as the discriminant, code that checks r.ok gets r.value; code that doesn't can't touch either field.",
            "Collect every error before returning, so the user can fix them all at once.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    },
    "lab-todo-reducer": {
        "body": "When implementing `todos(state, action)` in TypeScript, what core invariants must you satisfy?\n\nWrite the reducer `todos(state, action)`. It must never change `state` (typed `readonly`) and always return a new array. `add` appends `{ id, title, done: false }` with id one more than the largest id (1 for an empty list); `toggle` flips `done` on the matching id; `remove` drops it.\n\nConsider how TypeScript handles type boundaries and evaluation order. Ask yourself: What edge cases or false assumptions cause naive solutions to fail?\n\n`readonly Todo[]` makes the compiler reject push, splice and friends on state. map, filter and spread build new arrays. Ids come from the largest id, not the length, or removing an item would reuse an id.",
        "key_points": [
            "`readonly Todo[]` makes the compiler reject push, splice and friends on state.",
            "map, filter and spread build new arrays.",
            "Ids come from the largest id, not the length, or removing an item would reuse an id.",
            "Check edge cases (empty inputs, null/undefined, unexpected types) gracefully."
        ]
    }
}

def get_socratic_lesson(card_key: str) -> tuple[str, list[str]]:
    data = LESSONS.get(card_key)
    if data:
        return data["body"], data["key_points"]
    return "", []

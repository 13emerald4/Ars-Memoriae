"""Canonical Algorithmic Challenges Catalog (LeetCode Problem Studio).

Includes canonical problems spanning core algorithmic patterns:
Sliding Window, Two Pointers, Arrays & Hashing, Stack, Binary Search,
Linked List, Trees, Graphs, Dynamic Programming.
"""

from __future__ import annotations

PROBLEMS_CATALOG = [
    {
        "slug": "find-the-largest-almost-missing-integer",
        "title": "3471. Find the Largest Almost Missing Integer",
        "kind": "problem",
        "difficulty": "Easy",
        "category": "Sliding Window",
        "tags": ["Array", "Hash Table", "Sliding Window"],
        "description": """You are given an integer array `nums` and an integer `k`.

An integer `x` is **almost missing** from `nums` if `x` appears in **exactly one** subarray of size `k` within `nums`.

Return the **largest almost missing** integer from `nums`. If no such integer exists, return `-1`.

A **subarray** is a contiguous sequence of elements within an array.
""",
        "examples": [
            {
                "input": "nums = [3, 9, 2, 1, 7], k = 3",
                "output": "7",
                "explanation": """- 1 appears in 2 subarrays of size 3: [9, 2, 1] and [2, 1, 7].
- 2 appears in 3 subarrays of size 3: [3, 9, 2], [9, 2, 1], [2, 1, 7].
- 3 appears in 1 subarray of size 3: [3, 9, 2].
- 7 appears in 1 subarray of size 3: [2, 1, 7].
- 9 appears in 2 subarrays of size 3: [3, 9, 2], and [9, 2, 1].
We return 7 since it is the largest integer that appears in exactly one subarray of size k.""",
            },
            {
                "input": "nums = [3, 9, 7, 2, 1, 7], k = 4",
                "output": "3",
                "explanation": """- 1 appears in 2 subarrays of size 4: [9, 7, 2, 1], [7, 2, 1, 7].
- 2 appears in 3 subarrays of size 4: [3, 9, 7, 2], [9, 7, 2, 1], [7, 2, 1, 7].
- 3 appears in 1 subarray of size 4: [3, 9, 7, 2].
- 7 appears in 3 subarrays of size 4.
- 9 appears in 2 subarrays of size 4.
We return 3.""",
            },
            {
                "input": "nums = [0, 0], k = 1",
                "output": "-1",
                "explanation": "There is no integer that appears in exactly one subarray of size 1.",
            },
        ],
        "constraints": [
            "1 <= nums.length <= 50",
            "0 <= nums[i] <= 50",
            "1 <= k <= nums.length",
        ],
        "starter_codes": {
            "python": """class Solution:
    def largestInteger(self, nums: list[int], k: int) -> int:
        # Write your solution here
        pass
""",
            "typescript": """function largestInteger(nums: number[], k: number): number {
    // Write your solution here
    return -1;
}
""",
            "cpp": """#include <vector>
#include <unordered_map>
#include <unordered_set>
using namespace std;

class Solution {
public:
    int largestInteger(vector<int>& nums, int k) {
        // Write your solution here
        return -1;
    }
};
""",
        },
        "solutions": {
            "python": """class Solution:
    def largestInteger(self, nums: list[int], k: int) -> int:
        from collections import defaultdict
        n = len(nums)
        subarray_count = defaultdict(int)
        
        # Iterate over all subarrays of size k
        for i in range(n - k + 1):
            unique_in_sub = set(nums[i : i + k])
            for val in unique_in_sub:
                subarray_count[val] += 1
                
        # Find maximum value with frequency == 1
        candidates = [x for x, count in subarray_count.items() if count == 1]
        return max(candidates) if candidates else -1
""",
        },
        "editorial": """### Intuition & Pattern Recognition
We need to count how many distinct subarrays of size $k$ contain each number $x$.
1. A single subarray of length $k$ can contain duplicates of $x$, but it only contributes **1** to $x$'s subarray occurrence count.
2. We extract the unique set of elements for each sliding window of size $k$: `set(nums[i : i + k])`.
3. We increment a hash map counter `subarray_count[x] += 1` for each unique element in that window.
4. Finally, we filter for elements with `subarray_count[x] == 1` and return the maximum, or `-1` if no such element exists.

### Complexity Analysis
- **Time Complexity**: $O((N - k + 1) \\times k)$ to inspect each window of size $k$. Since $N \\le 50$, total operations $\\le 2500$, which runs in $< 1\\text{ms}$.
- **Space Complexity**: $O(N)$ auxiliary space for the frequency map and window set.
""",
        "test_cases": [
            {"input": {"nums": [3, 9, 2, 1, 7], "k": 3}, "expected": 7},
            {"input": {"nums": [3, 9, 7, 2, 1, 7], "k": 4}, "expected": 3},
            {"input": {"nums": [0, 0], "k": 1}, "expected": -1},
            {"input": {"nums": [1, 2, 3], "k": 2}, "expected": 3},
        ],
        "hints": [
            "Use a set to find unique elements in each subarray of size k.",
            "Count in how many subarrays each number appears.",
            "Find the maximum number with a count of exactly 1.",
        ],
    },
    {
        "slug": "two-sum",
        "title": "1. Two Sum",
        "kind": "problem",
        "difficulty": "Easy",
        "category": "Arrays & Hashing",
        "tags": ["Array", "Hash Table"],
        "description": """Given an array of integers `nums` and an integer `target`, return *indices of the two numbers such that they add up to `target`*.

You may assume that each input would have ***exactly one solution***, and you may not use the *same* element twice.

You can return the answer in any order.
""",
        "examples": [
            {
                "input": "nums = [2, 7, 11, 15], target = 9",
                "output": "[0, 1]",
                "explanation": "Because nums[0] + nums[1] == 9, we return [0, 1].",
            },
            {"input": "nums = [3, 2, 4], target = 6", "output": "[1, 2]"},
            {"input": "nums = [3, 3], target = 6", "output": "[0, 1]"},
        ],
        "constraints": [
            "2 <= nums.length <= 10^4",
            "-10^9 <= nums[i] <= 10^9",
            "-10^9 <= target <= 10^9",
            "Only one valid answer exists.",
        ],
        "starter_codes": {
            "python": """class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        # Write your solution here
        pass
""",
            "typescript": """function twoSum(nums: number[], target: number): number[] {
    // Write your solution here
    return [];
}
""",
        },
        "solutions": {
            "python": """class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        seen = {}
        for i, num in enumerate(nums):
            complement = target - num
            if complement in seen:
                return [seen[complement], i]
            seen[num] = i
        return []
"""
        },
        "editorial": """### One-Pass Hash Table
Instead of checking all pairs ($O(N^2)$), compute `complement = target - num`.
Check if `complement` exists in a hash map `seen`. If it does, return `[seen[complement], i]`. Otherwise, store `seen[num] = i`.

### Complexity
- **Time Complexity**: $O(N)$ single pass.
- **Space Complexity**: $O(N)$ for the hash map.
""",
        "test_cases": [
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]},
            {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2]},
            {"input": {"nums": [3, 3], "target": 6}, "expected": [0, 1]},
        ],
        "hints": [
            "What if you store the numbers you've already seen in a hash map?",
            "For each number x, check if target - x is already in the hash map.",
        ],
    },
    {
        "slug": "longest-substring-without-repeating-characters",
        "title": "3. Longest Substring Without Repeating Characters",
        "kind": "problem",
        "difficulty": "Medium",
        "category": "Sliding Window",
        "tags": ["Hash Table", "String", "Sliding Window"],
        "description": """Given a string `s`, find the length of the **longest substring** without repeating characters.
""",
        "examples": [
            {"input": "s = 'abcabcbb'", "output": "3", "explanation": "The answer is 'abc', with length 3."},
            {"input": "s = 'bbbbb'", "output": "1", "explanation": "The answer is 'b', with length 1."},
            {"input": "s = 'pwwkew'", "output": "3", "explanation": "The answer is 'wke', with length 3."},
        ],
        "constraints": ["0 <= s.length <= 5 * 10^4", "s consists of English letters, digits, symbols and spaces."],
        "starter_codes": {
            "python": """class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        # Write your solution here
        pass
"""
        },
        "solutions": {
            "python": """class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        seen = {}
        left = 0
        max_len = 0
        for right, char in enumerate(s):
            if char in seen and seen[char] >= left:
                left = seen[char] + 1
            seen[char] = right
            max_len = max(max_len, right - left + 1)
        return max_len
"""
        },
        "editorial": """### Optimized Sliding Window
Maintain a sliding window `[left, right]` and a hash map `seen` storing each character's last seen index.
When encountering a duplicate `char` within the current window (`seen[char] >= left`), jump `left = seen[char] + 1`.

### Complexity
- **Time Complexity**: $O(N)$ single pass.
- **Space Complexity**: $O(\\min(N, M))$ where $M$ is the character set size.
""",
        "test_cases": [
            {"input": {"s": "abcabcbb"}, "expected": 3},
            {"input": {"s": "bbbbb"}, "expected": 1},
            {"input": {"s": "pwwkew"}, "expected": 3},
            {"input": {"s": ""}, "expected": 0},
        ],
        "hints": ["Use a sliding window with left and right pointers.", "Keep track of the last seen index of each character."],
    },
    {
        "slug": "valid-parentheses",
        "title": "20. Valid Parentheses",
        "kind": "problem",
        "difficulty": "Easy",
        "category": "Stack",
        "tags": ["String", "Stack"],
        "description": """Given a string `s` containing just the characters `'('`, `')'`, `'{'`, `'}'`, `'['` and `']'`, determine if the input string is valid.

An input string is valid if:
1. Open brackets must be closed by the same type of brackets.
2. Open brackets must be closed in the correct order.
3. Every close bracket has a corresponding open bracket of the same type.
""",
        "examples": [
            {"input": "s = '()'", "output": "true"},
            {"input": "s = '()[]{}'", "output": "true"},
            {"input": "s = '(]'", "output": "false"},
        ],
        "constraints": ["1 <= s.length <= 10^4", "s consists of parentheses only '()[]{}'."],
        "starter_codes": {
            "python": """class Solution:
    def isValid(self, s: str) -> bool:
        # Write your solution here
        pass
"""
        },
        "solutions": {
            "python": """class Solution:
    def isValid(self, s: str) -> bool:
        stack = []
        mapping = {')': '(', '}': '{', ']': '['}
        for char in s:
            if char in mapping:
                top = stack.pop() if stack else '#'
                if mapping[char] != top:
                    return False
            else:
                stack.append(char)
        return not stack
"""
        },
        "editorial": """### Stack LIFO Matching
Push opening brackets onto a stack. When a closing bracket is seen, pop from the stack and verify that the popped opening bracket matches the expected closing bracket.

### Complexity
- **Time Complexity**: $O(N)$
- **Space Complexity**: $O(N)$
""",
        "test_cases": [
            {"input": {"s": "()"}, "expected": True},
            {"input": {"s": "()[]{}"}, "expected": True},
            {"input": {"s": "(]"}, "expected": False},
            {"input": {"s": "([)]"}, "expected": False},
        ],
        "hints": ["Use a stack to match the most recent opening bracket."],
    },
    {
        "slug": "climbing-stairs",
        "title": "70. Climbing Stairs",
        "kind": "problem",
        "difficulty": "Easy",
        "category": "Dynamic Programming",
        "tags": ["Math", "Dynamic Programming", "Memoization"],
        "description": """You are climbing a staircase. It takes `n` steps to reach the top.

Each time you can either climb `1` or `2` steps. In how many distinct ways can you climb to the top?
""",
        "examples": [
            {"input": "n = 2", "output": "2", "explanation": "1. 1 step + 1 step\n2. 2 steps"},
            {"input": "n = 3", "output": "3", "explanation": "1. 1 + 1 + 1\n2. 1 + 2\n3. 2 + 1"},
        ],
        "constraints": ["1 <= n <= 45"],
        "starter_codes": {
            "python": """class Solution:
    def climbStairs(self, n: int) -> int:
        # Write your solution here
        pass
"""
        },
        "solutions": {
            "python": """class Solution:
    def climbStairs(self, n: int) -> int:
        if n <= 2:
            return n
        a, b = 1, 2
        for _ in range(3, n + 1):
            a, b = b, a + b
        return b
"""
        },
        "editorial": """### Fibonacci DP State Transition
Let $dp[i]$ be the number of ways to reach step $i$.
To reach step $i$, you either took 1 step from $i-1$ or 2 steps from $i-2$:
$$dp[i] = dp[i-1] + dp[i-2]$$
We can optimize space from $O(N)$ to $O(1)$ by keeping track of the last two states $a$ and $b$.

### Complexity
- **Time Complexity**: $O(N)$
- **Space Complexity**: $O(1)$
""",
        "test_cases": [
            {"input": {"n": 2}, "expected": 2},
            {"input": {"n": 3}, "expected": 3},
            {"input": {"n": 5}, "expected": 8},
        ],
        "hints": ["To reach step n, you must come from either step n-1 or n-2."],
    },
]

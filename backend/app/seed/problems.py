"""
Seed script: inserts all AlgoMaster problems into the database.
Runs on startup; skips if problems already exist.

Loading priority:
  1. If /app/data/problems_data.json exists  → load from it (full data, no LeetCode needed)
  2. Otherwise                               → insert basic placeholder rows
"""
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.problem import Problem
import json
import re

# JSON cache written by export_problems.py after a successful bulk fetch
DATA_FILE = Path("/app/data/problems_data.json")

# ---------------------------------------------------------------------------
# Curated problem list — (title, difficulty, category, leetcode_url)
# Matches algomaster.io, 59 categories, ~500 problems
# ---------------------------------------------------------------------------
PROBLEMS = [
    # ── Arrays ──────────────────────────────────────────────────────────────
    ("Max Consecutive Ones", "Easy", "Arrays", "https://leetcode.com/problems/max-consecutive-ones/"),
    ("Third Maximum Number", "Easy", "Arrays", "https://leetcode.com/problems/third-maximum-number/"),
    ("Move Zeroes", "Easy", "Arrays", "https://leetcode.com/problems/move-zeroes/"),
    ("Shuffle the Array", "Easy", "Arrays", "https://leetcode.com/problems/shuffle-the-array/"),
    ("Majority Element", "Easy", "Arrays", "https://leetcode.com/problems/majority-element/"),
    ("Remove Duplicates from Sorted Array", "Easy", "Arrays", "https://leetcode.com/problems/remove-duplicates-from-sorted-array/"),
    ("Remove Element", "Easy", "Arrays", "https://leetcode.com/problems/remove-element/"),
    ("Best Time to Buy and Sell Stock", "Easy", "Arrays", "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/"),
    ("Missing Ranges", "Easy", "Arrays", "https://leetcode.com/problems/missing-ranges/"),
    ("Majority Element II", "Medium", "Arrays", "https://leetcode.com/problems/majority-element-ii/"),
    ("Rotate Array", "Medium", "Arrays", "https://leetcode.com/problems/rotate-array/"),
    ("Product of Array Except Self", "Medium", "Arrays", "https://leetcode.com/problems/product-of-array-except-self/"),
    ("Remove Duplicates from Sorted Array II", "Medium", "Arrays", "https://leetcode.com/problems/remove-duplicates-from-sorted-array-ii/"),
    ("Best Time to Buy and Sell Stock II", "Medium", "Arrays", "https://leetcode.com/problems/best-time-to-buy-and-sell-stock-ii/"),
    ("Number of Zero-Filled Subarrays", "Medium", "Arrays", "https://leetcode.com/problems/number-of-zero-filled-subarrays/"),
    ("Increasing Triplet Subsequence", "Medium", "Arrays", "https://leetcode.com/problems/increasing-triplet-subsequence/"),
    ("Next Permutation", "Medium", "Arrays", "https://leetcode.com/problems/next-permutation/"),
    ("First Missing Positive", "Hard", "Arrays", "https://leetcode.com/problems/first-missing-positive/"),

    # ── Strings ─────────────────────────────────────────────────────────────
    ("Reverse String", "Easy", "Strings", "https://leetcode.com/problems/reverse-string/"),
    ("Length of Last Word", "Easy", "Strings", "https://leetcode.com/problems/length-of-last-word/"),
    ("Is Subsequence", "Easy", "Strings", "https://leetcode.com/problems/is-subsequence/"),
    ("Valid Palindrome", "Easy", "Strings", "https://leetcode.com/problems/valid-palindrome/"),
    ("Valid Palindrome II", "Easy", "Strings", "https://leetcode.com/problems/valid-palindrome-ii/"),
    ("Valid Anagram", "Easy", "Strings", "https://leetcode.com/problems/valid-anagram/"),
    ("Rotate String", "Easy", "Strings", "https://leetcode.com/problems/rotate-string/"),
    ("Longest Common Prefix", "Easy", "Strings", "https://leetcode.com/problems/longest-common-prefix/"),
    ("Longest Palindrome", "Easy", "Strings", "https://leetcode.com/problems/longest-palindrome/"),
    ("Find the Index of the First Occurrence in a String", "Easy", "Strings", "https://leetcode.com/problems/find-the-index-of-the-first-occurrence-in-a-string/"),
    ("One Edit Distance", "Medium", "Strings", "https://leetcode.com/problems/one-edit-distance/"),
    ("Zigzag Conversion", "Medium", "Strings", "https://leetcode.com/problems/zigzag-conversion/"),
    ("Count and Say", "Medium", "Strings", "https://leetcode.com/problems/count-and-say/"),
    ("Reverse Words in a String", "Medium", "Strings", "https://leetcode.com/problems/reverse-words-in-a-string/"),
    ("Determine if Two Strings Are Close", "Medium", "Strings", "https://leetcode.com/problems/determine-if-two-strings-are-close/"),
    ("Add Bold Tag in String", "Medium", "Strings", "https://leetcode.com/problems/add-bold-tag-in-string/"),
    ("Text Justification", "Hard", "Strings", "https://leetcode.com/problems/text-justification/"),
    ("Guess the Word", "Hard", "Strings", "https://leetcode.com/problems/guess-the-word/"),

    # ── Bit Manipulation ────────────────────────────────────────────────────
    ("Single Number", "Easy", "Bit Manipulation", "https://leetcode.com/problems/single-number/"),
    ("Missing Number", "Easy", "Bit Manipulation", "https://leetcode.com/problems/missing-number/"),
    ("Set Mismatch", "Easy", "Bit Manipulation", "https://leetcode.com/problems/set-mismatch/"),
    ("Power of Two", "Easy", "Bit Manipulation", "https://leetcode.com/problems/power-of-two/"),
    ("Number of 1 Bits", "Easy", "Bit Manipulation", "https://leetcode.com/problems/number-of-1-bits/"),
    ("Counting Bits", "Easy", "Bit Manipulation", "https://leetcode.com/problems/counting-bits/"),
    ("Hamming Distance", "Easy", "Bit Manipulation", "https://leetcode.com/problems/hamming-distance/"),
    ("Reverse Bits", "Easy", "Bit Manipulation", "https://leetcode.com/problems/reverse-bits/"),
    ("Bitwise AND of Numbers Range", "Medium", "Bit Manipulation", "https://leetcode.com/problems/bitwise-and-of-numbers-range/"),
    ("Single Number II", "Medium", "Bit Manipulation", "https://leetcode.com/problems/single-number-ii/"),
    ("Single Number III", "Medium", "Bit Manipulation", "https://leetcode.com/problems/single-number-iii/"),
    ("Sum of Two Integers", "Medium", "Bit Manipulation", "https://leetcode.com/problems/sum-of-two-integers/"),

    # ── Hash Tables ─────────────────────────────────────────────────────────
    ("Design HashMap", "Easy", "Hash Tables", "https://leetcode.com/problems/design-hashmap/"),
    ("Contains Duplicate", "Easy", "Hash Tables", "https://leetcode.com/problems/contains-duplicate/"),
    ("Word Pattern", "Easy", "Hash Tables", "https://leetcode.com/problems/word-pattern/"),
    ("First Unique Character in a String", "Easy", "Hash Tables", "https://leetcode.com/problems/first-unique-character-in-a-string/"),
    ("Find All Numbers Disappeared in an Array", "Easy", "Hash Tables", "https://leetcode.com/problems/find-all-numbers-disappeared-in-an-array/"),
    ("Maximum Number of Balloons", "Easy", "Hash Tables", "https://leetcode.com/problems/maximum-number-of-balloons/"),
    ("Number of Good Pairs", "Easy", "Hash Tables", "https://leetcode.com/problems/number-of-good-pairs/"),
    ("Isomorphic Strings", "Easy", "Hash Tables", "https://leetcode.com/problems/isomorphic-strings/"),
    ("Ransom Note", "Easy", "Hash Tables", "https://leetcode.com/problems/ransom-note/"),
    ("Contains Duplicate II", "Easy", "Hash Tables", "https://leetcode.com/problems/contains-duplicate-ii/"),
    ("Intersection of Two Arrays II", "Easy", "Hash Tables", "https://leetcode.com/problems/intersection-of-two-arrays-ii/"),
    ("Group Anagrams", "Medium", "Hash Tables", "https://leetcode.com/problems/group-anagrams/"),
    ("Encode and Decode TinyURL", "Medium", "Hash Tables", "https://leetcode.com/problems/encode-and-decode-tinyurl/"),
    ("Reorganize String", "Medium", "Hash Tables", "https://leetcode.com/problems/reorganize-string/"),
    ("Longest Consecutive Sequence", "Medium", "Hash Tables", "https://leetcode.com/problems/longest-consecutive-sequence/"),
    ("Split Array into Consecutive Subsequences", "Medium", "Hash Tables", "https://leetcode.com/problems/split-array-into-consecutive-subsequences/"),
    ("Number of Matching Subsequences", "Medium", "Hash Tables", "https://leetcode.com/problems/number-of-matching-subsequences/"),
    ("Number of Good Ways to Split a String", "Medium", "Hash Tables", "https://leetcode.com/problems/number-of-good-ways-to-split-a-string/"),
    ("Group Shifted Strings", "Medium", "Hash Tables", "https://leetcode.com/problems/group-shifted-strings/"),
    ("Minimum Deletions to Make Character Frequencies Unique", "Medium", "Hash Tables", "https://leetcode.com/problems/minimum-deletions-to-make-character-frequencies-unique/"),

    # ── Two Pointers ────────────────────────────────────────────────────────
    ("Merge Sorted Array", "Easy", "Two Pointers", "https://leetcode.com/problems/merge-sorted-array/"),
    ("Merge Strings Alternately", "Easy", "Two Pointers", "https://leetcode.com/problems/merge-strings-alternately/"),
    ("Squares of a Sorted Array", "Easy", "Two Pointers", "https://leetcode.com/problems/squares-of-a-sorted-array/"),
    ("Two Sum", "Easy", "Two Pointers", "https://leetcode.com/problems/two-sum/"),
    ("Backspace String Compare", "Easy", "Two Pointers", "https://leetcode.com/problems/backspace-string-compare/"),
    ("Valid Word Abbreviation", "Easy", "Two Pointers", "https://leetcode.com/problems/valid-word-abbreviation/"),
    ("Count Binary Substrings", "Easy", "Two Pointers", "https://leetcode.com/problems/count-binary-substrings/"),
    ("Two Sum II - Input Array Is Sorted", "Medium", "Two Pointers", "https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/"),
    ("Container With Most Water", "Medium", "Two Pointers", "https://leetcode.com/problems/container-with-most-water/"),
    ("3Sum", "Medium", "Two Pointers", "https://leetcode.com/problems/3sum/"),
    ("4Sum", "Medium", "Two Pointers", "https://leetcode.com/problems/4sum/"),
    ("String Compression", "Medium", "Two Pointers", "https://leetcode.com/problems/string-compression/"),
    ("Boats to Save People", "Medium", "Two Pointers", "https://leetcode.com/problems/boats-to-save-people/"),
    ("Longest Palindromic Substring", "Medium", "Two Pointers", "https://leetcode.com/problems/longest-palindromic-substring/"),
    ("Trapping Rain Water", "Hard", "Two Pointers", "https://leetcode.com/problems/trapping-rain-water/"),
    ("Count Subarrays With Fixed Bounds", "Hard", "Two Pointers", "https://leetcode.com/problems/count-subarrays-with-fixed-bounds/"),

    # ── Prefix Sum ──────────────────────────────────────────────────────────
    ("Running Sum of 1d Array", "Easy", "Prefix Sum", "https://leetcode.com/problems/running-sum-of-1d-array/"),
    ("Range Sum Query - Immutable", "Easy", "Prefix Sum", "https://leetcode.com/problems/range-sum-query-immutable/"),
    ("Find Pivot Index", "Easy", "Prefix Sum", "https://leetcode.com/problems/find-pivot-index/"),
    ("Maximum Population Year", "Easy", "Prefix Sum", "https://leetcode.com/problems/maximum-population-year/"),
    ("Range Addition", "Medium", "Prefix Sum", "https://leetcode.com/problems/range-addition/"),
    ("Subarray Sum Equals K", "Medium", "Prefix Sum", "https://leetcode.com/problems/subarray-sum-equals-k/"),
    ("Subarray Sums Divisible by K", "Medium", "Prefix Sum", "https://leetcode.com/problems/subarray-sums-divisible-by-k/"),
    ("Continuous Subarray Sum", "Medium", "Prefix Sum", "https://leetcode.com/problems/continuous-subarray-sum/"),
    ("Contiguous Array", "Medium", "Prefix Sum", "https://leetcode.com/problems/contiguous-array/"),
    ("Range Sum Query 2D - Immutable", "Medium", "Prefix Sum", "https://leetcode.com/problems/range-sum-query-2d-immutable/"),
    ("Increment Submatrices by One", "Medium", "Prefix Sum", "https://leetcode.com/problems/increment-submatrices-by-one/"),
    ("Matrix Block Sum", "Medium", "Prefix Sum", "https://leetcode.com/problems/matrix-block-sum/"),

    # ── Sliding Window - Fixed Size ──────────────────────────────────────────
    ("Maximum Average Subarray I", "Easy", "Sliding Window - Fixed Size", "https://leetcode.com/problems/maximum-average-subarray-i/"),
    ("Find All Anagrams in a String", "Medium", "Sliding Window - Fixed Size", "https://leetcode.com/problems/find-all-anagrams-in-a-string/"),
    ("Permutation in String", "Medium", "Sliding Window - Fixed Size", "https://leetcode.com/problems/permutation-in-string/"),
    ("Maximum Number of Vowels in a Substring of Given Length", "Medium", "Sliding Window - Fixed Size", "https://leetcode.com/problems/maximum-number-of-vowels-in-a-substring-of-given-length/"),
    ("Maximum Sum of Distinct Subarrays With Length K", "Medium", "Sliding Window - Fixed Size", "https://leetcode.com/problems/maximum-sum-of-distinct-subarrays-with-length-k/"),
    ("Substring with Concatenation of All Words", "Hard", "Sliding Window - Fixed Size", "https://leetcode.com/problems/substring-with-concatenation-of-all-words/"),

    # ── Sliding Window - Dynamic Size ────────────────────────────────────────
    ("Longest Substring Without Repeating Characters", "Medium", "Sliding Window - Dynamic Size", "https://leetcode.com/problems/longest-substring-without-repeating-characters/"),
    ("Longest Repeating Character Replacement", "Medium", "Sliding Window - Dynamic Size", "https://leetcode.com/problems/longest-repeating-character-replacement/"),
    ("Minimum Size Subarray Sum", "Medium", "Sliding Window - Dynamic Size", "https://leetcode.com/problems/minimum-size-subarray-sum/"),
    ("Max Consecutive Ones III", "Medium", "Sliding Window - Dynamic Size", "https://leetcode.com/problems/max-consecutive-ones-iii/"),
    ("Count Number of Nice Subarrays", "Medium", "Sliding Window - Dynamic Size", "https://leetcode.com/problems/count-number-of-nice-subarrays/"),
    ("Fruit Into Baskets", "Medium", "Sliding Window - Dynamic Size", "https://leetcode.com/problems/fruit-into-baskets/"),
    ("Maximum Points You Can Obtain from Cards", "Medium", "Sliding Window - Dynamic Size", "https://leetcode.com/problems/maximum-points-you-can-obtain-from-cards/"),
    ("Subarray Product Less Than K", "Medium", "Sliding Window - Dynamic Size", "https://leetcode.com/problems/subarray-product-less-than-k/"),
    ("Frequency of the Most Frequent Element", "Medium", "Sliding Window - Dynamic Size", "https://leetcode.com/problems/frequency-of-the-most-frequent-element/"),
    ("Longest Substring with At Most Two Distinct Characters", "Medium", "Sliding Window - Dynamic Size", "https://leetcode.com/problems/longest-substring-with-at-most-two-distinct-characters/"),
    ("Longest Substring with At Most K Distinct Characters", "Medium", "Sliding Window - Dynamic Size", "https://leetcode.com/problems/longest-substring-with-at-most-k-distinct-characters/"),
    ("Longest Substring with At Least K Repeating Characters", "Medium", "Sliding Window - Dynamic Size", "https://leetcode.com/problems/longest-substring-with-at-least-k-repeating-characters/"),
    ("Minimum Window Substring", "Hard", "Sliding Window - Dynamic Size", "https://leetcode.com/problems/minimum-window-substring/"),
    ("Minimum Window Subsequence", "Hard", "Sliding Window - Dynamic Size", "https://leetcode.com/problems/minimum-window-subsequence/"),
    ("Subarrays with K Different Integers", "Hard", "Sliding Window - Dynamic Size", "https://leetcode.com/problems/subarrays-with-k-different-integers/"),

    # ── Kadane's Algorithm ───────────────────────────────────────────────────
    ("Maximum Subarray", "Medium", "Kadane's Algorithm", "https://leetcode.com/problems/maximum-subarray/"),
    ("Maximum Sum Circular Subarray", "Medium", "Kadane's Algorithm", "https://leetcode.com/problems/maximum-sum-circular-subarray/"),
    ("Maximum Subarray Sum with One Deletion", "Medium", "Kadane's Algorithm", "https://leetcode.com/problems/maximum-subarray-sum-with-one-deletion/"),
    ("Maximum Absolute Sum of Any Subarray", "Medium", "Kadane's Algorithm", "https://leetcode.com/problems/maximum-absolute-sum-of-any-subarray/"),
    ("Maximum Product Subarray", "Medium", "Kadane's Algorithm", "https://leetcode.com/problems/maximum-product-subarray/"),
    ("Longest Turbulent Subarray", "Medium", "Kadane's Algorithm", "https://leetcode.com/problems/longest-turbulent-subarray/"),
    ("Best Sightseeing Pair", "Medium", "Kadane's Algorithm", "https://leetcode.com/problems/best-sightseeing-pair/"),

    # ── Matrix (2D Array) ────────────────────────────────────────────────────
    ("Transpose Matrix", "Easy", "Matrix", "https://leetcode.com/problems/transpose-matrix/"),
    ("Spiral Matrix", "Medium", "Matrix", "https://leetcode.com/problems/spiral-matrix/"),
    ("Spiral Matrix II", "Medium", "Matrix", "https://leetcode.com/problems/spiral-matrix-ii/"),
    ("Diagonal Traverse", "Medium", "Matrix", "https://leetcode.com/problems/diagonal-traverse/"),
    ("Rotate Image", "Medium", "Matrix", "https://leetcode.com/problems/rotate-image/"),
    ("Set Matrix Zeroes", "Medium", "Matrix", "https://leetcode.com/problems/set-matrix-zeroes/"),
    ("Candy Crush", "Medium", "Matrix", "https://leetcode.com/problems/candy-crush/"),
    ("Valid Sudoku", "Medium", "Matrix", "https://leetcode.com/problems/valid-sudoku/"),
    ("Game of Life", "Medium", "Matrix", "https://leetcode.com/problems/game-of-life/"),

    # ── Linked List ──────────────────────────────────────────────────────────
    ("Intersection of Two Linked Lists", "Easy", "Linked List", "https://leetcode.com/problems/intersection-of-two-linked-lists/"),
    ("Remove Duplicates from Sorted List", "Easy", "Linked List", "https://leetcode.com/problems/remove-duplicates-from-sorted-list/"),
    ("Design Linked List", "Medium", "Linked List", "https://leetcode.com/problems/design-linked-list/"),
    ("Delete the Middle Node of a Linked List", "Medium", "Linked List", "https://leetcode.com/problems/delete-the-middle-node-of-a-linked-list/"),
    ("Remove Nth Node From End of List", "Medium", "Linked List", "https://leetcode.com/problems/remove-nth-node-from-end-of-list/"),
    ("Remove Duplicates from Sorted List II", "Medium", "Linked List", "https://leetcode.com/problems/remove-duplicates-from-sorted-list-ii/"),
    ("Odd Even Linked List", "Medium", "Linked List", "https://leetcode.com/problems/odd-even-linked-list/"),
    ("Swap Nodes in Pairs", "Medium", "Linked List", "https://leetcode.com/problems/swap-nodes-in-pairs/"),
    ("Copy List with Random Pointer", "Medium", "Linked List", "https://leetcode.com/problems/copy-list-with-random-pointer/"),
    ("Partition List", "Medium", "Linked List", "https://leetcode.com/problems/partition-list/"),
    ("Rotate List", "Medium", "Linked List", "https://leetcode.com/problems/rotate-list/"),
    ("Reorder List", "Medium", "Linked List", "https://leetcode.com/problems/reorder-list/"),
    ("Add Two Numbers", "Medium", "Linked List", "https://leetcode.com/problems/add-two-numbers/"),
    ("Add Two Numbers II", "Medium", "Linked List", "https://leetcode.com/problems/add-two-numbers-ii/"),
    ("Delete Node in a Linked List", "Medium", "Linked List", "https://leetcode.com/problems/delete-node-in-a-linked-list/"),
    ("Flatten a Multilevel Doubly Linked List", "Medium", "Linked List", "https://leetcode.com/problems/flatten-a-multilevel-doubly-linked-list/"),
    ("Insert into a Sorted Circular Linked List", "Medium", "Linked List", "https://leetcode.com/problems/insert-into-a-sorted-circular-linked-list/"),
    ("Merge In Between Linked Lists", "Medium", "Linked List", "https://leetcode.com/problems/merge-in-between-linked-lists/"),

    # ── LinkedList In-place Reversal ─────────────────────────────────────────
    ("Palindrome Linked List", "Easy", "LinkedList In-place Reversal", "https://leetcode.com/problems/palindrome-linked-list/"),
    ("Reverse Linked List", "Easy", "LinkedList In-place Reversal", "https://leetcode.com/problems/reverse-linked-list/"),
    ("Reverse Linked List II", "Medium", "LinkedList In-place Reversal", "https://leetcode.com/problems/reverse-linked-list-ii/"),
    ("Reverse Nodes in k-Group", "Hard", "LinkedList In-place Reversal", "https://leetcode.com/problems/reverse-nodes-in-k-group/"),

    # ── Fast and Slow Pointers ───────────────────────────────────────────────
    ("Middle of the Linked List", "Easy", "Fast and Slow Pointers", "https://leetcode.com/problems/middle-of-the-linked-list/"),
    ("Happy Number", "Easy", "Fast and Slow Pointers", "https://leetcode.com/problems/happy-number/"),
    ("Linked List Cycle II", "Medium", "Fast and Slow Pointers", "https://leetcode.com/problems/linked-list-cycle-ii/"),

    # ── Stacks ───────────────────────────────────────────────────────────────
    ("Valid Parentheses", "Easy", "Stacks", "https://leetcode.com/problems/valid-parentheses/"),
    ("Baseball Game", "Easy", "Stacks", "https://leetcode.com/problems/baseball-game/"),
    ("Remove All Adjacent Duplicates In String", "Easy", "Stacks", "https://leetcode.com/problems/remove-all-adjacent-duplicates-in-string/"),
    ("Maximum Nesting Depth of the Parentheses", "Easy", "Stacks", "https://leetcode.com/problems/maximum-nesting-depth-of-the-parentheses/"),
    ("Min Stack", "Medium", "Stacks", "https://leetcode.com/problems/min-stack/"),
    ("Asteroid Collision", "Medium", "Stacks", "https://leetcode.com/problems/asteroid-collision/"),
    ("Car Fleet", "Medium", "Stacks", "https://leetcode.com/problems/car-fleet/"),
    ("Valid Parenthesis String", "Medium", "Stacks", "https://leetcode.com/problems/valid-parenthesis-string/"),
    ("Validate Stack Sequences", "Medium", "Stacks", "https://leetcode.com/problems/validate-stack-sequences/"),
    ("Minimum Remove to Make Valid Parentheses", "Medium", "Stacks", "https://leetcode.com/problems/minimum-remove-to-make-valid-parentheses/"),
    ("Remove Duplicate Letters", "Medium", "Stacks", "https://leetcode.com/problems/remove-duplicate-letters/"),
    ("Removing Stars From a String", "Medium", "Stacks", "https://leetcode.com/problems/removing-stars-from-a-string/"),
    ("Simplify Path", "Medium", "Stacks", "https://leetcode.com/problems/simplify-path/"),
    ("Exclusive Time of Functions", "Medium", "Stacks", "https://leetcode.com/problems/exclusive-time-of-functions/"),
    ("Evaluate Reverse Polish Notation", "Medium", "Stacks", "https://leetcode.com/problems/evaluate-reverse-polish-notation/"),
    ("Basic Calculator II", "Medium", "Stacks", "https://leetcode.com/problems/basic-calculator-ii/"),
    ("Basic Calculator", "Hard", "Stacks", "https://leetcode.com/problems/basic-calculator/"),
    ("Longest Valid Parentheses", "Hard", "Stacks", "https://leetcode.com/problems/longest-valid-parentheses/"),

    # ── Monotonic Stack ──────────────────────────────────────────────────────
    ("Next Greater Element I", "Easy", "Monotonic Stack", "https://leetcode.com/problems/next-greater-element-i/"),
    ("Final Prices With a Special Discount in a Shop", "Easy", "Monotonic Stack", "https://leetcode.com/problems/final-prices-with-a-special-discount-in-a-shop/"),
    ("Next Greater Element II", "Medium", "Monotonic Stack", "https://leetcode.com/problems/next-greater-element-ii/"),
    ("Daily Temperatures", "Medium", "Monotonic Stack", "https://leetcode.com/problems/daily-temperatures/"),
    ("Online Stock Span", "Medium", "Monotonic Stack", "https://leetcode.com/problems/online-stock-span/"),
    ("Buildings With an Ocean View", "Medium", "Monotonic Stack", "https://leetcode.com/problems/buildings-with-an-ocean-view/"),
    ("132 Pattern", "Medium", "Monotonic Stack", "https://leetcode.com/problems/132-pattern/"),
    ("Remove K Digits", "Medium", "Monotonic Stack", "https://leetcode.com/problems/remove-k-digits/"),
    ("Maximum Width Ramp", "Medium", "Monotonic Stack", "https://leetcode.com/problems/maximum-width-ramp/"),
    ("Max Chunks To Make Sorted", "Medium", "Monotonic Stack", "https://leetcode.com/problems/max-chunks-to-make-sorted/"),
    ("Sum of Subarray Minimums", "Medium", "Monotonic Stack", "https://leetcode.com/problems/sum-of-subarray-minimums/"),
    ("Sum of Subarray Ranges", "Medium", "Monotonic Stack", "https://leetcode.com/problems/sum-of-subarray-ranges/"),
    ("Shortest Unsorted Continuous Subarray", "Medium", "Monotonic Stack", "https://leetcode.com/problems/shortest-unsorted-continuous-subarray/"),
    ("Next Greater Node In Linked List", "Medium", "Monotonic Stack", "https://leetcode.com/problems/next-greater-node-in-linked-list/"),
    ("Number of Visible People in a Queue", "Hard", "Monotonic Stack", "https://leetcode.com/problems/number-of-visible-people-in-a-queue/"),
    ("Largest Rectangle in Histogram", "Hard", "Monotonic Stack", "https://leetcode.com/problems/largest-rectangle-in-histogram/"),
    ("Create Maximum Number", "Hard", "Monotonic Stack", "https://leetcode.com/problems/create-maximum-number/"),

    # ── Queues ───────────────────────────────────────────────────────────────
    ("Number of Recent Calls", "Easy", "Queues", "https://leetcode.com/problems/number-of-recent-calls/"),
    ("Time Needed to Buy Tickets", "Easy", "Queues", "https://leetcode.com/problems/time-needed-to-buy-tickets/"),
    ("Moving Average from Data Stream", "Easy", "Queues", "https://leetcode.com/problems/moving-average-from-data-stream/"),
    ("Reveal Cards In Increasing Order", "Medium", "Queues", "https://leetcode.com/problems/reveal-cards-in-increasing-order/"),
    ("First Unique Number", "Medium", "Queues", "https://leetcode.com/problems/first-unique-number/"),
    ("Number of People Aware of a Secret", "Medium", "Queues", "https://leetcode.com/problems/number-of-people-aware-of-a-secret/"),
    ("Find the Winner of the Circular Game", "Medium", "Queues", "https://leetcode.com/problems/find-the-winner-of-the-circular-game/"),

    # ── Monotonic Queue ──────────────────────────────────────────────────────
    ("Jump Game VI", "Medium", "Monotonic Queue", "https://leetcode.com/problems/jump-game-vi/"),
    ("Continuous Subarrays", "Medium", "Monotonic Queue", "https://leetcode.com/problems/continuous-subarrays/"),
    ("Find the Most Competitive Subsequence", "Medium", "Monotonic Queue", "https://leetcode.com/problems/find-the-most-competitive-subsequence/"),
    ("Count Partitions With Max-Min Difference at Most K", "Medium", "Monotonic Queue", "https://leetcode.com/problems/count-partitions-with-even-sum-difference/"),
    ("Longest Continuous Subarray With Absolute Diff Less Than or Equal to Limit", "Medium", "Monotonic Queue", "https://leetcode.com/problems/longest-continuous-subarray-with-absolute-diff-less-than-or-equal-to-limit/"),
    ("Sliding Window Maximum", "Hard", "Monotonic Queue", "https://leetcode.com/problems/sliding-window-maximum/"),
    ("Max Value of Equation", "Hard", "Monotonic Queue", "https://leetcode.com/problems/max-value-of-equation/"),
    ("Constrained Subsequence Sum", "Hard", "Monotonic Queue", "https://leetcode.com/problems/constrained-subsequence-sum/"),
    ("Shortest Subarray with Sum at Least K", "Hard", "Monotonic Queue", "https://leetcode.com/problems/shortest-subarray-with-sum-at-least-k/"),

    # ── Bucket Sort ──────────────────────────────────────────────────────────
    ("Sort Characters By Frequency", "Medium", "Bucket Sort", "https://leetcode.com/problems/sort-characters-by-frequency/"),
    ("Top K Frequent Words", "Medium", "Bucket Sort", "https://leetcode.com/problems/top-k-frequent-words/"),
    ("Maximum Gap", "Medium", "Bucket Sort", "https://leetcode.com/problems/maximum-gap/"),
    ("Contains Duplicate III", "Hard", "Bucket Sort", "https://leetcode.com/problems/contains-duplicate-iii/"),

    # ── Recursion ────────────────────────────────────────────────────────────
    ("Merge Two Sorted Lists", "Easy", "Recursion", "https://leetcode.com/problems/merge-two-sorted-lists/"),
    ("Pow(x, n)", "Medium", "Recursion", "https://leetcode.com/problems/powx-n/"),
    ("Decode String", "Medium", "Recursion", "https://leetcode.com/problems/decode-string/"),
    ("Special Binary String", "Hard", "Recursion", "https://leetcode.com/problems/special-binary-string/"),
    ("Integer to English Words", "Hard", "Recursion", "https://leetcode.com/problems/integer-to-english-words/"),

    # ── Divide and Conquer ───────────────────────────────────────────────────
    ("Longest Nice Substring", "Easy", "Divide and Conquer", "https://leetcode.com/problems/longest-nice-substring/"),
    ("Convert Sorted List to Binary Search Tree", "Medium", "Divide and Conquer", "https://leetcode.com/problems/convert-sorted-list-to-binary-search-tree/"),
    ("Construct Quad Tree", "Medium", "Divide and Conquer", "https://leetcode.com/problems/construct-quad-tree/"),
    ("Maximum Binary Tree", "Medium", "Divide and Conquer", "https://leetcode.com/problems/maximum-binary-tree/"),

    # ── Merge Sort ───────────────────────────────────────────────────────────
    ("Sort an Array", "Medium", "Merge Sort", "https://leetcode.com/problems/sort-an-array/"),
    ("Sort List", "Medium", "Merge Sort", "https://leetcode.com/problems/sort-list/"),
    ("Reverse Pairs", "Hard", "Merge Sort", "https://leetcode.com/problems/reverse-pairs/"),
    ("Count of Range Sum", "Hard", "Merge Sort", "https://leetcode.com/problems/count-of-range-sum/"),

    # ── QuickSort / QuickSelect ──────────────────────────────────────────────
    ("Sort Colors", "Medium", "QuickSort/QuickSelect", "https://leetcode.com/problems/sort-colors/"),
    ("Kth Largest Element in an Array", "Medium", "QuickSort/QuickSelect", "https://leetcode.com/problems/kth-largest-element-in-an-array/"),
    ("Find the Kth Largest Integer in the Array", "Medium", "QuickSort/QuickSelect", "https://leetcode.com/problems/find-the-kth-largest-integer-in-the-array/"),

    # ── Binary Search ────────────────────────────────────────────────────────
    ("Binary Search", "Easy", "Binary Search", "https://leetcode.com/problems/binary-search/"),
    ("First Bad Version", "Easy", "Binary Search", "https://leetcode.com/problems/first-bad-version/"),
    ("Valid Perfect Square", "Easy", "Binary Search", "https://leetcode.com/problems/valid-perfect-square/"),
    ("Search Insert Position", "Easy", "Binary Search", "https://leetcode.com/problems/search-insert-position/"),
    ("Guess Number Higher or Lower", "Easy", "Binary Search", "https://leetcode.com/problems/guess-number-higher-or-lower/"),
    ("Find Smallest Letter Greater Than Target", "Easy", "Binary Search", "https://leetcode.com/problems/find-smallest-letter-greater-than-target/"),
    ("Find First and Last Position of Element in Sorted Array", "Medium", "Binary Search", "https://leetcode.com/problems/find-first-and-last-position-of-element-in-sorted-array/"),
    ("Search in Rotated Sorted Array", "Medium", "Binary Search", "https://leetcode.com/problems/search-in-rotated-sorted-array/"),
    ("Search in Rotated Sorted Array II", "Medium", "Binary Search", "https://leetcode.com/problems/search-in-rotated-sorted-array-ii/"),
    ("Find Peak Element", "Medium", "Binary Search", "https://leetcode.com/problems/find-peak-element/"),
    ("Random Pick with Weight", "Medium", "Binary Search", "https://leetcode.com/problems/random-pick-with-weight/"),
    ("Find K Closest Elements", "Medium", "Binary Search", "https://leetcode.com/problems/find-k-closest-elements/"),
    ("Heaters", "Medium", "Binary Search", "https://leetcode.com/problems/heaters/"),
    ("Koko Eating Bananas", "Medium", "Binary Search", "https://leetcode.com/problems/koko-eating-bananas/"),
    ("Capacity To Ship Packages Within D Days", "Medium", "Binary Search", "https://leetcode.com/problems/capacity-to-ship-packages-within-d-days/"),
    ("Minimum Number of Days to Make m Bouquets", "Medium", "Binary Search", "https://leetcode.com/problems/minimum-number-of-days-to-make-m-bouquets/"),
    ("Find Minimum in Rotated Sorted Array", "Medium", "Binary Search", "https://leetcode.com/problems/find-minimum-in-rotated-sorted-array/"),
    ("Search a 2D Matrix", "Medium", "Binary Search", "https://leetcode.com/problems/search-a-2d-matrix/"),
    ("Search a 2D Matrix II", "Medium", "Binary Search", "https://leetcode.com/problems/search-a-2d-matrix-ii/"),
    ("Magnetic Force Between Two Balls", "Medium", "Binary Search", "https://leetcode.com/problems/magnetic-force-between-two-balls/"),
    ("Find in Mountain Array", "Hard", "Binary Search", "https://leetcode.com/problems/find-in-mountain-array/"),
    ("Split Array Largest Sum", "Hard", "Binary Search", "https://leetcode.com/problems/split-array-largest-sum/"),
    ("Median of Two Sorted Arrays", "Hard", "Binary Search", "https://leetcode.com/problems/median-of-two-sorted-arrays/"),
    ("Find K-th Smallest Pair Distance", "Hard", "Binary Search", "https://leetcode.com/problems/find-k-th-smallest-pair-distance/"),

    # ── Backtracking ─────────────────────────────────────────────────────────
    ("Generate Parentheses", "Medium", "Backtracking", "https://leetcode.com/problems/generate-parentheses/"),
    ("Permutations", "Medium", "Backtracking", "https://leetcode.com/problems/permutations/"),
    ("Permutations II", "Medium", "Backtracking", "https://leetcode.com/problems/permutations-ii/"),
    ("Subsets", "Medium", "Backtracking", "https://leetcode.com/problems/subsets/"),
    ("Subsets II", "Medium", "Backtracking", "https://leetcode.com/problems/subsets-ii/"),
    ("Combination Sum", "Medium", "Backtracking", "https://leetcode.com/problems/combination-sum/"),
    ("Combination Sum II", "Medium", "Backtracking", "https://leetcode.com/problems/combination-sum-ii/"),
    ("Combination Sum III", "Medium", "Backtracking", "https://leetcode.com/problems/combination-sum-iii/"),
    ("Combinations", "Medium", "Backtracking", "https://leetcode.com/problems/combinations/"),
    ("Letter Combinations of a Phone Number", "Medium", "Backtracking", "https://leetcode.com/problems/letter-combinations-of-a-phone-number/"),
    ("Restore IP Addresses", "Medium", "Backtracking", "https://leetcode.com/problems/restore-ip-addresses/"),
    ("Palindrome Partitioning", "Medium", "Backtracking", "https://leetcode.com/problems/palindrome-partitioning/"),
    ("Unique Paths III", "Hard", "Backtracking", "https://leetcode.com/problems/unique-paths-iii/"),
    ("Remove Invalid Parentheses", "Hard", "Backtracking", "https://leetcode.com/problems/remove-invalid-parentheses/"),
    ("N-Queens", "Hard", "Backtracking", "https://leetcode.com/problems/n-queens/"),
    ("Sudoku Solver", "Hard", "Backtracking", "https://leetcode.com/problems/sudoku-solver/"),

    # ── Tree Traversal - Level Order ─────────────────────────────────────────
    ("Maximum Depth of Binary Tree", "Easy", "Tree Traversal - Level Order", "https://leetcode.com/problems/maximum-depth-of-binary-tree/"),
    ("Average of Levels in Binary Tree", "Easy", "Tree Traversal - Level Order", "https://leetcode.com/problems/average-of-levels-in-binary-tree/"),
    ("Binary Tree Level Order Traversal", "Medium", "Tree Traversal - Level Order", "https://leetcode.com/problems/binary-tree-level-order-traversal/"),
    ("Binary Tree Right Side View", "Medium", "Tree Traversal - Level Order", "https://leetcode.com/problems/binary-tree-right-side-view/"),
    ("Binary Tree Zigzag Level Order Traversal", "Medium", "Tree Traversal - Level Order", "https://leetcode.com/problems/binary-tree-zigzag-level-order-traversal/"),
    ("Binary Tree Vertical Order Traversal", "Medium", "Tree Traversal - Level Order", "https://leetcode.com/problems/binary-tree-vertical-order-traversal/"),
    ("Populating Next Right Pointers in Each Node", "Medium", "Tree Traversal - Level Order", "https://leetcode.com/problems/populating-next-right-pointers-in-each-node/"),
    ("Populating Next Right Pointers in Each Node II", "Medium", "Tree Traversal - Level Order", "https://leetcode.com/problems/populating-next-right-pointers-in-each-node-ii/"),
    ("Maximum Width of Binary Tree", "Medium", "Tree Traversal - Level Order", "https://leetcode.com/problems/maximum-width-of-binary-tree/"),
    ("Check Completeness of a Binary Tree", "Medium", "Tree Traversal - Level Order", "https://leetcode.com/problems/check-completeness-of-a-binary-tree/"),

    # ── Tree Traversal - Pre Order ───────────────────────────────────────────
    ("Binary Tree Preorder Traversal", "Easy", "Tree Traversal - Pre Order", "https://leetcode.com/problems/binary-tree-preorder-traversal/"),
    ("Same Tree", "Easy", "Tree Traversal - Pre Order", "https://leetcode.com/problems/same-tree/"),
    ("Symmetric Tree", "Easy", "Tree Traversal - Pre Order", "https://leetcode.com/problems/symmetric-tree/"),
    ("Sum of Left Leaves", "Easy", "Tree Traversal - Pre Order", "https://leetcode.com/problems/sum-of-left-leaves/"),
    ("Subtree of Another Tree", "Easy", "Tree Traversal - Pre Order", "https://leetcode.com/problems/subtree-of-another-tree/"),
    ("Binary Tree Paths", "Easy", "Tree Traversal - Pre Order", "https://leetcode.com/problems/binary-tree-paths/"),
    ("Convert Sorted Array to Binary Search Tree", "Easy", "Tree Traversal - Pre Order", "https://leetcode.com/problems/convert-sorted-array-to-binary-search-tree/"),
    ("Count Complete Tree Nodes", "Easy", "Tree Traversal - Pre Order", "https://leetcode.com/problems/count-complete-tree-nodes/"),
    ("Path Sum II", "Medium", "Tree Traversal - Pre Order", "https://leetcode.com/problems/path-sum-ii/"),
    ("Path Sum III", "Medium", "Tree Traversal - Pre Order", "https://leetcode.com/problems/path-sum-iii/"),
    ("Longest Univalue Path", "Medium", "Tree Traversal - Pre Order", "https://leetcode.com/problems/longest-univalue-path/"),
    ("Maximum Difference Between Node and Ancestor", "Medium", "Tree Traversal - Pre Order", "https://leetcode.com/problems/maximum-difference-between-node-and-ancestor/"),
    ("Construct Binary Tree from Preorder and Inorder Traversal", "Medium", "Tree Traversal - Pre Order", "https://leetcode.com/problems/construct-binary-tree-from-preorder-and-inorder-traversal/"),
    ("Construct Binary Tree from Inorder and Postorder Traversal", "Medium", "Tree Traversal - Pre Order", "https://leetcode.com/problems/construct-binary-tree-from-inorder-and-postorder-traversal/"),
    ("Serialize and Deserialize Binary Tree", "Hard", "Tree Traversal - Pre Order", "https://leetcode.com/problems/serialize-and-deserialize-binary-tree/"),

    # ── Tree Traversal - In Order ────────────────────────────────────────────
    ("Binary Tree Inorder Traversal", "Easy", "Tree Traversal - In Order", "https://leetcode.com/problems/binary-tree-inorder-traversal/"),
    ("Minimum Distance Between BST Nodes", "Easy", "Tree Traversal - In Order", "https://leetcode.com/problems/minimum-distance-between-bst-nodes/"),
    ("Minimum Absolute Difference in BST", "Easy", "Tree Traversal - In Order", "https://leetcode.com/problems/minimum-absolute-difference-in-bst/"),
    ("Validate Binary Search Tree", "Medium", "Tree Traversal - In Order", "https://leetcode.com/problems/validate-binary-search-tree/"),
    ("Kth Smallest Element in a BST", "Medium", "Tree Traversal - In Order", "https://leetcode.com/problems/kth-smallest-element-in-a-bst/"),
    ("Binary Search Tree Iterator", "Medium", "Tree Traversal - In Order", "https://leetcode.com/problems/binary-search-tree-iterator/"),
    ("Balance a Binary Search Tree", "Medium", "Tree Traversal - In Order", "https://leetcode.com/problems/balance-a-binary-search-tree/"),

    # ── Tree Traversal - Post-Order ──────────────────────────────────────────
    ("Binary Tree Postorder Traversal", "Easy", "Tree Traversal - Post-Order", "https://leetcode.com/problems/binary-tree-postorder-traversal/"),
    ("Invert Binary Tree", "Easy", "Tree Traversal - Post-Order", "https://leetcode.com/problems/invert-binary-tree/"),
    ("Balanced Binary Tree", "Easy", "Tree Traversal - Post-Order", "https://leetcode.com/problems/balanced-binary-tree/"),
    ("Diameter of Binary Tree", "Easy", "Tree Traversal - Post-Order", "https://leetcode.com/problems/diameter-of-binary-tree/"),
    ("Count Good Nodes in Binary Tree", "Medium", "Tree Traversal - Post-Order", "https://leetcode.com/problems/count-good-nodes-in-binary-tree/"),
    ("Sum Root to Leaf Numbers", "Medium", "Tree Traversal - Post-Order", "https://leetcode.com/problems/sum-root-to-leaf-numbers/"),
    ("Delete Nodes And Return Forest", "Medium", "Tree Traversal - Post-Order", "https://leetcode.com/problems/delete-nodes-and-return-forest/"),
    ("Lowest Common Ancestor of a Binary Tree", "Medium", "Tree Traversal - Post-Order", "https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-tree/"),
    ("Find Duplicate Subtrees", "Medium", "Tree Traversal - Post-Order", "https://leetcode.com/problems/find-duplicate-subtrees/"),
    ("Flatten Binary Tree to Linked List", "Medium", "Tree Traversal - Post-Order", "https://leetcode.com/problems/flatten-binary-tree-to-linked-list/"),
    ("Distribute Coins in Binary Tree", "Medium", "Tree Traversal - Post-Order", "https://leetcode.com/problems/distribute-coins-in-binary-tree/"),
    ("Boundary of Binary Tree", "Medium", "Tree Traversal - Post-Order", "https://leetcode.com/problems/boundary-of-binary-tree/"),
    ("Step-By-Step Directions From a Binary Tree Node to Another", "Medium", "Tree Traversal - Post-Order", "https://leetcode.com/problems/step-by-step-directions-from-a-binary-tree-node-to-another/"),
    ("Binary Tree Maximum Path Sum", "Hard", "Tree Traversal - Post-Order", "https://leetcode.com/problems/binary-tree-maximum-path-sum/"),

    # ── BST / Ordered Set ────────────────────────────────────────────────────
    ("Search in a Binary Search Tree", "Easy", "BST/Ordered Set", "https://leetcode.com/problems/search-in-a-binary-search-tree/"),
    ("Closest Binary Search Tree Value", "Easy", "BST/Ordered Set", "https://leetcode.com/problems/closest-binary-search-tree-value/"),
    ("Two Sum IV - Input is a BST", "Easy", "BST/Ordered Set", "https://leetcode.com/problems/two-sum-iv-input-is-a-bst/"),
    ("Range Sum of BST", "Easy", "BST/Ordered Set", "https://leetcode.com/problems/range-sum-of-bst/"),
    ("Inorder Successor in BST", "Medium", "BST/Ordered Set", "https://leetcode.com/problems/inorder-successor-in-bst/"),
    ("Inorder Successor in BST II", "Medium", "BST/Ordered Set", "https://leetcode.com/problems/inorder-successor-in-bst-ii/"),
    ("Insert into a Binary Search Tree", "Medium", "BST/Ordered Set", "https://leetcode.com/problems/insert-into-a-binary-search-tree/"),
    ("Delete Node in a BST", "Medium", "BST/Ordered Set", "https://leetcode.com/problems/delete-node-in-a-bst/"),
    ("Trim a Binary Search Tree", "Medium", "BST/Ordered Set", "https://leetcode.com/problems/trim-a-binary-search-tree/"),
    ("Lowest Common Ancestor of a Binary Search Tree", "Medium", "BST/Ordered Set", "https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-search-tree/"),
    ("Largest BST Subtree", "Medium", "BST/Ordered Set", "https://leetcode.com/problems/largest-bst-subtree/"),
    ("Recover Binary Search Tree", "Medium", "BST/Ordered Set", "https://leetcode.com/problems/recover-binary-search-tree/"),
    ("Convert Binary Search Tree to Sorted Doubly Linked List", "Medium", "BST/Ordered Set", "https://leetcode.com/problems/convert-binary-search-tree-to-sorted-doubly-linked-list/"),
    ("Construct Binary Search Tree from Preorder Traversal", "Medium", "BST/Ordered Set", "https://leetcode.com/problems/construct-binary-search-tree-from-preorder-traversal/"),
    ("My Calendar I", "Medium", "BST/Ordered Set", "https://leetcode.com/problems/my-calendar-i/"),
    ("My Calendar II", "Medium", "BST/Ordered Set", "https://leetcode.com/problems/my-calendar-ii/"),
    ("Stock Price Fluctuation", "Medium", "BST/Ordered Set", "https://leetcode.com/problems/stock-price-fluctuation/"),

    # ── Tries ────────────────────────────────────────────────────────────────
    ("Implement Trie (Prefix Tree)", "Medium", "Tries", "https://leetcode.com/problems/implement-trie-prefix-tree/"),
    ("Design Add and Search Words Data Structure", "Medium", "Tries", "https://leetcode.com/problems/design-add-and-search-words-data-structure/"),
    ("Search Suggestions System", "Medium", "Tries", "https://leetcode.com/problems/search-suggestions-system/"),
    ("Longest Word in Dictionary", "Medium", "Tries", "https://leetcode.com/problems/longest-word-in-dictionary/"),
    ("Replace Words", "Medium", "Tries", "https://leetcode.com/problems/replace-words/"),
    ("Maximum XOR of Two Numbers in an Array", "Medium", "Tries", "https://leetcode.com/problems/maximum-xor-of-two-numbers-in-an-array/"),
    ("Remove Sub-Folders from the Filesystem", "Medium", "Tries", "https://leetcode.com/problems/remove-sub-folders-from-the-filesystem/"),
    ("Find the Length of the Longest Common Prefix", "Medium", "Tries", "https://leetcode.com/problems/find-the-length-of-the-longest-common-prefix/"),
    ("Words Within Two Edits of Dictionary", "Medium", "Tries", "https://leetcode.com/problems/words-within-two-edits-of-dictionary/"),
    ("Word Search II", "Hard", "Tries", "https://leetcode.com/problems/word-search-ii/"),
    ("Stream of Characters", "Hard", "Tries", "https://leetcode.com/problems/stream-of-characters/"),
    ("Concatenated Words", "Hard", "Tries", "https://leetcode.com/problems/concatenated-words/"),
    ("Word Squares", "Hard", "Tries", "https://leetcode.com/problems/word-squares/"),
    ("Palindrome Pairs", "Hard", "Tries", "https://leetcode.com/problems/palindrome-pairs/"),

    # ── Heaps ────────────────────────────────────────────────────────────────
    ("Last Stone Weight", "Easy", "Heaps", "https://leetcode.com/problems/last-stone-weight/"),
    ("Minimum Cost to Connect Sticks", "Medium", "Heaps", "https://leetcode.com/problems/minimum-cost-to-connect-sticks/"),
    ("Furthest Building You Can Reach", "Medium", "Heaps", "https://leetcode.com/problems/furthest-building-you-can-reach/"),
    ("Single-Threaded CPU", "Medium", "Heaps", "https://leetcode.com/problems/single-threaded-cpu/"),
    ("Process Tasks Using Servers", "Medium", "Heaps", "https://leetcode.com/problems/process-tasks-using-servers/"),
    ("Longest Happy String", "Medium", "Heaps", "https://leetcode.com/problems/longest-happy-string/"),
    ("Maximum Performance of a Team", "Hard", "Heaps", "https://leetcode.com/problems/maximum-performance-of-a-team/"),

    # ── Two Heaps ────────────────────────────────────────────────────────────
    ("Find Median from Data Stream", "Hard", "Two Heaps", "https://leetcode.com/problems/find-median-from-data-stream/"),
    ("IPO", "Hard", "Two Heaps", "https://leetcode.com/problems/ipo/"),
    ("Sliding Window Median", "Hard", "Two Heaps", "https://leetcode.com/problems/sliding-window-median/"),

    # ── Top K Elements ───────────────────────────────────────────────────────
    ("Kth Largest Element in a Stream", "Easy", "Top K Elements", "https://leetcode.com/problems/kth-largest-element-in-a-stream/"),
    ("Top K Frequent Elements", "Medium", "Top K Elements", "https://leetcode.com/problems/top-k-frequent-elements/"),
    ("K Closest Points to Origin", "Medium", "Top K Elements", "https://leetcode.com/problems/k-closest-points-to-origin/"),

    # ── Intervals ────────────────────────────────────────────────────────────
    ("Summary Ranges", "Easy", "Intervals", "https://leetcode.com/problems/summary-ranges/"),
    ("Meeting Rooms", "Easy", "Intervals", "https://leetcode.com/problems/meeting-rooms/"),
    ("Meeting Rooms II", "Medium", "Intervals", "https://leetcode.com/problems/meeting-rooms-ii/"),
    ("Meeting Scheduler", "Medium", "Intervals", "https://leetcode.com/problems/meeting-scheduler/"),
    ("Interval List Intersections", "Medium", "Intervals", "https://leetcode.com/problems/interval-list-intersections/"),
    ("Car Pooling", "Medium", "Intervals", "https://leetcode.com/problems/car-pooling/"),
    ("Merge Intervals", "Medium", "Intervals", "https://leetcode.com/problems/merge-intervals/"),
    ("Insert Interval", "Medium", "Intervals", "https://leetcode.com/problems/insert-interval/"),
    ("Remove Covered Intervals", "Medium", "Intervals", "https://leetcode.com/problems/remove-covered-intervals/"),
    ("Partition Labels", "Medium", "Intervals", "https://leetcode.com/problems/partition-labels/"),
    ("Minimum Number of Arrows to Burst Balloons", "Medium", "Intervals", "https://leetcode.com/problems/minimum-number-of-arrows-to-burst-balloons/"),
    ("Maximum Number of Events That Can Be Attended", "Medium", "Intervals", "https://leetcode.com/problems/maximum-number-of-events-that-can-be-attended/"),
    ("Non-overlapping Intervals", "Medium", "Intervals", "https://leetcode.com/problems/non-overlapping-intervals/"),
    ("Two Best Non-Overlapping Events", "Medium", "Intervals", "https://leetcode.com/problems/two-best-non-overlapping-events/"),
    ("Meeting Rooms III", "Hard", "Intervals", "https://leetcode.com/problems/meeting-rooms-iii/"),

    # ── K-Way Merge ──────────────────────────────────────────────────────────
    ("Find K Pairs with Smallest Sums", "Medium", "K-Way Merge", "https://leetcode.com/problems/find-k-pairs-with-smallest-sums/"),
    ("Kth Smallest Element in a Sorted Matrix", "Medium", "K-Way Merge", "https://leetcode.com/problems/kth-smallest-element-in-a-sorted-matrix/"),
    ("Merge k Sorted Lists", "Hard", "K-Way Merge", "https://leetcode.com/problems/merge-k-sorted-lists/"),
    ("Smallest Range Covering Elements from K Lists", "Hard", "K-Way Merge", "https://leetcode.com/problems/smallest-range-covering-elements-from-k-lists/"),

    # ── Data Structure Design ────────────────────────────────────────────────
    ("Logger Rate Limiter", "Easy", "Data Structure Design", "https://leetcode.com/problems/logger-rate-limiter/"),
    ("Implement Queue using Stacks", "Easy", "Data Structure Design", "https://leetcode.com/problems/implement-queue-using-stacks/"),
    ("Implement Stack using Queues", "Easy", "Data Structure Design", "https://leetcode.com/problems/implement-stack-using-queues/"),
    ("Design Circular Queue", "Medium", "Data Structure Design", "https://leetcode.com/problems/design-circular-queue/"),
    ("Design Circular Deque", "Medium", "Data Structure Design", "https://leetcode.com/problems/design-circular-deque/"),
    ("Design Hit Counter", "Medium", "Data Structure Design", "https://leetcode.com/problems/design-hit-counter/"),
    ("Design Browser History", "Medium", "Data Structure Design", "https://leetcode.com/problems/design-browser-history/"),
    ("Time Based Key-Value Store", "Medium", "Data Structure Design", "https://leetcode.com/problems/time-based-key-value-store/"),
    ("Encode and Decode Strings", "Medium", "Data Structure Design", "https://leetcode.com/problems/encode-and-decode-strings/"),
    ("Snapshot Array", "Medium", "Data Structure Design", "https://leetcode.com/problems/snapshot-array/"),
    ("Design Twitter", "Medium", "Data Structure Design", "https://leetcode.com/problems/design-twitter/"),
    ("LRU Cache", "Medium", "Data Structure Design", "https://leetcode.com/problems/lru-cache/"),
    ("Insert Delete GetRandom O(1)", "Medium", "Data Structure Design", "https://leetcode.com/problems/insert-delete-getrandom-o1/"),
    ("Design a Food Rating System", "Medium", "Data Structure Design", "https://leetcode.com/problems/design-a-food-rating-system/"),
    ("LFU Cache", "Hard", "Data Structure Design", "https://leetcode.com/problems/lfu-cache/"),
    ("Max Stack", "Hard", "Data Structure Design", "https://leetcode.com/problems/max-stack/"),
    ("Maximum Frequency Stack", "Hard", "Data Structure Design", "https://leetcode.com/problems/maximum-frequency-stack/"),
    ("All O`one Data Structure", "Hard", "Data Structure Design", "https://leetcode.com/problems/all-oone-data-structure/"),
    ("Range Module", "Hard", "Data Structure Design", "https://leetcode.com/problems/range-module/"),
    ("Design Search Autocomplete System", "Hard", "Data Structure Design", "https://leetcode.com/problems/design-search-autocomplete-system/"),
    ("Design In-Memory File System", "Hard", "Data Structure Design", "https://leetcode.com/problems/design-in-memory-file-system/"),
    ("Design a Text Editor", "Hard", "Data Structure Design", "https://leetcode.com/problems/design-a-text-editor/"),

    # ── Greedy ───────────────────────────────────────────────────────────────
    ("Assign Cookies", "Easy", "Greedy", "https://leetcode.com/problems/assign-cookies/"),
    ("Apple Redistribution into Boxes", "Easy", "Greedy", "https://leetcode.com/problems/apple-redistribution-into-boxes/"),
    ("Jump Game", "Medium", "Greedy", "https://leetcode.com/problems/jump-game/"),
    ("Jump Game II", "Medium", "Greedy", "https://leetcode.com/problems/jump-game-ii/"),
    ("Jump Game VII", "Medium", "Greedy", "https://leetcode.com/problems/jump-game-vii/"),
    ("Minimum Add to Make Parentheses Valid", "Medium", "Greedy", "https://leetcode.com/problems/minimum-add-to-make-parentheses-valid/"),
    ("Gas Station", "Medium", "Greedy", "https://leetcode.com/problems/gas-station/"),
    ("Task Scheduler", "Medium", "Greedy", "https://leetcode.com/problems/task-scheduler/"),
    ("Maximum Swap", "Medium", "Greedy", "https://leetcode.com/problems/maximum-swap/"),
    ("Queue Reconstruction by Height", "Medium", "Greedy", "https://leetcode.com/problems/queue-reconstruction-by-height/"),
    ("Maximum Score From Removing Substrings", "Medium", "Greedy", "https://leetcode.com/problems/maximum-score-from-removing-substrings/"),
    ("Avoid Flood in The City", "Medium", "Greedy", "https://leetcode.com/problems/avoid-flood-in-the-city/"),
    ("Maximum Matrix Sum", "Medium", "Greedy", "https://leetcode.com/problems/maximum-matrix-sum/"),
    ("Most Profit Assigning Work", "Medium", "Greedy", "https://leetcode.com/problems/most-profit-assigning-work/"),
    ("Minimum Cost to Hire K Workers", "Hard", "Greedy", "https://leetcode.com/problems/minimum-cost-to-hire-k-workers/"),
    ("Candy", "Hard", "Greedy", "https://leetcode.com/problems/candy/"),
    ("Minimum Number of Refueling Stops", "Hard", "Greedy", "https://leetcode.com/problems/minimum-number-of-refueling-stops/"),
    ("Set Intersection Size At Least Two", "Hard", "Greedy", "https://leetcode.com/problems/set-intersection-size-at-least-two/"),

    # ── Depth First Search (DFS) ─────────────────────────────────────────────
    ("Flood Fill", "Easy", "DFS", "https://leetcode.com/problems/flood-fill/"),
    ("Number of Islands", "Medium", "DFS", "https://leetcode.com/problems/number-of-islands/"),
    ("Number of Distinct Islands", "Medium", "DFS", "https://leetcode.com/problems/number-of-distinct-islands/"),
    ("Word Search", "Medium", "DFS", "https://leetcode.com/problems/word-search/"),
    ("Time Needed to Inform All Employees", "Medium", "DFS", "https://leetcode.com/problems/time-needed-to-inform-all-employees/"),
    ("All Paths From Source to Target", "Medium", "DFS", "https://leetcode.com/problems/all-paths-from-source-to-target/"),
    ("Clone Graph", "Medium", "DFS", "https://leetcode.com/problems/clone-graph/"),
    ("Is Graph Bipartite?", "Medium", "DFS", "https://leetcode.com/problems/is-graph-bipartite/"),
    ("All Nodes Distance K in Binary Tree", "Medium", "DFS", "https://leetcode.com/problems/all-nodes-distance-k-in-binary-tree/"),
    ("Employee Importance", "Medium", "DFS", "https://leetcode.com/problems/employee-importance/"),
    ("Surrounded Regions", "Medium", "DFS", "https://leetcode.com/problems/surrounded-regions/"),
    ("Pacific Atlantic Water Flow", "Medium", "DFS", "https://leetcode.com/problems/pacific-atlantic-water-flow/"),
    ("Number of Enclaves", "Medium", "DFS", "https://leetcode.com/problems/number-of-enclaves/"),
    ("Making A Large Island", "Hard", "DFS", "https://leetcode.com/problems/making-a-large-island/"),
    ("Critical Connections in a Network", "Hard", "DFS", "https://leetcode.com/problems/critical-connections-in-a-network/"),
    ("Longest Path With Different Adjacent Characters", "Hard", "DFS", "https://leetcode.com/problems/longest-path-with-different-adjacent-characters/"),

    # ── Breadth First Search (BFS) ───────────────────────────────────────────
    ("Rotting Oranges", "Medium", "BFS", "https://leetcode.com/problems/rotting-oranges/"),
    ("01 Matrix", "Medium", "BFS", "https://leetcode.com/problems/01-matrix/"),
    ("Open the Lock", "Medium", "BFS", "https://leetcode.com/problems/open-the-lock/"),
    ("Snakes and Ladders", "Medium", "BFS", "https://leetcode.com/problems/snakes-and-ladders/"),
    ("Minimum Genetic Mutation", "Medium", "BFS", "https://leetcode.com/problems/minimum-genetic-mutation/"),
    ("Walls and Gates", "Medium", "BFS", "https://leetcode.com/problems/walls-and-gates/"),
    ("Minimum Knight Moves", "Medium", "BFS", "https://leetcode.com/problems/minimum-knight-moves/"),
    ("Shortest Path in Binary Matrix", "Medium", "BFS", "https://leetcode.com/problems/shortest-path-in-binary-matrix/"),
    ("Path With Maximum Minimum Value", "Medium", "BFS", "https://leetcode.com/problems/path-with-maximum-minimum-value/"),
    ("Shortest Path in a Grid with Obstacles Elimination", "Hard", "BFS", "https://leetcode.com/problems/shortest-path-in-a-grid-with-obstacles-elimination/"),
    ("Bus Routes", "Hard", "BFS", "https://leetcode.com/problems/bus-routes/"),
    ("Word Ladder", "Hard", "BFS", "https://leetcode.com/problems/word-ladder/"),
    ("Minimum Obstacle Removal to Reach Corner", "Hard", "BFS", "https://leetcode.com/problems/minimum-obstacle-removal-to-reach-corner/"),

    # ── Topological Sort ─────────────────────────────────────────────────────
    ("Course Schedule II", "Medium", "Topological Sort", "https://leetcode.com/problems/course-schedule-ii/"),
    ("Course Schedule IV", "Medium", "Topological Sort", "https://leetcode.com/problems/course-schedule-iv/"),
    ("Parallel Courses", "Medium", "Topological Sort", "https://leetcode.com/problems/parallel-courses/"),
    ("Find Eventual Safe States", "Medium", "Topological Sort", "https://leetcode.com/problems/find-eventual-safe-states/"),
    ("Minimum Height Trees", "Medium", "Topological Sort", "https://leetcode.com/problems/minimum-height-trees/"),
    ("Find All Possible Recipes from Given Supplies", "Medium", "Topological Sort", "https://leetcode.com/problems/find-all-possible-recipes-from-given-supplies/"),
    ("Sort Items by Groups Respecting Dependencies", "Hard", "Topological Sort", "https://leetcode.com/problems/sort-items-by-groups-respecting-dependencies/"),
    ("Alien Dictionary", "Hard", "Topological Sort", "https://leetcode.com/problems/alien-dictionary/"),

    # ── Union Find ───────────────────────────────────────────────────────────
    ("Number of Connected Components in an Undirected Graph", "Medium", "Union Find", "https://leetcode.com/problems/number-of-connected-components-in-an-undirected-graph/"),
    ("Number of Provinces", "Medium", "Union Find", "https://leetcode.com/problems/number-of-provinces/"),
    ("Redundant Connection", "Medium", "Union Find", "https://leetcode.com/problems/redundant-connection/"),
    ("Graph Valid Tree", "Medium", "Union Find", "https://leetcode.com/problems/graph-valid-tree/"),
    ("Accounts Merge", "Medium", "Union Find", "https://leetcode.com/problems/accounts-merge/"),
    ("Evaluate Division", "Medium", "Union Find", "https://leetcode.com/problems/evaluate-division/"),
    ("Most Stones Removed with Same Row or Column", "Medium", "Union Find", "https://leetcode.com/problems/most-stones-removed-with-same-row-or-column/"),
    ("Minimize Malware Spread", "Hard", "Union Find", "https://leetcode.com/problems/minimize-malware-spread/"),
    ("Number of Islands II", "Hard", "Union Find", "https://leetcode.com/problems/number-of-islands-ii/"),

    # ── Minimum Spanning Tree ────────────────────────────────────────────────
    ("Min Cost to Connect All Points", "Medium", "Minimum Spanning Tree", "https://leetcode.com/problems/min-cost-to-connect-all-points/"),
    ("Connecting Cities With Minimum Cost", "Medium", "Minimum Spanning Tree", "https://leetcode.com/problems/connecting-cities-with-minimum-cost/"),
    ("Optimize Water Distribution in a Village", "Hard", "Minimum Spanning Tree", "https://leetcode.com/problems/optimize-water-distribution-in-a-village/"),
    ("Find Critical and Pseudo-Critical Edges in Minimum Spanning Tree", "Hard", "Minimum Spanning Tree", "https://leetcode.com/problems/find-critical-and-pseudo-critical-edges-in-minimum-spanning-tree/"),
    ("Maximize Spanning Tree Stability with Upgrades", "Hard", "Minimum Spanning Tree", "https://leetcode.com/problems/maximum-edge-removal-in-forest-to-make-uniformly-colored/"),

    # ── Shortest Path ────────────────────────────────────────────────────────
    ("Network Delay Time", "Medium", "Shortest Path", "https://leetcode.com/problems/network-delay-time/"),
    ("Cheapest Flights Within K Stops", "Medium", "Shortest Path", "https://leetcode.com/problems/cheapest-flights-within-k-stops/"),
    ("Path with Maximum Probability", "Medium", "Shortest Path", "https://leetcode.com/problems/path-with-maximum-probability/"),
    ("Path With Minimum Effort", "Medium", "Shortest Path", "https://leetcode.com/problems/path-with-minimum-effort/"),
    ("The Maze II", "Medium", "Shortest Path", "https://leetcode.com/problems/the-maze-ii/"),
    ("Minimum Cost to Convert String I", "Medium", "Shortest Path", "https://leetcode.com/problems/minimum-cost-to-convert-string-i/"),
    ("Minimum Edge Reversals So Every Node Is Reachable", "Hard", "Shortest Path", "https://leetcode.com/problems/minimum-edge-reversals-so-every-node-is-reachable/"),
    ("Find Minimum Time to Reach Last Room I", "Medium", "Shortest Path", "https://leetcode.com/problems/find-minimum-time-to-reach-last-room-i/"),
    ("Swim in Rising Water", "Hard", "Shortest Path", "https://leetcode.com/problems/swim-in-rising-water/"),
    ("Minimum Cost to Make at Least One Valid Path in a Grid", "Hard", "Shortest Path", "https://leetcode.com/problems/minimum-cost-to-make-at-least-one-valid-path-in-a-grid/"),
    ("Minimum Weighted Subgraph With the Required Paths", "Hard", "Shortest Path", "https://leetcode.com/problems/minimum-weighted-subgraph-with-the-required-paths/"),

    # ── Eulerian Circuit ─────────────────────────────────────────────────────
    ("Reconstruct Itinerary", "Hard", "Eulerian Circuit", "https://leetcode.com/problems/reconstruct-itinerary/"),
    ("Cracking the Safe", "Hard", "Eulerian Circuit", "https://leetcode.com/problems/cracking-the-safe/"),
    ("Valid Arrangement of Pairs", "Hard", "Eulerian Circuit", "https://leetcode.com/problems/valid-arrangement-of-pairs/"),

    # ── 1-D DP ───────────────────────────────────────────────────────────────
    ("Fibonacci Number", "Easy", "1-D DP", "https://leetcode.com/problems/fibonacci-number/"),
    ("Climbing Stairs", "Easy", "1-D DP", "https://leetcode.com/problems/climbing-stairs/"),
    ("Min Cost Climbing Stairs", "Easy", "1-D DP", "https://leetcode.com/problems/min-cost-climbing-stairs/"),
    ("House Robber", "Medium", "1-D DP", "https://leetcode.com/problems/house-robber/"),
    ("House Robber II", "Medium", "1-D DP", "https://leetcode.com/problems/house-robber-ii/"),
    ("Maximum Length of Pair Chain", "Medium", "1-D DP", "https://leetcode.com/problems/maximum-length-of-pair-chain/"),
    ("Delete and Earn", "Medium", "1-D DP", "https://leetcode.com/problems/delete-and-earn/"),
    ("Integer Break", "Medium", "1-D DP", "https://leetcode.com/problems/integer-break/"),
    ("Greatest Sum Divisible by Three", "Medium", "1-D DP", "https://leetcode.com/problems/greatest-sum-divisible-by-three/"),
    ("Number of Ways to Paint N x 3 Grid", "Hard", "1-D DP", "https://leetcode.com/problems/number-of-ways-to-paint-n-3-grid/"),

    # ── 0/1 Knapsack ─────────────────────────────────────────────────────────
    ("Partition Equal Subset Sum", "Medium", "0/1 Knapsack", "https://leetcode.com/problems/partition-equal-subset-sum/"),
    ("Target Sum", "Medium", "0/1 Knapsack", "https://leetcode.com/problems/target-sum/"),
    ("Last Stone Weight II", "Medium", "0/1 Knapsack", "https://leetcode.com/problems/last-stone-weight-ii/"),
    ("Ones and Zeroes", "Medium", "0/1 Knapsack", "https://leetcode.com/problems/ones-and-zeroes/"),
    ("Profitable Schemes", "Hard", "0/1 Knapsack", "https://leetcode.com/problems/profitable-schemes/"),

    # ── Unbounded Knapsack ───────────────────────────────────────────────────
    ("Coin Change", "Medium", "Unbounded Knapsack", "https://leetcode.com/problems/coin-change/"),
    ("Coin Change II", "Medium", "Unbounded Knapsack", "https://leetcode.com/problems/coin-change-2/"),
    ("Perfect Squares", "Medium", "Unbounded Knapsack", "https://leetcode.com/problems/perfect-squares/"),
    ("Minimum Cost For Tickets", "Medium", "Unbounded Knapsack", "https://leetcode.com/problems/minimum-cost-for-tickets/"),

    # ── Longest Increasing Subsequence (LIS) ─────────────────────────────────
    ("Longest Increasing Subsequence", "Medium", "Longest Increasing Subsequence (LIS)", "https://leetcode.com/problems/longest-increasing-subsequence/"),
    ("Number of Longest Increasing Subsequence", "Medium", "Longest Increasing Subsequence (LIS)", "https://leetcode.com/problems/number-of-longest-increasing-subsequence/"),
    ("Longest String Chain", "Medium", "Longest Increasing Subsequence (LIS)", "https://leetcode.com/problems/longest-string-chain/"),
    ("Longest Arithmetic Subsequence", "Medium", "Longest Increasing Subsequence (LIS)", "https://leetcode.com/problems/longest-arithmetic-subsequence/"),
    ("Russian Doll Envelopes", "Hard", "Longest Increasing Subsequence (LIS)", "https://leetcode.com/problems/russian-doll-envelopes/"),

    # ── 2D Grid DP ───────────────────────────────────────────────────────────
    ("Pascal's Triangle", "Easy", "2D Grid DP", "https://leetcode.com/problems/pascals-triangle/"),
    ("Unique Paths", "Medium", "2D Grid DP", "https://leetcode.com/problems/unique-paths/"),
    ("Unique Paths II", "Medium", "2D Grid DP", "https://leetcode.com/problems/unique-paths-ii/"),
    ("Minimum Path Sum", "Medium", "2D Grid DP", "https://leetcode.com/problems/minimum-path-sum/"),
    ("Triangle", "Medium", "2D Grid DP", "https://leetcode.com/problems/triangle/"),
    ("Maximal Square", "Medium", "2D Grid DP", "https://leetcode.com/problems/maximal-square/"),
    ("Count Square Submatrices with All Ones", "Medium", "2D Grid DP", "https://leetcode.com/problems/count-square-submatrices-with-all-ones/"),
    ("Maximum Number of Points with Cost", "Medium", "2D Grid DP", "https://leetcode.com/problems/maximum-number-of-points-with-cost/"),
    ("Paint House", "Medium", "2D Grid DP", "https://leetcode.com/problems/paint-house/"),
    ("Minimum Falling Path Sum", "Medium", "2D Grid DP", "https://leetcode.com/problems/minimum-falling-path-sum/"),
    ("Maximum Profit in Job Scheduling", "Hard", "2D Grid DP", "https://leetcode.com/problems/maximum-profit-in-job-scheduling/"),
    ("Burst Balloons", "Hard", "2D Grid DP", "https://leetcode.com/problems/burst-balloons/"),
    ("Remove Boxes", "Hard", "2D Grid DP", "https://leetcode.com/problems/remove-boxes/"),
    ("Maximal Rectangle", "Hard", "2D Grid DP", "https://leetcode.com/problems/maximal-rectangle/"),
    ("Cherry Pickup", "Hard", "2D Grid DP", "https://leetcode.com/problems/cherry-pickup/"),
    ("Dungeon Game", "Hard", "2D Grid DP", "https://leetcode.com/problems/dungeon-game/"),
    ("Longest Increasing Path in a Matrix", "Hard", "2D Grid DP", "https://leetcode.com/problems/longest-increasing-path-in-a-matrix/"),
    ("Painting a Grid With Three Different Colors", "Hard", "2D Grid DP", "https://leetcode.com/problems/painting-a-grid-with-three-different-colors/"),
    ("Frog Jump", "Hard", "2D Grid DP", "https://leetcode.com/problems/frog-jump/"),
    ("Optimal Account Balancing", "Hard", "2D Grid DP", "https://leetcode.com/problems/optimal-account-balancing/"),
    ("Minimum Difficulty of a Job Schedule", "Hard", "2D Grid DP", "https://leetcode.com/problems/minimum-difficulty-of-a-job-schedule/"),
    ("Minimum Cost to Cut a Stick", "Hard", "2D Grid DP", "https://leetcode.com/problems/minimum-cost-to-cut-a-stick/"),
    ("Cherry Pickup II", "Hard", "2D Grid DP", "https://leetcode.com/problems/cherry-pickup-ii/"),

    # ── String DP ────────────────────────────────────────────────────────────
    ("Longest Common Subsequence", "Medium", "String DP", "https://leetcode.com/problems/longest-common-subsequence/"),
    ("Longest Palindromic Subsequence", "Medium", "String DP", "https://leetcode.com/problems/longest-palindromic-subsequence/"),
    ("Edit Distance", "Medium", "String DP", "https://leetcode.com/problems/edit-distance/"),
    ("Decode Ways", "Medium", "String DP", "https://leetcode.com/problems/decode-ways/"),
    ("Word Break", "Medium", "String DP", "https://leetcode.com/problems/word-break/"),
    ("Interleaving String", "Medium", "String DP", "https://leetcode.com/problems/interleaving-string/"),
    ("Minimum Deletions to Make String Balanced", "Medium", "String DP", "https://leetcode.com/problems/minimum-deletions-to-make-string-balanced/"),
    ("Word Break II", "Hard", "String DP", "https://leetcode.com/problems/word-break-ii/"),
    ("Wildcard Matching", "Hard", "String DP", "https://leetcode.com/problems/wildcard-matching/"),
    ("Regular Expression Matching", "Hard", "String DP", "https://leetcode.com/problems/regular-expression-matching/"),
    ("Distinct Subsequences", "Hard", "String DP", "https://leetcode.com/problems/distinct-subsequences/"),
    ("Palindrome Partitioning II", "Hard", "String DP", "https://leetcode.com/problems/palindrome-partitioning-ii/"),
    ("Strange Printer", "Hard", "String DP", "https://leetcode.com/problems/strange-printer/"),
    ("Shortest Common Supersequence", "Hard", "String DP", "https://leetcode.com/problems/shortest-common-supersequence/"),

    # ── Tree / Graph DP ──────────────────────────────────────────────────────
    ("House Robber III", "Medium", "Tree/Graph DP", "https://leetcode.com/problems/house-robber-iii/"),
    ("Unique Binary Search Trees II", "Medium", "Tree/Graph DP", "https://leetcode.com/problems/unique-binary-search-trees-ii/"),
    ("Number of Ways to Arrive at Destination", "Medium", "Tree/Graph DP", "https://leetcode.com/problems/number-of-ways-to-arrive-at-destination/"),
    ("Binary Tree Cameras", "Hard", "Tree/Graph DP", "https://leetcode.com/problems/binary-tree-cameras/"),
    ("Sum of Distances in Tree", "Hard", "Tree/Graph DP", "https://leetcode.com/problems/sum-of-distances-in-tree/"),

    # ── Bitmask DP ───────────────────────────────────────────────────────────
    ("Campus Bikes II", "Medium", "Bitmask DP", "https://leetcode.com/problems/campus-bikes-ii/"),
    ("Partition to K Equal Sum Subsets", "Medium", "Bitmask DP", "https://leetcode.com/problems/partition-to-k-equal-sum-subsets/"),
    ("Minimum Number of Work Sessions to Finish the Tasks", "Medium", "Bitmask DP", "https://leetcode.com/problems/minimum-number-of-work-sessions-to-finish-the-tasks/"),
    ("Fair Distribution of Cookies", "Medium", "Bitmask DP", "https://leetcode.com/problems/fair-distribution-of-cookies/"),
    ("Shortest Path Visiting All Nodes", "Hard", "Bitmask DP", "https://leetcode.com/problems/shortest-path-visiting-all-nodes/"),

    # ── Digit DP ─────────────────────────────────────────────────────────────
    ("Count Numbers with Unique Digits", "Medium", "Digit DP", "https://leetcode.com/problems/count-numbers-with-unique-digits/"),
    ("Number of Digit One", "Hard", "Digit DP", "https://leetcode.com/problems/number-of-digit-one/"),
    ("Numbers At Most N Given Digit Set", "Hard", "Digit DP", "https://leetcode.com/problems/numbers-at-most-n-given-digit-set/"),

    # ── Probability DP ───────────────────────────────────────────────────────
    ("Knight Probability in Chessboard", "Medium", "Probability DP", "https://leetcode.com/problems/knight-probability-in-chessboard/"),
    ("Soup Servings", "Medium", "Probability DP", "https://leetcode.com/problems/soup-servings/"),
    ("New 21 Game", "Medium", "Probability DP", "https://leetcode.com/problems/new-21-game/"),

    # ── State Machine DP ─────────────────────────────────────────────────────
    ("Best Time to Buy and Sell Stock with Cooldown", "Medium", "State Machine DP", "https://leetcode.com/problems/best-time-to-buy-and-sell-stock-with-cooldown/"),
    ("Best Time to Buy and Sell Stock with Transaction Fee", "Medium", "State Machine DP", "https://leetcode.com/problems/best-time-to-buy-and-sell-stock-with-transaction-fee/"),
    ("Best Time to Buy and Sell Stock III", "Hard", "State Machine DP", "https://leetcode.com/problems/best-time-to-buy-and-sell-stock-iii/"),
    ("Best Time to Buy and Sell Stock IV", "Hard", "State Machine DP", "https://leetcode.com/problems/best-time-to-buy-and-sell-stock-iv/"),

    # ── Maths / Geometry ─────────────────────────────────────────────────────
    ("Palindrome Number", "Easy", "Maths/Geometry", "https://leetcode.com/problems/palindrome-number/"),
    ("Plus One", "Easy", "Maths/Geometry", "https://leetcode.com/problems/plus-one/"),
    ("Roman to Integer", "Easy", "Maths/Geometry", "https://leetcode.com/problems/roman-to-integer/"),
    ("Excel Sheet Column Title", "Easy", "Maths/Geometry", "https://leetcode.com/problems/excel-sheet-column-title/"),
    ("Greatest Common Divisor of Strings", "Easy", "Maths/Geometry", "https://leetcode.com/problems/greatest-common-divisor-of-strings/"),
    ("Ugly Number", "Easy", "Maths/Geometry", "https://leetcode.com/problems/ugly-number/"),
    ("Ugly Number II", "Medium", "Maths/Geometry", "https://leetcode.com/problems/ugly-number-ii/"),
    ("Reverse Integer", "Medium", "Maths/Geometry", "https://leetcode.com/problems/reverse-integer/"),
    ("Multiply Strings", "Medium", "Maths/Geometry", "https://leetcode.com/problems/multiply-strings/"),
    ("Find the Duplicate Number", "Medium", "Maths/Geometry", "https://leetcode.com/problems/find-the-duplicate-number/"),
    ("Count Good Numbers", "Medium", "Maths/Geometry", "https://leetcode.com/problems/count-good-numbers/"),
    ("Count Primes", "Medium", "Maths/Geometry", "https://leetcode.com/problems/count-primes/"),
    ("Factorial Trailing Zeroes", "Medium", "Maths/Geometry", "https://leetcode.com/problems/factorial-trailing-zeroes/"),
    ("Valid Triangle Number", "Medium", "Maths/Geometry", "https://leetcode.com/problems/valid-triangle-number/"),
    ("Valid Square", "Medium", "Maths/Geometry", "https://leetcode.com/problems/valid-square/"),
    ("Minimum Area Rectangle", "Medium", "Maths/Geometry", "https://leetcode.com/problems/minimum-area-rectangle/"),
    ("Minimum Area Rectangle II", "Medium", "Maths/Geometry", "https://leetcode.com/problems/minimum-area-rectangle-ii/"),
    ("Max Points on a Line", "Hard", "Maths/Geometry", "https://leetcode.com/problems/max-points-on-a-line/"),

    # ── String Matching ──────────────────────────────────────────────────────
    ("Repeated Substring Pattern", "Easy", "String Matching", "https://leetcode.com/problems/repeated-substring-pattern/"),
    ("Repeated String Match", "Medium", "String Matching", "https://leetcode.com/problems/repeated-string-match/"),
    ("Number of Distinct Substrings in a String", "Medium", "String Matching", "https://leetcode.com/problems/number-of-distinct-substrings-in-a-string/"),
    ("Longest Happy Prefix", "Hard", "String Matching", "https://leetcode.com/problems/longest-happy-prefix/"),
    ("Shortest Palindrome", "Hard", "String Matching", "https://leetcode.com/problems/shortest-palindrome/"),
    ("Longest Duplicate Substring", "Hard", "String Matching", "https://leetcode.com/problems/longest-duplicate-substring/"),

    # ── Binary Indexed Tree / Segment Tree ───────────────────────────────────
    ("Range Sum Query - Mutable", "Medium", "Binary Indexed Tree/Segment Tree", "https://leetcode.com/problems/range-sum-query-mutable/"),
    ("Range Sum Query 2D - Mutable", "Hard", "Binary Indexed Tree/Segment Tree", "https://leetcode.com/problems/range-sum-query-2d-mutable/"),
    ("Count of Smaller Numbers After Self", "Hard", "Binary Indexed Tree/Segment Tree", "https://leetcode.com/problems/count-of-smaller-numbers-after-self/"),
    ("Falling Squares", "Hard", "Binary Indexed Tree/Segment Tree", "https://leetcode.com/problems/falling-squares/"),
    ("Block Placement Queries", "Hard", "Binary Indexed Tree/Segment Tree", "https://leetcode.com/problems/block-placement-queries/"),
    ("Number of Pairs Satisfying Inequality", "Hard", "Binary Indexed Tree/Segment Tree", "https://leetcode.com/problems/number-of-pairs-satisfying-inequality/"),
    ("My Calendar III", "Hard", "Binary Indexed Tree/Segment Tree", "https://leetcode.com/problems/my-calendar-iii/"),

    # ── Line Sweep ───────────────────────────────────────────────────────────
    ("Employee Free Time", "Hard", "Line Sweep", "https://leetcode.com/problems/employee-free-time/"),
    ("Minimum Interval to Include Each Query", "Hard", "Line Sweep", "https://leetcode.com/problems/minimum-interval-to-include-each-query/"),
    ("The Skyline Problem", "Hard", "Line Sweep", "https://leetcode.com/problems/the-skyline-problem/"),
    ("Rectangle Area II", "Hard", "Line Sweep", "https://leetcode.com/problems/rectangle-area-ii/"),
    ("Perfect Rectangle", "Hard", "Line Sweep", "https://leetcode.com/problems/perfect-rectangle/"),
]


def _starter_code(category: str) -> str:
    return f'''def solve(nums):
    """
    Category: {category}
    TODO: Implement your solution here.
    """
    pass
'''


async def _seed_from_json(db) -> int:
    """Load full problem data from local JSON cache — no LeetCode request needed."""
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    to_insert = []
    for item in data:
        to_insert.append(Problem(
            slug=item["slug"],
            title=item["title"],
            difficulty=item["difficulty"],
            category=item["category"],
            subcategory=item.get("subcategory") or None,
            leetcode_url=item.get("leetcode_url") or None,
            description=item.get("description", ""),
            constraints=item.get("constraints", ""),
            starter_code=item.get("starter_code") or _starter_code(item["category"]),
            test_cases=item.get("test_cases", []),
            hints=item.get("hints", []),
            tags=item.get("tags", []),
            is_new=False,
        ))
    db.add_all(to_insert)
    await db.commit()
    populated = sum(1 for p in to_insert if len(p.description or "") > 80)
    print(f"[seed] Loaded {len(to_insert)} problems from JSON cache ({populated} with full descriptions).")
    return len(to_insert)


async def _seed_hardcoded(db) -> int:
    """Insert basic placeholder rows from the hardcoded PROBLEMS list."""
    seen_slugs: set[str] = set()
    to_insert = []
    for idx, (title, difficulty, category, url) in enumerate(PROBLEMS, start=1):
        base_slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        slug = base_slug
        counter = 2
        while slug in seen_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1
        seen_slugs.add(slug)

        to_insert.append(Problem(
            slug=slug,
            title=title,
            difficulty=difficulty,
            category=category,
            leetcode_url=url,
            description=f"Solve the '{title}' problem. See LeetCode for full description.",
            starter_code=_starter_code(category),
            test_cases=[],
            hints=[],
            tags=[],
            constraints="",
            is_new=False,
        ))

    db.add_all(to_insert)
    await db.commit()
    print(f"[seed] Inserted {len(to_insert)} placeholder problems. Go to Settings to fetch descriptions.")
    return len(to_insert)


async def seed_problems():
    async with AsyncSessionLocal() as db:
        count_q = await db.execute(select(func.count()).select_from(Problem))
        existing = count_q.scalar() or 0
        if existing >= len(PROBLEMS):
            return  # already seeded, DB volume persists

        if DATA_FILE.exists():
            # JSON cache found — load full data instantly (no network needed)
            await _seed_from_json(db)
        else:
            # No cache yet — insert basic placeholders; user fetches from LeetCode via Settings
            await _seed_hardcoded(db)
